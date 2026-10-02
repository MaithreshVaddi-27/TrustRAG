"""
TRUSTRAG — Document parsers for PDF, DOCX, TXT, MD, CSV, JSON, and HTML files.

Extracts document text and temporal validity metadata.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, BinaryIO

import pymupdf as fitz

from app.core.config import get_model_config
from app.core.exceptions import IngestionError, UnsupportedFormatError
from app.core.logging import get_logger
from app.rag.ingestion import ocr as ocr_module

logger = get_logger(__name__)

# ISO format matching: YYYY-MM-DD
DATE_PATTERN_FROM = re.compile(
    r"effective\s+from:\s*(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

DATE_PATTERN_UNTIL = re.compile(
    r"effective\s+until:\s*(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def validate_magic_bytes(filename: str, stream: BinaryIO) -> None:
    """
    Validate file signature (magic bytes) matches the declared extension.
    Reads minimal bytes from stream start; stream position is preserved.
    """
    MAGIC_BYTES = {".pdf": [b"%PDF"], ".docx": [b"PK\x03\x04"]}  # noqa: N806
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in MAGIC_BYTES:
        return  # No signature check for this format

    expected_signatures = MAGIC_BYTES[ext]
    pos = stream.tell()
    try:
        header = stream.read(16)
        if not header:
            raise IngestionError("Empty file", detail=f"File '{filename}' has no content")
        for sig in expected_signatures:
            if header.startswith(sig):
                return  # Valid signature
        raise IngestionError(
            "File signature mismatch",
            detail=(
                f"File '{filename}' has extension '{ext}' but content "
                "does not match expected format"
            ),
        )
    finally:
        stream.seek(pos)


def _decode_utf8(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        pass
    # Fallback: detected encoding (head-sampled, never the whole file).
    encoding = _detect_encoding(raw_bytes)
    try:
        return raw_bytes.decode(encoding, errors="replace")
    except Exception as exc:
        raise IngestionError(
            "File is not valid UTF-8",
            detail="TrustRAG accepts UTF-8 encoded text files.",
        ) from exc


# Head sample bound for encoding detection: chardet sees the first 64KB
# only, so a 2MB upload never pays full-buffer detection (RAM + time).
_ENCODING_DETECT_SLICE = 65536


def _detect_encoding(raw_bytes: bytes) -> str:
    """Detect text encoding from a head sample (never the whole buffer)."""
    import chardet

    sample = bytes(raw_bytes[:_ENCODING_DETECT_SLICE])
    detected = chardet.detect(sample) or {}
    return str(detected.get("encoding") or "utf-8")


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
        with contextlib.suppress(ValueError):
            eff_from = datetime.strptime(match_from.group(1), "%Y-%m-%d").replace(tzinfo=UTC)

    match_until = DATE_PATTERN_UNTIL.search(header_snippet)
    if match_until:
        with contextlib.suppress(ValueError):
            eff_until = datetime.strptime(match_until.group(1), "%Y-%m-%d").replace(tzinfo=UTC)

    return eff_from, eff_until


MAX_PDF_PAGES = 500
MAX_RENDER_PIXELS = 25_000_000  # ~25MP cap per OCR render (RAM guard)


def parse_pdf(stream: BinaryIO) -> list[dict[str, Any]]:
    """
    Parse a PDF file page-by-page.
    Returns a list of dicts: [{"page": page_num, "text": page_text,
    "ocr_used": bool, "ocr_confidence": float | None,
    "page_image_png": bytes | None}, ...].

    Pages with sufficient native text keep native extraction. Pages below the
    native-text density threshold fall back to RapidOCR-ONNX (ingestion.ocr.*)
    when enabled. OCR failures fail open to whatever native text exists.
    """
    cfg = get_model_config()
    try:
        raw = stream.read()
        with fitz.open(stream=raw, filetype="pdf") as doc:
            if len(doc) > MAX_PDF_PAGES:
                raise IngestionError(
                    "PDF exceeds page limit",
                    detail=f"PDF has {len(doc)} pages, limit is {MAX_PDF_PAGES}",
                )
            pages = []
            for i, page in enumerate(doc):
                native_text = page.get_text().strip()
                text, ocr_used, ocr_confidence = native_text, False, None
                page_image_png: bytes | None = None
                if cfg.ocr_enabled and ocr_module.should_ocr_page(
                    native_text, cfg.ocr_min_native_chars
                ):
                    try:
                        pix = page.get_pixmap(dpi=cfg.ocr_dpi)
                        if pix.w * pix.h > MAX_RENDER_PIXELS:
                            # Downscale render: huge pages (e.g. A0 at 300dpi)
                            # would spike RAM. Halve DPI and re-render.
                            pix = page.get_pixmap(dpi=max(72, cfg.ocr_dpi // 2))
                            if pix.w * pix.h > MAX_RENDER_PIXELS:
                                logger.warning(
                                    "OCR render exceeds pixel cap; keeping native text",
                                    page=i + 1,
                                    pixels=pix.w * pix.h,
                                )
                                raise ValueError("OCR render exceeds pixel cap")
                        png_bytes = pix.tobytes("png")
                        ocr_result = ocr_module.ocr_image_bytes(
                            png_bytes,
                            min_confidence=cfg.ocr_min_confidence,
                        )
                        text = ocr_result.text.strip()
                        ocr_used, ocr_confidence = True, ocr_result.confidence
                        # Page-image chain: keep the exact rendered pixels the
                        # engine read so chunks can link to the image. Only when
                        # persistence is enabled (models.yaml ingestion.ocr.
                        # store_page_images) — otherwise renders cost RAM/disk
                        # for nothing. Native/fallback pages carry None.
                        page_image_png = png_bytes if cfg.ocr_store_page_images else None

                        logger.info(
                            "OCR fallback used for PDF page",
                            page=i + 1,
                            confidence=ocr_confidence,
                        )
                    except Exception as exc:
                        # Fail open: a broken OCR page must not kill ingestion
                        # of the whole document; keep whatever native text exists.
                        logger.warning(
                            "OCR fallback failed; keeping native page text",
                            page=i + 1,
                            error=str(exc),
                        )
                pages.append(
                    {
                        "page": i + 1,
                        "text": text,
                        "ocr_used": ocr_used,
                        "ocr_confidence": ocr_confidence,
                        "page_image_png": page_image_png,
                    }
                )
            return pages
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("Failed to parse PDF document", detail=str(exc)) from exc


def parse_csv(stream: BinaryIO) -> list[dict[str, Any]]:
    """Parse a UTF-8 CSV file with a required header row."""
    raw_bytes = stream.read()

    if not raw_bytes:
        raise IngestionError(
            "CSV file is empty",
            detail="CSV files must contain a header row.",
        )

    text = _decode_utf8(raw_bytes)

    try:
        rows = list(csv.reader(io.StringIO(text)))

        if not rows:
            raise IngestionError(
                "CSV file is empty",
                detail="CSV files must contain a header row.",
            )

        headers = [header.strip() for header in rows[0]]

        if not headers or not any(headers):
            raise IngestionError(
                "CSV header is missing",
                detail="The first row of a CSV file must contain column headers.",
            )

        if len(set(headers)) != len(headers):
            raise IngestionError(
                "CSV header contains duplicate columns",
                detail="Each CSV column must have a unique header.",
            )

        column_count = len(headers)

        for row_number, row in enumerate(rows[1:], start=2):
            if not row:
                continue

            if len(row) != column_count:
                raise IngestionError(
                    "Invalid CSV row",
                    detail=(f"Row {row_number} has {len(row)} columns; expected {column_count}."),
                )

        formatted_rows = []

        for row in rows[1:]:
            if not row:
                continue

            formatted_rows.append(
                " | ".join(
                    f"{header}: {value.strip()}" for header, value in zip(headers, row, strict=True)
                )
            )

        return [
            {
                "page": 1,
                "text": "\n".join(formatted_rows),
            }
        ]

    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(
            "Failed to parse CSV document",
            detail=str(exc),
        ) from exc


def parse_json(stream: BinaryIO) -> list[dict[str, Any]]:
    raw_bytes = stream.read()
    if not raw_bytes:
        return [{"page": 1, "text": ""}]

    try:
        text_content = _decode_utf8(raw_bytes)
        data = json.loads(text_content)
        formatted_text = json.dumps(data, indent=2, ensure_ascii=False)
        return [{"page": 1, "text": formatted_text.strip()}]
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("Failed to parse JSON document", detail=str(exc)) from exc


def parse_txt_or_md(stream: BinaryIO) -> list[dict[str, Any]]:
    raw_bytes = stream.read()
    if not raw_bytes:
        return [{"page": 1, "text": ""}]

    text = _decode_utf8(raw_bytes)
    return [{"page": 1, "text": text.strip()}]


class _HTMLTextExtractor(HTMLParser):
    """Stdlib tag stripper: block tags break lines, script/style dropped."""

    _BLOCK_TAGS = frozenset(
        {
            "p",
            "div",
            "section",
            "article",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "ul",
            "ol",
            "br",
            "tr",
            "table",
            "header",
            "footer",
        }
    )
    _SKIP_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif tag in self._BLOCK_TAGS and not self._skip_depth:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK_TAGS and not self._skip_depth:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        collapsed = re.sub(r"[ \t]+", " ", "".join(self._parts))
        return re.sub(r"\n\s*\n+", "\n", collapsed).strip()


def parse_html(stream: BinaryIO) -> list[dict[str, Any]]:
    """Parse HTML/HTM: strip tags (stdlib, no dep), keep readable text."""
    raw_bytes = stream.read()
    if not raw_bytes:
        return [{"page": 1, "text": ""}]
    try:
        extractor = _HTMLTextExtractor()
        extractor.feed(_decode_utf8(raw_bytes))
        return [{"page": 1, "text": extractor.text()}]
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("Failed to parse HTML document", detail=str(exc)) from exc


# Zip-bomb ceiling for DOCX: compressed archives that expand past this are
# rejected before XML parsing (RAM guard, not a format judgment).
_DOCX_MAX_EXPANDED_BYTES = 10 * 1024 * 1024


def parse_docx(stream: BinaryIO) -> list[dict[str, Any]]:
    """Parse DOCX via stdlib zipfile + defusedxml (no python-docx needed).

    Security: decompressed-size cap (zip bomb), XXE-safe parsing
    (defusedxml forbids entities — the XXE test vector raises instead of
    resolving file:///etc/passwd), document.xml must exist.
    """
    from defusedxml import ElementTree as DETree

    try:
        raw = stream.read()
    except Exception as exc:
        raise IngestionError("Failed to read DOCX document", detail=str(exc)) from exc
    if not raw:
        raise IngestionError("Empty file", detail="DOCX file has no content")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            try:
                info = zf.getinfo("word/document.xml")
            except KeyError as exc:
                raise IngestionError(
                    "Invalid DOCX document", detail="word/document.xml missing"
                ) from exc
            if info.file_size > _DOCX_MAX_EXPANDED_BYTES:
                raise IngestionError(
                    "DOCX decompression bomb suspected",
                    detail=(
                        f"word/document.xml expands to {info.file_size} bytes "
                        f"(limit {_DOCX_MAX_EXPANDED_BYTES})"
                    ),
                )
            # Ratio guard: a 2MB-of-zeros document.xml compresses ~1000:1 —
            # well past any legitimate Office XML (~10:1). Absolute size
            # alone would miss it.
            if info.file_size > 1024 * 1024 and info.file_size / max(1, info.compress_size) > 100:
                raise IngestionError(
                    "DOCX decompression bomb suspected",
                    detail=(
                        "word/document.xml compression ratio "
                        f"{info.file_size / max(1, info.compress_size):.0f}:1 "
                        "exceeds the 100:1 ceiling"
                    ),
                )
            xml_bytes = zf.read("word/document.xml")
            if len(xml_bytes) > _DOCX_MAX_EXPANDED_BYTES:
                raise IngestionError(
                    "DOCX decompression bomb suspected",
                    detail="word/document.xml exceeds the expanded-size limit",
                )
    except IngestionError:
        raise
    except zipfile.BadZipFile as exc:
        raise IngestionError("Invalid DOCX document", detail="Not a ZIP archive") from exc
    except Exception as exc:
        raise IngestionError("Failed to parse DOCX document", detail=str(exc)) from exc
    try:
        root = DETree.fromstring(xml_bytes)
    except Exception as exc:
        # defusedxml.EntitiesForbidden (XXE) lands here: never resolve.
        raise IngestionError("Invalid DOCX document XML", detail=str(exc)[:200]) from exc
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts = [(t.text or "") for t in root.findall(".//w:t", ns) if (t.text or "").strip() != ""]
    return [{"page": 1, "text": "\n".join(texts).strip()}]


def _validate_file_size(filename: str, stream: BinaryIO) -> None:
    cfg = get_model_config()
    max_bytes = int(cfg.max_file_size_mb * 1024 * 1024)

    pos = stream.tell()
    try:
        stream.seek(0, 2)
        size = stream.tell()
    finally:
        stream.seek(pos)

    if size > max_bytes:
        size_mb = size / (1024 * 1024)
        raise IngestionError(
            "File exceeds size limit",
            detail=f"File '{filename}' is {size_mb:.1f}MB, limit is {cfg.max_file_size_mb}MB",
        )


def parse_document(
    filename: str, stream: BinaryIO
) -> tuple[list[dict[str, Any]], datetime | None, datetime | None]:
    """
    Determine format and parse document bytes across all supported extensions.
    Extracts temporal validity metadata if present.
    """
    _validate_file_size(filename, stream)
    # AV scan before magic-byte validation (malware may masquerade)
    scan_for_malware(stream)
    # Validate magic bytes before parsing
    validate_magic_bytes(filename, stream)

    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        pages = parse_pdf(stream)
    elif ext in (".txt", ".md"):
        pages = parse_txt_or_md(stream)
    elif ext == ".csv":
        pages = parse_csv(stream)
    elif ext == ".json":
        pages = parse_json(stream)
    elif ext in (".html", ".htm"):
        pages = parse_html(stream)
    elif ext == ".docx":
        pages = parse_docx(stream)
    else:
        raise UnsupportedFormatError(f"Unsupported file format '{ext}' during ingestion")

    # Combine text snippet to extract dates
    full_text = "\n".join(p["text"] for p in pages)
    eff_from, eff_until = extract_dates(full_text)

    return pages, eff_from, eff_until


EICAR_TEST_STRING = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def _scan_eicar(stream: BinaryIO) -> None:
    """Built-in EICAR self-test: dependency-free, split-boundary safe.

    ClamAV runs only where a daemon exists (rare in dev/docker); without
    this check the "AV scan" would be theater on exactly the hosts that
    need it. Reads in 64KB chunks with a holdover so a signature split
    across a chunk boundary still trips. Stream position is preserved.
    """
    sig = EICAR_TEST_STRING
    holdover = b""
    try:
        pos = stream.tell()
    except Exception:
        pos = None
    try:
        stream.seek(0)
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            window = holdover + chunk
            if sig in window:
                raise IngestionError(
                    "EICAR test signature detected",
                    detail="Upload blocked: AV self-test signature present.",
                )
            holdover = window[-(len(sig) - 1) :] if len(sig) > 1 else b""
    finally:
        if pos is not None:
            try:
                stream.seek(pos)
            except Exception:
                logger.debug("Failed to restore stream position after EICAR scan")


def scan_for_malware(stream: BinaryIO) -> None:
    """Scan the upload: built-in EICAR self-test first, then ClamAV when available."""
    _scan_eicar(stream)
    try:
        pos = stream.tell()
    except Exception:
        pos = None

    try:
        try:
            import pyclamd  # type: ignore
        except ImportError:
            logger.debug("pyclamd unavailable, skipping AV scan")
            return

        try:
            stream.seek(0)
            cd = pyclamd.ClamdNetworkSocket()

            if not cd.ping():
                logger.debug("ClamAV daemon unavailable, skipping AV scan")
                return

            result = cd.scan_stream(stream.read())

        except Exception:
            logger.debug("ClamAV daemon unavailable, skipping AV scan")
            return

        if result:
            raise IngestionError(
                "Malware detected by AV engine",
                detail=str(result),
            )

    finally:
        if pos is not None:
            try:
                stream.seek(pos)
            except Exception:
                logger.debug("Failed to restore stream position after AV scan")
