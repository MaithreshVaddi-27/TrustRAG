"""
Tests for the exception handlers and request-ID middleware (audit B-11 remainder).

`_register_exception_handlers` (`main.py:277-393`) and `request_id_middleware`
(`main.py:405-...`) were uncovered. These are the responses a user actually
sees on failure, and the generic handler is the app's last line of defence
against leaking stack traces — so their behaviour is security-relevant, not
just coverage.

The contract pinned here is the nested envelope `{"error": {"code", "message"}}`
plus the status code each exception class maps to.
"""

from __future__ import annotations

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import _register_exception_handlers, request_id_middleware

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-]{1,64}$")


def _app_with_route(exc: Exception, path: str = "/boom") -> TestClient:
    app = FastAPI()
    _register_exception_handlers(app)

    @app.get(path)
    async def _boom():
        raise exc

    @app.middleware("http")
    async def _mw(request, call_next):
        return await request_id_middleware(request, call_next)

    return TestClient(app, raise_server_exceptions=False)


# Each row: (exception instance, expected status, expected error code).
# The status/code pairs are the wire contract the frontend switches on.
# Extracted from _register_exception_handlers (app/main.py:277-393). Dependency
# errors are the caller's fault (4xx); infrastructure and configuration failures
# are "the service cannot serve right now" (503), which tells a client to retry
# rather than to treat the request as malformed.
_CASES = [
    ("AuthenticationError", 401, "UNAUTHORIZED"),
    ("AuthorizationError", 403, "FORBIDDEN"),
    ("NotFoundError", 404, "NOT_FOUND"),
    ("AnalysisNotFoundError", 404, "NOT_FOUND"),
    ("ConflictError", 409, "CONFLICT"),
    ("UnsupportedFormatError", 422, "UNSUPPORTED_FORMAT"),
    ("FileTooLargeError", 413, "FILE_TOO_LARGE"),
    ("IngestionError", 422, "INGESTION_ERROR"),
    ("InputValidationError", 422, "VALIDATION_ERROR"),
    # Retryable: the model server, the DB, or the vector store is unavailable.
    ("LLMUnavailableError", 503, "LLM_UNAVAILABLE"),
    ("ConfigurationError", 503, "CONFIGURATION_ERROR"),
    ("DatabaseError", 503, "SERVICE_UNAVAILABLE"),
    ("VectorStoreError", 503, "SERVICE_UNAVAILABLE"),
    ("TrustRAGError", 500, "INTERNAL_ERROR"),
]


@pytest.mark.parametrize("exc_name,expected_status,expected_code", _CASES)
def test_handler_returns_nested_envelope_with_expected_status(
    exc_name, expected_status, expected_code
):
    """Every domain error must map to its documented status and stable code, in
    the nested envelope. The frontend branches on `error.code`, so a shape
    change here silently degrades the UI's error UX."""
    from app.core import exceptions as exc_mod

    exc_cls = getattr(exc_mod, exc_name)
    r = _app_with_route(exc_cls("boom message")).get("/boom")

    assert r.status_code == expected_status, f"{exc_name}: {r.status_code} != {expected_status}"
    body = r.json()
    # Nested envelope, not a flat one — the audit found this was once wrong.
    assert "error" in body and isinstance(body["error"], dict), f"{exc_name}: {body}"
    assert body["error"]["code"] == expected_code, f"{exc_name}: {body}"
    assert body["error"]["message"], f"{exc_name}: empty message"


def test_generic_handler_never_leaks_internal_detail():
    """The catch-all must return a generic message. Leaking `str(exc)` here
    would expose connection strings, file paths, and query fragments."""
    secret = "mongodb://admin:hunter2@10.0.0.5:27017/prod"

    class _Explosive(Exception):
        def __str__(self):
            return secret

    r = _app_with_route(_Explosive(secret)).get("/boom")

    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert secret not in r.text, "internal connection string leaked to the client"
    assert "hunter2" not in r.text
    assert "Traceback" not in r.text


def test_validation_error_does_not_echo_the_submitted_payload():
    """A 422 from pydantic can echo the offending input. The handler must
    return our own message rather than the raw validation detail."""
    r = _app_with_route(ValueError("user supplied: /etc/shadow")).get("/boom")
    assert r.status_code in (400, 422, 500)
    if r.status_code == 422:
        assert "/etc/shadow" not in r.text


# ─── Request-ID middleware ───────────────────────────────────────────────────
# NOTE: these use a *domain* exception on purpose. FastAPI registers the
# catch-all `Exception` handler on ServerErrorMiddleware, the OUTERMOST layer,
# so an unhandled 500 never re-enters user middleware — see
# test_unhandled_500_has_no_request_id_header below, which pins that gap.


def _app_that_raises_not_found():
    from app.core.exceptions import NotFoundError

    return _app_with_route(NotFoundError("nope"))


def test_request_id_is_echoed_when_client_supplied_a_valid_one():
    r = _app_that_raises_not_found().get("/boom", headers={"X-Request-ID": "abc-123"})
    assert r.status_code == 404
    assert r.headers["X-Request-ID"] == "abc-123"


@pytest.mark.parametrize(
    "hostile",
    [
        "has space",
        "bad\nnewline",  # log forgery / header injection
        "semi;colon",
        "a" * 200,  # over the 64-char limit
    ],
)
def test_invalid_request_id_is_replaced_with_a_uuid(hostile):
    """A client-supplied X-Request-ID lands in every log line. Accepting
    newlines or oversized values would let a caller forge log entries, so an
    invalid value must be discarded in favour of a server-generated UUID."""
    r = _app_that_raises_not_found().get("/boom", headers={"X-Request-ID": hostile})
    got = r.headers.get("X-Request-ID")
    assert got, "no X-Request-ID assigned"
    assert re.fullmatch(r"[0-9a-f-]{36}", got), f"forged/invalid id accepted: {got!r}"


def test_request_id_is_generated_when_absent():
    r = _app_that_raises_not_found().get("/boom")
    assert re.fullmatch(r"[0-9a-f-]{36}", r.headers["X-Request-ID"])


def test_unhandled_500_echoes_the_request_id():
    """FastAPI wires the catch-all `Exception` handler to ServerErrorMiddleware,
    the OUTERMOST layer, so an unhandled error never re-enters
    request_id_middleware and the response would carry no X-Request-ID — leaving
    a client unable to quote an id when reporting a 500. The id is recoverable
    from structlog contextvars, which request_id_middleware binds before
    dispatch, so the generic handler echoes it."""
    r = _app_with_route(RuntimeError("unhandled")).get("/boom", headers={"X-Request-ID": "abc-123"})
    assert r.status_code == 500
    assert r.headers.get("X-Request-ID") == "abc-123", (
        "unhandled 500s lost the request id; client cannot correlate the failure"
    )


def test_unhandled_500_still_hides_internal_detail():
    """Adding the header must not weaken the no-stack-trace guarantee."""
    r = _app_with_route(RuntimeError("mongodb://admin:hunter2@db:27017")).get("/boom")
    assert r.status_code == 500
    assert "hunter2" not in r.text
    assert "mongodb://" not in r.text
