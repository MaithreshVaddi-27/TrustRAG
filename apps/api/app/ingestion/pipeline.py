"""
TRUSTRAG — Ingestion pipeline coordinator.

Generates dense and sparse embeddings, indexes points to Qdrant,
and updates document ingestion status in MongoDB.
"""

from __future__ import annotations

import asyncio
import hashlib
import threading
import uuid
import weakref
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from qdrant_client.http import models

from app.core.config import get_model_config
from app.core.hardware import get_ingest_embed_batch_size
from app.core.logging import get_logger
from app.core.memory import trim_memory
from app.core.model_registry import get_embedding_model
from app.db.mongodb import Collections, get_collection
from app.db.qdrant import get_collection_name, get_qdrant_client, init_kb_collection
from app.ingestion.chunking_strategies import ChunkingStrategy
from app.ingestion.sparse_vector import generate_sparse_vector

logger = get_logger(__name__)

# Ingestion can run several CPU/embedding-heavy background jobs at once. Keep
# it serialized per event loop so uploads cannot starve the local model or API.
# Keyed by the loop *object* in a WeakKeyDictionary, not by id(loop): CPython
# reuses ids of collected objects, so an id-keyed map can hand a semaphore
# bound to a dead loop to a brand-new loop (M5: documents wedged in
# "processing" forever). Weak keys also drop the entry when the loop closes.
# Same pattern as app/core/concurrency.py.
_INGESTION_SEMAPHORES: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)
_INGESTION_SEMAPHORE_LOCK = threading.Lock()


def _get_ingestion_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    semaphore = _INGESTION_SEMAPHORES.get(loop)
    if semaphore is None:
        with _INGESTION_SEMAPHORE_LOCK:
            semaphore = _INGESTION_SEMAPHORES.get(loop)
            if semaphore is None:
                semaphore = asyncio.Semaphore(1)
                _INGESTION_SEMAPHORES[loop] = semaphore
    return semaphore


