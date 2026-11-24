"""
CI-safe smoke for the launch-critical path:

    register -> knowledge base -> document upload -> analysis -> detail

The external boundaries (user store, KB store, parser, embedder, analysis
worker) are mocked; the FastAPI routing, schemas, dependency injection and the
public wire shapes are real. This is the deterministic counterpart to the live
end-to-end run recorded in docs/PROJECT_STATUS_AND_AUDIT.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.schemas.analysis import AnalysisResponse, DiagnosisSummary, ReliabilitySummary
from app.api.v1.schemas.auth import UserResponse
from app.api.v1.schemas.kb import DocResponse, KBResponse
from app.main import app

USER_ID = "64ee39d09c6292376e191981"
KB_ID = "64ee39d09c6292376e191982"
DOC_ID = "64ee39d09c6292376e1919ab"
ANALYSIS_ID = "64ee39d09c6292376e1919ac"
NOW = datetime.now(UTC)

client = TestClient(app)


@pytest.fixture
def current_user():
    user = {
        "_id": ObjectId(USER_ID),
        "email": "launch@example.com",
        "hashed_password": "x",
        "is_active": True,
    }
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.clear()


def _user_response() -> UserResponse:
    return UserResponse(
        id=USER_ID,
        email="launch@example.com",
        full_name="Launch Smoke",
        is_active=True,
        created_at=NOW,
    )


def _kb_response() -> KBResponse:
    return KBResponse(
        id=KB_ID,
        name="Launch smoke",
        description="CI-safe path check",
        user_id=USER_ID,
        document_count=0,
        created_at=NOW,
        version="1.0",
        parent_kb_id=None,
        is_snapshot=False,
        embedding_model=None,
        embedding_dim=None,
    )


def _doc_response() -> DocResponse:
    return DocResponse(
        id=DOC_ID,
        filename="service-api.md",
        file_size=12,
        content_hash="a" * 64,
        knowledge_base_id=KB_ID,
        created_at=NOW,
        ingestion_status="completed",
        effective_from=None,
        effective_until=None,
        error_message=None,
    )


def _analysis_response() -> AnalysisResponse:
    return AnalysisResponse(
        id=ANALYSIS_ID,
        user_id=USER_ID,
        knowledge_base_id=KB_ID,
        query="What is the default request rate limit?",
        status="completed",
        answer="50 requests per second per tenant.",
        reliability=ReliabilitySummary(score=1.0, status="TRUSTED"),
        diagnosis=DiagnosisSummary(type="NONE", failures=[]),
        created_at=NOW,
    )


def test_register_kb_document_analysis_detail_chain(current_user):
    """A fresh user can reach a verified detail payload in four HTTP calls."""
    with patch(
        "app.api.v1.auth.auth_service.register_user",
        AsyncMock(return_value=_user_response()),
    ):
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": "launch@example.com",
                "password": "Str0ng!Passphrase2026",
                "full_name": "Launch Smoke",
            },
        )
    assert reg.status_code == 201, reg.text
    assert reg.json()["id"] == USER_ID

    with patch(
        "app.api.v1.knowledge_bases.kb_service.create_kb",
        AsyncMock(return_value=_kb_response()),
    ):
        kb = client.post(
            "/api/v1/knowledge-bases",
            json={"name": "Launch smoke", "description": "CI-safe path check"},
        )
    assert kb.status_code == 201, kb.text
    assert kb.json()["id"] == KB_ID

    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[{"text": "50 requests per second.", "page": 1}])
    with (
        patch(
            "app.api.v1.knowledge_bases.parse_document",
            MagicMock(return_value=([{"text": "50 requests per second.", "page": 1}], None, None)),
        ),
        patch("app.api.v1.knowledge_bases.get_chunking_strategy", return_value=chunker),
        patch("app.api.v1.knowledge_bases.kb_service.get_kb", AsyncMock()),
        patch(
            "app.api.v1.knowledge_bases.kb_service.add_document",
            AsyncMock(return_value=_doc_response()),
        ),
        # The embedder is the expensive external boundary; indexing must be
        # scheduled or documents are stored but never searchable.
        patch("app.api.v1.knowledge_bases.index_parsed_chunks", AsyncMock()) as index_task,
    ):
        upload = client.post(
            f"/api/v1/knowledge-bases/{KB_ID}/documents",
            files={"file": ("service-api.md", b"50 requests per second.", "text/plain")},
        )
    assert upload.status_code == 201, upload.text
    assert upload.json()["id"] == DOC_ID
    index_task.assert_awaited()

    with patch(
        "app.api.v1.analyses.analysis_service.create_analysis",
        AsyncMock(return_value=_analysis_response()),
    ) as create:
        analysis = client.post(
            "/api/v1/analyses",
            json={"knowledge_base_id": KB_ID, "query": "What is the default request rate limit?"},
        )
    assert analysis.status_code == 201, analysis.text
    assert analysis.json()["reliability"] == {"score": 1.0, "status": "TRUSTED"}
    create.assert_awaited()

    detail_payload = {
        "analysis": analysis.json(),
        "claims": [{"id": "c1", "text": "Rate limit is 50 rps.", "state": "SUPPORTED"}],
        "evidence": [
            {"id": "e1", "text": "50 requests per second.", "integrity_status": "VERIFIED"}
        ],
        "trace": [{"event": "analysis.completed"}],
    }
    with patch(
        "app.api.v1.analyses.analysis_service.get_analysis_detail",
        AsyncMock(return_value=detail_payload),
    ):
        detail = client.get(f"/api/v1/analyses/{ANALYSIS_ID}/detail")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["claims"][0]["state"] == "SUPPORTED"
    assert body["evidence"][0]["integrity_status"] == "VERIFIED"
