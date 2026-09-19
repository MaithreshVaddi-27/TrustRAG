"""
TRUSTRAG — OCR page-image persistence (Phase 7 provenance residual).

Completes the provenance chain ``Answer → OCR chunk → page → original image``:
page renders that fed the OCR engine are stored on disk once per
``(kb_id, document_id, page)`` and referenced from chunk records
(Mongo + Qdrant payload) via a relative ``page_image_ref``.

Layout: ``<base>/<kb_id>/<document_id>/p<page>.png`` where ``<base>`` is
``PAGE_IMAGES_DIR`` when set, else ``apps/api/data/page_images``.

Safety: refs are validated against a strict pattern on both write and read;
resolution is confined to the base dir (traversal-safe); all helpers fail
open (None / 0) so storage problems never break ingestion or retrieval.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

API_ROOT = Path(__file__).resolve().parents[2]

_ID_PART = r"[A-Za-z0-9_-]+"
_REF_RE = re.compile(rf"^({_ID_PART})/({_ID_PART})/p(\d+)\.png$")


def base_dir() -> Path:
    """Resolve the page-image store, creating it on demand (tests override via env)."""
    override = os.environ.get("PAGE_IMAGES_DIR")
    base = Path(override) if override else API_ROOT / "data" / "page_images"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(_ID_PART, value) is not None


def save_page_image(kb_id: str, doc_id: str, page: int, png_bytes: bytes) -> str:
    """Persist one rendered page; return its relative ref. Raises ValueError on bad input."""
    if not _valid_id(kb_id) or not _valid_id(doc_id):
        raise ValueError("kb_id/doc_id must be filename-safe identifiers")
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise ValueError("page must be a positive int")
    if not png_bytes:
        raise ValueError("png_bytes must be non-empty")

    dest = base_dir() / kb_id / doc_id / f"p{page}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(png_bytes)
    return os.path.join(kb_id, doc_id, f"p{page}.png")


def resolve_page_image_path(ref: str | None) -> Path | None:
    """Resolve a stored ref to an on-disk file. None when invalid or missing."""
    if not ref:
        return None
    match = _REF_RE.fullmatch(ref)
    if not match:
        return None
    kb_id, doc_id, page = match.groups()
    try:
        candidate = (base_dir() / kb_id / doc_id / f"p{page}.png").resolve()
        candidate.relative_to(base_dir().resolve())
    except (ValueError, OSError, RuntimeError):
        return None
    return candidate if candidate.is_file() else None


def copy_page_image(ref: str | None, dest_kb_id: str, dest_doc_id: str) -> str | None:
    """Duplicate a stored image under new ownership (snapshot path). None on any failure."""
    src = resolve_page_image_path(ref)
    if src is None or not _valid_id(dest_kb_id) or not _valid_id(dest_doc_id):
        return None
    try:
        return save_page_image(dest_kb_id, dest_doc_id, int(src.stem[1:]), src.read_bytes())
    except (ValueError, OSError) as exc:
        logger.warning("Page-image copy failed; snapshot chunk keeps no image ref", error=str(exc))
        return None


def delete_doc_page_images(kb_id: str, doc_id: str) -> int:
    """Remove one document's page images. Returns files removed; never raises."""
    if not (_valid_id(kb_id) and _valid_id(doc_id)):
        return 0
    return _remove_tree(base_dir() / kb_id / doc_id)


def delete_kb_page_images(kb_id: str) -> int:
    """Remove a whole KB's page images. Returns files removed; never raises."""
    return _remove_tree(base_dir() / kb_id) if _valid_id(kb_id) else 0


def _remove_tree(path: Path) -> int:
    try:
        if not path.is_dir():
            return 0
        removed = sum(1 for _ in path.rglob("*.png"))
        shutil.rmtree(path)
        return removed
    except OSError as exc:
        logger.warning("Page-image purge failed; files orphaned on disk", error=str(exc))
        return 0
