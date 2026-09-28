"""
Route-level tests for the two heaviest untested handlers (audit B-8):

* POST /knowledge-bases/{id}/documents            (knowledge_bases.py:157-228)
* POST /knowledge-bases/{id}/documents/from-url   (knowledge_bases.py:264-359)

Together these were 130+ uncovered statements on the primary user-facing write
path, with ZERO coverage of the extension, size, and SSRF branches. The upload
handler is the only place user bytes enter the system, so its guards are
security-relevant, not just test coverage.

KB ownership is enforced inside `kb_service.add_document` via `get_kb`, so that
is where the tenant guards are exercised.
"""

from __future__ import annotations

import hashlib
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.schemas.kb import DocResponse
from app.main import app

KB_ID = "64ee39d09c6292376e191982"
USER_ID = "64ee39d09c6292376e191981"
OTHER_USER_ID = "64ee39d09c6292376e199001"

client = TestClient(app)


@pytest.fixture
def auth_user():
    user = {
        "_id": ObjectId(USER_ID),
        "email": "upload@example.com",
        "hashed_password": "x",
        "is_active": True,
    }
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.clear()


def _doc_response() -> DocResponse:
    """A real DocResponse so serialisation is exercised, not mocked."""
    return DocResponse(
        id="64ee39d09c6292376e1919ab",
        filename="policy.txt",
        file_size=12,
        content_hash="deadbeef",
        knowledge_base_id=KB_ID,
        created_at="2026-08-27T10:00:00Z",
        ingestion_status="PENDING",
        effective_from=None,
        effective_until=None,
        error_message=None,
    )


class _Capture:
    """Records add_document kwargs so the test can assert what was persisted."""

    def __init__(self) -> None:
        self.kwargs: dict = {}
        self.calls = 0

    async def __call__(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return _doc_response()


def _chunker(chunks: list[dict] | None = None) -> MagicMock:
    strategy = MagicMock()
    strategy.chunk = MagicMock(return_value=chunks if chunks is not None else [{"text": "c1"}])
    return strategy


def _parse() -> MagicMock:
    return MagicMock(return_value=([{"text": "Refunds within 30 days.", "page": 1}], None, None))


def _upload_files(filename: str, payload: bytes) -> dict:
    return {"file": (filename, io.BytesIO(payload), "text/plain")}


# ─── Upload: happy path ───────────────────────────────────────────────────────


def test_upload_accepts_a_supported_file(auth_user):
    """201, the record is written, and the chunker is invoked. A missing
    background task means documents are stored but never searchable — silently."""
    capture = _Capture()
    strategy = _chunker()

    with (
        patch("app.api.v1.knowledge_bases.parse_document", _parse()),
        patch("app.api.v1.knowledge_bases.get_chunking_strategy", return_value=strategy),
        patch("app.api.v1.knowledge_bases.kb_service.add_document", capture),
        patch("app.api.v1.knowledge_bases.index_parsed_chunks", AsyncMock()),
    ):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents",
            files=_upload_files("policy.txt", b"Refunds rtn."),
        )

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "policy.txt"
    assert body["ingestion_status"] == "PENDING"
    assert capture.calls == 1, "document record was never created"
    assert strategy.chunk.called, "chunker was never invoked"


def test_upload_computes_a_stable_content_hash(auth_user):
    """Content hashing de-duplicates re-uploads; without it the same bytes get
    indexed repeatedly under different ids."""
    payload = b"Refunds rtn."
    capture = _Capture()

    with (
        patch("app.api.v1.knowledge_bases.parse_document", _parse()),
        patch("app.api.v1.knowledge_bases.get_chunking_strategy", return_value=_chunker()),
        patch("app.api.v1.knowledge_bases.kb_service.add_document", capture),
        patch("app.api.v1.knowledge_bases.index_parsed_chunks", AsyncMock()),
    ):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents",
            files=_upload_files("policy.txt", payload),
        )

    assert r.status_code == 201, r.text
    assert capture.kwargs.get("content_hash") == hashlib.sha256(payload).hexdigest()


def test_upload_derives_filename_from_the_path_and_strips_nulls(auth_user):
    """Path traversal in the client-supplied filename must not survive into the
    stored record."""
    capture = _Capture()
    traversal = "../../etc/passwd.txt"

    with (
        patch("app.api.v1.knowledge_bases.parse_document", _parse()),
        patch("app.api.v1.knowledge_bases.get_chunking_strategy", return_value=_chunker()),
        patch("app.api.v1.knowledge_bases.kb_service.add_document", capture),
        patch("app.api.v1.knowledge_bases.index_parsed_chunks", AsyncMock()),
    ):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents",
            files=_upload_files(traversal, b"data"),
        )

    assert r.status_code == 201, r.text
    stored = capture.kwargs.get("filename", "")
    assert "/" not in stored and ".." not in stored, f"traversal survived: {stored!r}"
    assert stored.endswith(".txt")


# ─── Upload: guards ───────────────────────────────────────────────────────────


