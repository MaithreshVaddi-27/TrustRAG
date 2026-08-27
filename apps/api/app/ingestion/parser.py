"""
TRUSTRAG — Document parsers for PDF, TXT, and MD files.

Page-by-page extraction for PDFs (PyMuPDF) and encoding detection (chardet).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, BinaryIO

import chardet
import fitz  # PyMuPDF

from app.core.exceptions import IngestionError, UnsupportedFormatError
from app.core.logging import get_logger

logger = get_logger(__name__)

# ISO format matching: YYYY-MM-DD
DATE_PATTERN_FROM = re.compile(r"effective\s+from:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
DATE_PATTERN_UNTIL = re.compile(r"effective\s+until:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


def extract_dates(text: str) -> tuple[datetime | None, datetime | None]:
    """
    Search text for metadata expressions indicating effective periods:
      - 'Effective from: YYYY-MM-DD'
      - 'Effective until: YYYY-MM-DD'
    """
    eff_from = None
    eff_until = None

    # Scan first 2000 characters for metadata headers
    header_snippet = text[:2000]

    match_from = DATE_PATTERN_FROM.search(header_snippet)
    if match_from:
        try:
            eff_from = datetime.strptime(match_from.group(1), "%Y-%m-%d")
        except ValueError:
            pass

    match_until = DATE_PATTERN_UNTIL.search(header_snippet)
    if match_until:
        try:
            eff_until = datetime.strptime(match_until.group(1), "%Y-%m-%d")
        except ValueError:
            pass

    return eff_from, eff_until


def parse_pdf(stream: BinaryIO) -> list[dict[str, Any]]:
    """
    Parse a PDF file page-by-page.
    Returns a list of dicts: [{"page": page_num, "text": page_text}].
    """
    pages = []
    try:
        # Open PDF from byte stream
        doc = fitz.open(stream=stream.read(), filetype="pdf")
        for i, page in enumerate(doc):
            text = page.get_text()
            pages.append({"page": i + 1, "text": text.strip()})
        return pages
    except Exception as exc:
        raise IngestionError("Failed to parse PDF document", detail=str(exc)) from exc


def parse_txt_or_md(stream: BinaryIO) -> list[dict[str, Any]]:
    """
    Parse a text or Markdown file.
    Detects encoding using chardet before reading.
    """
    raw_bytes = stream.read()
    if not raw_bytes:
        return [{"page": 1, "text": ""}]

    # Detect encoding
    detected = chardet.detect(raw_bytes)
    encoding = detected.get("encoding") or "utf-8"

    try:
        text = raw_bytes.decode(encoding, errors="replace")
        return [{"page": 1, "text": text.strip()}]
    except Exception as exc:
        raise IngestionError(
            f"Failed to decode text file using encoding '{encoding}'", detail=str(exc)
        ) from exc


def parse_document(
    filename: str, stream: BinaryIO
) -> tuple[list[dict[str, Any]], datetime | None, datetime | None]:
    """
    Determine format and parse document bytes.
    Extracts temporal validity metadata if present.
    """
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        pages = parse_pdf(stream)
    elif ext in (".txt", ".md"):
        pages = parse_txt_or_md(stream)
    else:
        raise UnsupportedFormatError(f"Unsupported file format '{ext}' during ingestion")

    # Combine text snippet to extract dates
    full_text = "\n".join(p["text"] for p in pages)
    eff_from, eff_until = extract_dates(full_text)

    return pages, eff_from, eff_until