async def _index_parsed_chunks(
    doc_id_str: str,
    kb_id_str: str,
    chunks: list[dict[str, Any]] | None = None,
    strategy: ChunkingStrategy | None = None,
) -> None:
    """
    Background task to generate embeddings and index chunks to Qdrant.

    Stages:
      1. Fetch document record, update status to 'processing'
      2. Ensure Qdrant collection 'kb_{kb_id}' exists
      3. For each chunk:
          - Generate dense embedding (single ONNX BGE engine, models.yaml)
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
        # OCR provenance: parent-document version rides into every chunk
        # record + vector payload so answers stay traceable to a version.
        doc_version = doc.get("version", "1.0") if doc else "1.0"
        doc_is_snapshot = bool(doc.get("is_snapshot", False)) if doc else False

        # NOTE: chunking happens at upload time (knowledge_bases.py selects the
        # configured strategy via get_chunking_strategy()). The `strategy`
        # parameter is kept for backward compatibility and ignored here —
        # this stage only embeds and indexes the chunks it receives.

        # Pin check BEFORE any writes: never mix embedding spaces in one
        # collection (retriever would truncate/pad garbage). Fail loudly so the
        # operator re-uploads into a NEW KB instead of corrupting this one.
        # Runs before Mongo insert + Qdrant upsert so a mismatch leaves no
        # orphan chunks behind. The model is the single models.yaml value —
        # a pinned KB keeps working, and a config change requires re-upload.
        cfg_early = get_model_config()
        _kb_coll_early = get_collection(Collections.KNOWLEDGE_BASES)
        _existing_kb_early = await _kb_coll_early.find_one({"_id": ObjectId(kb_id_str)})
        _pinned_model = (_existing_kb_early or {}).get("embedding_model")
        # Single embedding engine: the server always runs the models.yaml
        # default. A pinned KB with a different id means re-upload.
        effective_embedding_model = cfg_early.embedding_model
        _pinned_norm = _pinned_model.strip().lower() if _pinned_model else ""
        if _pinned_model and _pinned_norm != effective_embedding_model.strip().lower():
            raise RuntimeError(
                f"Embedding model mismatch: KB pinned to "
                f"{_pinned_model} but current is "
                f"{effective_embedding_model}. Re-upload into a NEW KB to migrate."
            )
        if _existing_kb_early is not None and not _pinned_model:
            await _kb_coll_early.update_one(
                {"_id": ObjectId(kb_id_str)},
                {
                    "$set": {
                        "embedding_model": effective_embedding_model,
                        "embedding_dim": cfg_early.embedding_dimensionality,
                    }
                },
            )

        # Store chunks in MongoDB for future integrity audits
        # Dedup on retry/re-ingest: Qdrant upsert is idempotent (deterministic
        # point IDs) but Mongo insert_many is not — clear this doc's chunks first.
        chunks_coll = get_collection(Collections.DOCUMENT_CHUNKS)
        await chunks_coll.delete_many({"document_id": doc_id})
        # Page-image chain (Answer → chunk → page → image): persist each
        # distinct rendered page ONCE (many chunks share one page), then link
        # every chunk to its page's ref. Raw bytes never enter any store.
        # Best-effort: a save failure must not fail indexing.
        page_refs: dict[int, str] = {}
        try:
            from app.ingestion import page_images as page_images_mod

            seen_pages: dict[int, bytes] = {}
            for c in chunks:
                png = c.get("page_image_png")
                if isinstance(png, (bytes, bytearray)) and png and c.get("page") not in seen_pages:
                    seen_pages[c["page"]] = bytes(png)
            for page_num, png_bytes in seen_pages.items():
                try:
                    page_refs[page_num] = page_images_mod.save_page_image(
                        kb_id_str, doc_id_str, int(page_num), png_bytes
                    )
                except Exception as exc:
                    logger.warning(
                        "Page-image persist failed; chunk keeps text only",
                        doc_id=doc_id_str,
                        page=page_num,
                        error=str(exc),
                    )
        except Exception as exc:
            logger.warning("Page-image persist skipped", doc_id=doc_id_str, error=str(exc))
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
                    "ocr_used": bool(c.get("ocr_used", False)),
                    "ocr_confidence": c.get("ocr_confidence"),
                    "page_image_ref": page_refs.get(c["page"]),
                    "document_version": doc_version,
                    "is_snapshot": doc_is_snapshot,
                }
            )
        if mongo_chunks:
            await chunks_coll.insert_many(mongo_chunks)

        # 2. Ensure Qdrant collection is initialized
        await init_kb_collection(kb_id_str)

        # 3. Load embedding model (cached) — single models.yaml model.
        embed_model = get_embedding_model()

        # Zero-Cost Contextual Prefixing (Anthropic SOTA pattern):
        # Prepend document filename and zone to resolve chunk ambiguity without extra LLM cost
        contextual_texts = [
            f"[{doc_filename} | {c.get('zone', 'body').upper()}] {c['text']}" for c in chunks
        ]
        logger.info("Generating dense embeddings", doc_id=doc_id_str, count=len(contextual_texts))

        # Use async batch embedding (aembed_documents) for 2.87x speedup
        # The CachedEmbeddingsWrapper handles disk cache lookup and batching internally
        embed_batch_size = get_ingest_embed_batch_size()
        # Single ONNX-local engine: failures are deterministic (bad input or
        # missing weights), never rate limits — no 429 backoff. Fail fast so
        # a broken batch surfaces immediately instead of sleeping for minutes.
        dense_vectors = []
        for offset in range(0, len(contextual_texts), embed_batch_size):
            batch_slice = contextual_texts[offset : offset + embed_batch_size]
            batch_vecs = await embed_model.aembed_documents(batch_slice)
            dense_vectors.extend(batch_vecs)

        qdrant_client = await get_qdrant_client()
        collection_name = get_collection_name(kb_id_str)

        # 4. Construct Qdrant points
        points = []
        for i, chunk in enumerate(chunks):
            # Sparse TF over RAW text only: the [file | ZONE] prefix is for
            # dense (Anthropic contextual) — filename terms would dominate BM25.
            chunk_zone = chunk.get("zone", "body")
            sparse_vec = generate_sparse_vector(chunk["text"], zone=chunk_zone)

            # Unique deterministic ID for Qdrant point (based on doc ID and chunk index)
            point_id = hashlib_qdrant_id(doc_id_str, chunk["chunk_index"])

            # Payload contains metadata + text + zone + OCR provenance.
            # page_image_png bytes are stripped here: only the persisted ref
            # rides the payload (raw bytes never leak into stores).
            payload = {
                "document_id": doc_id_str,
                "knowledge_base_id": kb_id_str,
                "user_id": str(user_id) if user_id else "",
                "chunk_index": chunk["chunk_index"],
                "page": chunk["page"],
                "character_offset": chunk["character_offset"],
                "zone": chunk_zone,
                "text": chunk["text"],
                "ocr_used": bool(chunk.get("ocr_used", False)),
                "ocr_confidence": chunk.get("ocr_confidence"),
                "page_image_ref": page_refs.get(chunk["page"]),
                "document_version": doc_version,
                "is_snapshot": doc_is_snapshot,
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

        # Incremental indexing: upsert only new/updated points
        # The deterministic point IDs based on (doc_id, chunk_index) ensure
        # existing chunks are updated in place rather than duplicated.
        # Batch upsert to prevent network timeouts (size from models.yaml).
        upsert_batch = get_model_config().qdrant_upsert_batch
        for offset in range(0, len(points), upsert_batch):
            batch = points[offset : offset + upsert_batch]
            await qdrant_client.upsert(collection_name=collection_name, points=batch)

        logger.info("Incremental indexing completed", doc_id=doc_id_str, chunks=len(points))

        # 5. Mark document completed
        await doc_coll.update_one({"_id": doc_id}, {"$set": {"ingestion_status": "completed"}})
        logger.info("Ingestion completed successfully", doc_id=doc_id_str, chunks=len(points))

        # 6. Record embedding dimensionality on the KB (pin itself was
        # enforced before any writes above; this only stamps dim/pinned_at
        # using the effective model, never re-pinning across spaces).
        if dense_vectors:
            kb_coll = get_collection(Collections.KNOWLEDGE_BASES)
            await kb_coll.update_one(
                {"_id": ObjectId(kb_id_str)},
                {
                    "$set": {
                        "embedding_dim": len(dense_vectors[0]),
                        "embedding_pinned_at": datetime.now(UTC),
                    }
                },
            )

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
        await asyncio.to_thread(trim_memory)


async def index_parsed_chunks(
    doc_id_str: str,
    kb_id_str: str,
    chunks: list[dict[str, Any]] | None = None,
    strategy: ChunkingStrategy | None = None,
) -> None:
    """Run one ingestion job at a time per API process."""
    try:
        async with _get_ingestion_semaphore():
            await _index_parsed_chunks(
                doc_id_str=doc_id_str,
                kb_id_str=kb_id_str,
                chunks=chunks,
                strategy=strategy,
            )
    except Exception as exc:
        # The semaphore acquire sits outside the inner handler's try/except,
        # so an acquire failure used to strand the document in "processing"
        # forever (M5). Mark it failed here instead — same envelope as inside.
        logger.error("Ingestion semaphore acquire failed", doc_id=doc_id_str, error=str(exc))
        try:
            doc_coll = get_collection(Collections.DOCUMENTS)
            err_type = type(exc).__name__
            await doc_coll.update_one(
                {"_id": ObjectId(doc_id_str)},
                {
                    "$set": {
                        "ingestion_status": "failed",
                        "error_message": f"Ingestion error ({err_type}). See server logs.",
                    }
                },
            )
        except Exception:
            logger.error("Failed to mark document failed after semaphore error", doc_id=doc_id_str)


def hashlib_qdrant_id(doc_id_str: str, chunk_index: int) -> str:
    """Generate a consistent UUID string for Qdrant from doc_id and chunk_index."""
    unique_str = f"{doc_id_str}_{chunk_index}"
    hash_bytes = hashlib.sha256(unique_str.encode("utf-8")).digest()[:16]
    return str(uuid.UUID(bytes=hash_bytes))
