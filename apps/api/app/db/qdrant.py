"""
TRUSTRAG — Qdrant vector database client.

Handles collection initialization and drops.
Separates knowledge bases into independent Qdrant collections.
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import get_model_config, get_settings
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Return a thread-safe Qdrant client singleton."""
    global _client
    if _client is None:
        settings = get_settings()
        logger.info("Initializing Qdrant client", url=settings.qdrant_url)
        try:
            if settings.qdrant_api_key:
                _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
            else:
                _client = QdrantClient(url=settings.qdrant_url)
        except Exception as exc:
            raise VectorStoreError("Failed to initialize Qdrant client", detail=str(exc)) from exc
    return _client


def get_collection_name(kb_id: str) -> str:
    """Consistently format collection name per KB ID."""
    return f"kb_{kb_id}"


async def init_kb_collection(kb_id: str) -> None:
    """
    Initialize a vector collection for the given knowledge base ID.

    Creates a collection with:
      - Dense vector parameters: Cosine distance, 384 dimensions (HuggingFace)
      - Sparse vector parameters: BM25/keyword sparse query configuration
    """
    client = get_qdrant_client()
    collection_name = get_collection_name(kb_id)
    cfg = get_model_config()

    try:
        # Check if already exists
        exists = client.collection_exists(collection_name)
        if exists:
            logger.debug("Qdrant collection already exists", collection=collection_name)
            return

        logger.info(
            "Creating Qdrant collection",
            collection=collection_name,
            dense_dim=cfg.embedding_dimensionality,
        )

        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=cfg.embedding_dimensionality,
                distance=models.Distance.COSINE,
            ),
            # Setup sparse vectors indexing (sparse query matching/BM25)
            sparse_vectors_config={
                "sparse-text": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=True)
                )
            },
        )
        logger.info("Qdrant collection created successfully", collection=collection_name)
    except Exception as exc:
        raise VectorStoreError(
            f"Failed to initialize Qdrant collection '{collection_name}'", detail=str(exc)
        ) from exc


async def delete_kb_collection(kb_id: str) -> None:
    """Drop the Qdrant collection associated with this KB."""
    client = get_qdrant_client()
    collection_name = get_collection_name(kb_id)

    try:
        if client.collection_exists(collection_name):
            logger.info("Dropping Qdrant collection", collection=collection_name)
            client.delete_collection(collection_name)
            logger.info("Qdrant collection dropped", collection=collection_name)
    except Exception as exc:
        raise VectorStoreError(
            f"Failed to drop Qdrant collection '{collection_name}'", detail=str(exc)
        ) from exc