def test_upload_rejects_unsupported_extension(auth_user):
    """An .exe must never reach the parser."""
    r = client.post(
        f"/api/v1/knowledge-bases/{KB_ID}/documents",
        files={"file": ("payload.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
    )
    assert r.status_code in (400, 415, 422), f"expected a rejection, got {r.status_code}"


def test_upload_rejects_oversize_file(auth_user):
    """The size guard is a streaming read, so it must trip before buffering the
    whole payload into memory."""
    from app.core.config import get_model_config

    limit = get_model_config().max_file_size_mb
    oversize = b"a" * ((limit + 1) * 1024 * 1024)

    r = client.post(
        f"/api/v1/knowledge-bases/{KB_ID}/documents",
        files=_upload_files("big.txt", oversize),
    )
    assert r.status_code in (400, 413, 422), f"expected a size rejection, got {r.status_code}"


def test_upload_of_empty_file_does_not_crash(auth_user):
    """An empty upload has nothing to index. Whatever the route decides, it must
    not 500 in the parser."""
    with (
        patch("app.api.v1.knowledge_bases.get_chunking_strategy", return_value=_chunker([])),
        patch("app.api.v1.knowledge_bases.kb_service.add_document", _Capture()),
        patch("app.api.v1.knowledge_bases.index_parsed_chunks", AsyncMock()),
    ):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents",
            files=_upload_files("empty.txt", b""),
        )
    assert r.status_code in (201, 400, 413, 415, 422), f"got {r.status_code}: {r.text[:200]}"


def test_upload_to_foreign_kb_is_refused(auth_user):
    """Cross-tenant guard: ownership is enforced inside kb_service.add_document."""
    from app.core.exceptions import AuthorizationError

    async def _deny(*_a, **_k):
        raise AuthorizationError("Not your knowledge base")

    with patch("app.services.kb_service.get_kb", _deny):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents",
            files=_upload_files("policy.txt", b"data"),
        )
    assert r.status_code in (403, 404), f"cross-tenant upload not refused: {r.status_code}"


def test_upload_against_missing_kb_is_refused(auth_user):
    from app.core.exceptions import NotFoundError

    async def _missing(*_a, **_k):
        raise NotFoundError("Knowledge base not found")

    with patch("app.services.kb_service.get_kb", _missing):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents",
            files=_upload_files("policy.txt", b"data"),
        )
    assert r.status_code == 404, f"missing KB should be 404, got {r.status_code}"


# ─── URL ingest: SSRF guards ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/private",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "http://[::1]/x",
    ],
)
def test_url_ingest_blocks_ssrf_targets(url, auth_user):
    """This is the SSRF boundary. A poisoned retrieved document must not make the
    server fetch cloud metadata or a local file."""
    r = client.post(
        f"/api/v1/knowledge-bases/{KB_ID}/documents/from-url",
        json={"url": url},
    )
    assert r.status_code in (400, 403, 422), f"SSRF target not blocked: {url} -> {r.status_code}"


def test_url_ingest_reports_fetch_failure(auth_user):
    """A fetch failure must surface as 400 with a reason, not a 500."""
    with patch(
        "app.api.v1.knowledge_bases.fetch_document_from_url",
        AsyncMock(return_value=(None, "connection reset")),
    ):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents/from-url",
            json={"url": "https://en.wikipedia.org/wiki/Refund_policy"},
        )
    assert r.status_code == 400, f"expected 400 on fetch failure, got {r.status_code}"
    assert "connection reset" in r.text.lower()


def test_url_ingest_happy_path(auth_user):
    capture = _Capture()
    with (
        patch(
            "app.api.v1.knowledge_bases.fetch_document_from_url",
            AsyncMock(return_value=(b"Refunds within 30 days.", None)),
        ),
        patch("app.api.v1.knowledge_bases.parse_document", _parse()),
        patch("app.api.v1.knowledge_bases.get_chunking_strategy", return_value=_chunker()),
        patch("app.api.v1.knowledge_bases.kb_service.add_document", capture),
        patch("app.api.v1.knowledge_bases.index_parsed_chunks", AsyncMock()),
    ):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents/from-url",
            json={"url": "https://en.wikipedia.org/wiki/Refund_policy"},
        )

    assert r.status_code == 201, r.text
    assert capture.calls == 1


def test_url_ingest_rejects_oversize_fetch(auth_user):
    """A remote document that exceeds the size cap must be rejected before
    parsing, even though the caller sent no bytes."""
    from app.core.config import get_model_config

    limit = get_model_config().max_file_size_mb
    huge = b"a" * ((limit + 1) * 1024 * 1024)
    with patch(
        "app.api.v1.knowledge_bases.fetch_document_from_url",
        AsyncMock(return_value=(huge, None)),
    ):
        r = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents/from-url",
            json={"url": "https://en.wikipedia.org/wiki/Big"},
        )
    assert r.status_code in (400, 413, 422), f"expected a size rejection, got {r.status_code}"
