"""
TRUSTRAG — Ingestion Capability.

Document parsing, chunking, OCR, sparse vectors, and indexing pipeline.
"""

from app.rag.ingestion.chunker import (
    chunk_by_strategy,
    chunk_text,
)
from app.rag.ingestion.chunking_strategies import (
    ChunkingStrategy,
    get_chunking_strategy,
)
from app.rag.ingestion.ocr import (
    ocr_image_bytes,
)
from app.rag.ingestion.page_images import (
    extract_page_images,
)
from app.rag.ingestion.parser import (
    parse_document,
    parse_document_bytes,
)
from app.rag.ingestion.pipeline import (
    index_parsed_chunks,
)
from app.rag.ingestion.preprocessor import (
    ZONE_WEIGHT_BOOSTS,
    detect_chunk_zone,
    lexical_analyze,
    normalize_text,
    stem_word,
)
from app.rag.ingestion.sparse_vector import (
    generate_sparse_vector,
)

__all__ = [
    "ZONE_WEIGHT_BOOSTS",
    "ChunkingStrategy",
    "chunk_by_strategy",
    "chunk_text",
    "detect_chunk_zone",
    "extract_page_images",
    "generate_sparse_vector",
    "get_chunking_strategy",
    "index_parsed_chunks",
    "lexical_analyze",
    "normalize_text",
    "ocr_image_bytes",
    "parse_document",
    "parse_document_bytes",
    "stem_word",
]
