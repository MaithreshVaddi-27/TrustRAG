"""
TRUSTRAG — Ingestion Capability.

Document parsing, chunking, OCR, sparse vectors, and indexing pipeline.
"""

from app.rag.ingestion.parser import (
    parse_document,
    parse_document_bytes,
)
from app.rag.ingestion.chunker import (
    chunk_text,
    chunk_by_strategy,
)
from app.rag.ingestion.chunking_strategies import (
    ChunkingStrategy,
    get_chunking_strategy,
)
from app.rag.ingestion.pipeline import (
    index_parsed_chunks,
)
from app.rag.ingestion.sparse_vector import (
    generate_sparse_vector,
)
from app.rag.ingestion.ocr import (
    ocr_image_bytes,
)
from app.rag.ingestion.page_images import (
    extract_page_images,
)
from app.rag.ingestion.preprocessor import (
    normalize_text,
    detect_chunk_zone,
    lexical_analyze,
    stem_word,
    ZONE_WEIGHT_BOOSTS,
)

__all__ = [
    "parse_document",
    "parse_document_bytes",
    "chunk_text",
    "chunk_by_strategy",
    "ChunkingStrategy",
    "get_chunking_strategy",
    "index_parsed_chunks",
    "generate_sparse_vector",
    "ocr_image_bytes",
    "extract_page_images",
    "normalize_text",
    "detect_chunk_zone",
    "lexical_analyze",
    "stem_word",
    "ZONE_WEIGHT_BOOSTS",
]