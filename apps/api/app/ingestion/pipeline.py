"""
TRUSTRAG — Ingestion pipeline coordinator.

Generates dense and sparse embeddings, indexes points to Qdrant,
and updates document ingestion status in MongoDB.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from qdrant_client.http import models

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

        # Store chunks in MongoDB for future integrity audits
        import hashlib

        chunks_coll = get_collection(Collections.DOCUMENT_CHUNKS)
        mongo_chunks = []
        for c in chunks:
            mongo_chunks.append(
                {
                    "document_id": doc_id,
                    "chunk_index": c["chunk_index"],
                    "text": c["text"],
                    "page": c["page"],
                    "character_offset": c["character_offset"],
                    "text_hash": hashlib.sha256(c["text"].encode("utf-8")).hexdigest(),
                }
            )
        if mongo_chunks:
            await chunks_coll.insert_many(mongo_chunks)

        # 2. Ensure Qdrant collection is initialized
        await init_kb_collection(kb_id_str)

        # 3. Load embedding model (cached)
        embed_model = get_embedding_model()

        # Extract texts for batch embedding
        texts = [c["text"] for c in chunks]
        logger.info("Generating dense embeddings", doc_id=doc_id_str, count=len(texts))

        # Batch encode
        dense_vectors = embed_model.embed_documents(texts)

        qdrant_client = get_qdrant_client()
        collection_name = get_collection_name(kb_id_str)

        # 4. Construct Qdrant points
        points = []
        for i, chunk in enumerate(chunks):
            # Compute sparse TF vector
            sparse_vec = generate_sparse_vector(chunk["text"])

            # Unique deterministic ID for Qdrant point (based on doc ID and chunk index)
            point_id = hashlib_qdrant_id(doc_id_str, chunk["chunk_index"])

            # Payload contains metadata + text
            payload = {
                "document_id": doc_id_str,
                "knowledge_base_id": kb_id_str,
                "chunk_index": chunk["chunk_index"],
                "page": chunk["page"],
                "character_offset": chunk["character_offset"],
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
        # Mark document failed with error trace
        await doc_coll.update_one(
            {"_id": doc_id}, {"$set": {"ingestion_status": "failed", "error_message": str(exc)}}
        )


def hashlib_qdrant_id(doc_id_str: str, chunk_index: int) -> str:
    """Generate a consistent UUID string for Qdrant from doc_id and chunk_index."""
    import hashlib
    import uuid

    unique_str = f"{doc_id_str}_{chunk_index}"
    hash_bytes = hashlib.sha256(unique_str.encode("utf-8")).digest()[:16]
    return str(uuid.UUID(bytes=hash_bytes))
