"""
TRUSTRAG — Ingestion pipeline coordinator.

Generates dense and sparse embeddings, indexes points to Qdrant,
and updates document ingestion status in MongoDB.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from qdrant_client.http import models

from app.core.config import get_model_config
from app.core.logging import get_logger
from app.core.model_registry import get_embedding_model
from app.db.mongodb import Collections, get_collection
from app.db.qdrant import get_collection_name, get_qdrant_client, init_kb_collection
from app.ingestion.sparse_vector import generate_sparse_vector

logger = get_logger(__name__)


async def index_parsed_chunks(
    doc_id_str: str, kb_id_str: str, chunks: list[dict[str, Any]]
) -> None:
    """
    Background task to generate embeddings and index chunks to Qdrant.

    Stages:
      1. Fetch document record, update status to 'processing'
      2. Ensure Qdrant collection 'kb_{kb_id}' exists
      3. For each chunk:
         - Generate dense embedding (sentence-transformers/all-MiniLM-L6-v2)
         - Generate sparse keyword weights
         - Construct Qdrant point
      4. Upsert points into Qdrant
      5. Update document status to 'completed'
    """
    doc_id = ObjectId(doc_id_str)
    doc_coll = get_collection(Collections.DOCUMENTS)

    # 1. Update status to processing
    await doc_coll.update_one(
        {"_id": doc_id},
        {"$set": {"ingestion_status": "processing", "updated_at": datetime.now(UTC)}},
    )

    try:
        if not chunks:
            await doc_coll.update_one({"_id": doc_id}, {"$set": {"ingestion_status": "completed"}})
            logger.info("Ingestion completed: document has no text chunks", doc_id=doc_id_str)
            return
        user_id = None
        doc_filename = "Document"
        doc = await doc_coll.find_one({"_id": doc_id})
        if doc:
            user_id = doc.get("user_id")
            doc_filename = doc.get("filename", "Document")

        # Store chunks in MongoDB for future integrity audits
        import hashlib

        chunks_coll = get_collection(Collections.DOCUMENT_CHUNKS)
        mongo_chunks = []
        for c in chunks:
            mongo_chunks.append(
                {
                    "document_id": doc_id,
                    "knowledge_base_id": ObjectId(kb_id_str),
                    "user_id": user_id,
                    "chunk_index": c["chunk_index"],
                    "text": c["text"],
                    "page": c["page"],
                    "character_offset": c["character_offset"],
                    "zone": c.get("zone", "body"),
                    "text_hash": hashlib.sha256(c["text"].encode("utf-8")).hexdigest(),
                }
            )
        if mongo_chunks:
            await chunks_coll.insert_many(mongo_chunks)

        # 2. Ensure Qdrant collection is initialized
        await init_kb_collection(kb_id_str)

        # 3. Load embedding model (cached)
        embed_model = get_embedding_model()
        cfg = get_model_config()

        # Zero-Cost Contextual Prefixing (Anthropic SOTA pattern):
        # Prepend document filename and zone to resolve chunk ambiguity without extra LLM cost
        contextual_texts = [
            f"[{doc_filename} | {c.get('zone', 'body').upper()}] {c['text']}" for c in chunks
        ]
        logger.info("Generating dense embeddings", doc_id=doc_id_str, count=len(contextual_texts))

        # Batch encode in chunks of 20 with 30s backoff to respect Google free-tier 100 RPM quota
        embed_batch_size = 20
        dense_vectors = []
        for offset in range(0, len(contextual_texts), embed_batch_size):
            batch_slice = contextual_texts[offset : offset + embed_batch_size]
            for attempt in range(5):
                try:
                    batch_vecs = await asyncio.to_thread(embed_model.embed_documents, batch_slice)
                    dense_vectors.extend(batch_vecs)
                    break
                except Exception as batch_err:
                    err_msg = str(batch_err)
                    if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < 4:
                        wait_seconds = 32 if attempt >= 1 else 15
                        logger.warning(
                            "Embedding rate limit reached, waiting for quota reset",
                            attempt=attempt + 1,
                            wait_seconds=wait_seconds,
                        )
                        await asyncio.sleep(wait_seconds)
                    else:
                        raise batch_err
            has_more = offset + embed_batch_size < len(contextual_texts)
            if has_more and cfg.embedding_provider == "google_genai":
                await asyncio.sleep(1.0)

        qdrant_client = get_qdrant_client()
        collection_name = get_collection_name(kb_id_str)

        # 4. Construct Qdrant points
        points = []
        for i, chunk in enumerate(chunks):
            # Compute sparse TF vector with zone weighting over contextual text
            chunk_zone = chunk.get("zone", "body")
            sparse_vec = generate_sparse_vector(contextual_texts[i], zone=chunk_zone)

            # Unique deterministic ID for Qdrant point (based on doc ID and chunk index)
            point_id = hashlib_qdrant_id(doc_id_str, chunk["chunk_index"])

            # Payload contains metadata + text + zone
            payload = {
                "document_id": doc_id_str,
                "knowledge_base_id": kb_id_str,
                "user_id": str(user_id) if user_id else "",
                "chunk_index": chunk["chunk_index"],
                "page": chunk["page"],
                "character_offset": chunk["character_offset"],
                "zone": chunk_zone,
                "text": chunk["text"],
            }

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        # Named vector configurations
                        "": dense_vectors[i],  # Default/dense
                        "sparse-text": models.SparseVector(  # Sparse BM25
                            indices=sparse_vec["indices"], values=sparse_vec["values"]
                        ),
                    },
                    payload=payload,
                )
            )

        # Upsert in batches of 100 to prevent network timeouts
        batch_size = 100
        for offset in range(0, len(points), batch_size):
            batch = points[offset : offset + batch_size]
            qdrant_client.upsert(collection_name=collection_name, points=batch)

        # 5. Mark document completed
        await doc_coll.update_one({"_id": doc_id}, {"$set": {"ingestion_status": "completed"}})
        logger.info("Ingestion completed successfully", doc_id=doc_id_str, chunks=len(points))

    except Exception as exc:
        logger.error("Ingestion pipeline failed", doc_id=doc_id_str, error=str(exc))
        # Store a generic error type — NOT str(exc), which can leak internal details
        # (file paths, connection strings, stack info) to the client via DocResponse
        # (this field is returned as-is by the documents API).
        error_type = type(exc).__name__
        await doc_coll.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "ingestion_status": "failed",
                    "error_message": f"Ingestion error ({error_type}). See server logs.",
                }
            },
        )
    finally:
        from app.core.memory import trim_memory

        trim_memory()


def hashlib_qdrant_id(doc_id_str: str, chunk_index: int) -> str:
    """Generate a consistent UUID string for Qdrant from doc_id and chunk_index."""
    import hashlib
    import uuid

    unique_str = f"{doc_id_str}_{chunk_index}"
    hash_bytes = hashlib.sha256(unique_str.encode("utf-8")).digest()[:16]
    return str(uuid.UUID(bytes=hash_bytes))
