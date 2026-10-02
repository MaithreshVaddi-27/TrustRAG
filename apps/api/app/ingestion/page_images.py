"""
TRUSTRAG — OCR page-image persistence (Answer → chunk → page → image chain).

Stores the exact page renders the OCR engine read so evidence stays
visually auditable. Layout on disk::

    <PAGE_IMAGES_DIR>/<kb_id>/<doc_id>/p<page>.png

Refs (`kb/doc/pN.png`, os.path.join form) ride chunk records in MongoDB and
Qdrant; the GET /documents/{id}/pages/{page}/image route resolves them back
to bytes. Raw ``page_image_png`` bytes never enter any store.

Safety:
- kb/doc ids are validated as hex-ish path segments (no traversal, no abs).
- resolve/copy/delete never raise for missing files (best-effort purge on
  KB/doc delete must not fail the delete).
- Base dir comes from ``PAGE_IMAGES_DIR`` env (tests) or
  ``apps/api/data/page_images`` (production default, alongside the SQLite
  cache dir pattern in app/core/disk_cache.py).
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# ObjectId hex (24) plus a small tolerance for non-Mongo callers (tests use
# short ids like "kb1"). Anything else (.., /, absolute) is rejected.
_SAFE_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}\Z")


def _base_dir() -> Path:
    env = os.environ.get("PAGE_IMAGES_DIR")
    if env and env.strip():
        return Path(env)
    here = Path(__file__).resolve()
    return here.parents[2] / "data" / "page_images"


def _check_segment(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"Invalid {name} for page-image storage: {value!r}")
    return value


def _ref_path(ref: str) -> Path | None:
    """Resolve a stored ref to an existing file, or None (never raises)."""
    try:
        if not isinstance(ref, str) or not ref:
            return None
        parts = ref.replace("\\", "/").split("/")
        if len(parts) != 3:
            return None
        kb_id, doc_id, filename = parts
        for seg in (kb_id, doc_id):
            if not _SAFE_SEGMENT.fullmatch(seg):
                return None
        if not re.fullmatch(r"p[1-9][0-9]*\.png", filename):
            return None
        candidate = _base_dir() / kb_id / doc_id / filename
        resolved = candidate.resolve()
        if not resolved.is_file():
            return None
        # Containment: the resolved file must live under the base dir
        # (symlinked tmp dirs resolve differently — compare resolved forms).
        try:
            resolved.relative_to(_base_dir().resolve())
        except ValueError:
            return None
        return resolved
    except Exception:
        return None


def save_page_image(kb_id: str, doc_id: str, page: int, png_bytes: bytes) -> str:
    """Persist one rendered page; return its relative ref (os.path.join form)."""
    _check_segment(kb_id, "kb_id")
    _check_segment(doc_id, "doc_id")
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise ValueError(f"Invalid page number for page-image storage: {page!r}")
    if not isinstance(png_bytes, (bytes, bytearray)) or not png_bytes:
        raise ValueError("Empty page-image bytes are never stored")
    dest = _base_dir() / kb_id / doc_id / f"p{page}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(bytes(png_bytes))
    return os.path.join(kb_id, doc_id, f"p{page}.png")


def resolve_page_image_path(ref: str) -> Path | None:
    """Map a stored ref back to its file, or None for bad/unknown refs."""
    return _ref_path(ref)


def copy_page_image(src_ref: str, dest_kb_id: str, dest_doc_id: str) -> str | None:
    """Copy a stored image into another doc's tree (snapshots own COPIES).

    Returns the new ref, or None when the source does not resolve. The page
    number rides along (pN.png → pN.png). Never raises.
    """
    try:
        _check_segment(dest_kb_id, "kb_id")
        _check_segment(dest_doc_id, "doc_id")
        src = _ref_path(src_ref)
        if src is None:
            return None
        dest = _base_dir() / dest_kb_id / dest_doc_id / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        return os.path.join(dest_kb_id, dest_doc_id, src.name)
    except Exception as exc:
        logger.warning("Page-image copy failed", src_ref=src_ref, error=str(exc))
        return None


def delete_doc_page_images(kb_id: str, doc_id: str) -> int:
    """Remove one document's image tree. Returns files removed; never raises."""
    try:
        _check_segment(kb_id, "kb_id")
        _check_segment(doc_id, "doc_id")
        tree = _base_dir() / kb_id / doc_id
        files = list(tree.rglob("*.png")) if tree.is_dir() else []
        shutil.rmtree(tree, ignore_errors=True)
        return len(files)
    except Exception as exc:
        logger.warning("Page-image doc purge failed", kb_id=kb_id, error=str(exc))
        return 0


def delete_kb_page_images(kb_id: str) -> int:
    """Remove a whole KB image tree. Returns files removed; never raises."""
    try:
        _check_segment(kb_id, "kb_id")
        tree = _base_dir() / kb_id
        files = list(tree.rglob("*.png")) if tree.is_dir() else []
        shutil.rmtree(tree, ignore_errors=True)
        return len(files)
    except Exception as exc:
        logger.warning("Page-image KB purge failed", kb_id=kb_id, error=str(exc))
        return 0
