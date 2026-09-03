"""
TRUSTRAG API — FastAPI application factory.

Responsibilities:
  - Application lifecycle (startup/shutdown)
  - Middleware registration (CORS, request ID, rate limiting)
  - Exception handler registration (domain errors → HTTP responses)
  - Router mounting

Security notes:
  - CORS is locked to configured origins only
  - Raw exception details are NEVER sent to clients
  - Request IDs are bound to structured log context per request
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    AnalysisNotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    FileTooLargeError,
    IngestionError,
    InputValidationError,
    NotFoundError,
    TrustRAGError,
    UnsupportedFormatError,
    VectorStoreError,
)
from app.core.logging import configure_logging, get_logger
from app.core.model_registry import get_embedding_model
from app.core.rate_limiter import limiter
from app.db.mongodb import connect_db, create_indexes, disconnect_db

logger = get_logger(__name__)


# ─── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application startup and shutdown.

    Startup:
      1. Configure structured logging
      2. Connect to MongoDB Atlas
      3. Create/verify all indexes

    Shutdown:
      1. Close MongoDB connection
    """
    # ── Startup ──────────────────────────────────────────────────────────
    configure_logging()
    settings = get_settings()

    # Enforce strict offline operation for all auxiliary tools & telemetry
    import os

    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    if settings.hf_token:
        os.environ["HF_TOKEN"] = settings.hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token

    logger.info("TRUSTRAG API starting (Local Offline Mode)", env=settings.app_env)

    await connect_db()
    await create_indexes()

    logger.info("TRUSTRAG API ready")

    # Schedule non-blocking model warmup in background task so Uvicorn binds port INSTANTLY
    async def _async_warmup() -> None:
        try:
            embed_model = get_embedding_model()
            await asyncio.to_thread(embed_model.embed_query, "warmup")
            logger.info("Embedding model pre-warmed and resident in memory")
        except Exception as warm_err:
            logger.warning(
                "Embedding model warmup deferred to first query",
                error=str(warm_err),
            )

    warmup_task = asyncio.create_task(_async_warmup())

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    if not warmup_task.done():
        warmup_task.cancel()
    logger.info("TRUSTRAG API shutting down")
    await disconnect_db()


# ─── Rate limiter ─────────────────────────────────────────────────────────────
# Import shared limiter (defined in app.core.rate_limiter to avoid circular imports)


# ─── Exception handlers ───────────────────────────────────────────────────────


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Produce a consistent error response. Never includes internal detail."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return _error_response(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", exc.message)

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        return _error_response(status.HTTP_403_FORBIDDEN, "FORBIDDEN", exc.message)

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", exc.message)

    @app.exception_handler(AnalysisNotFoundError)
    async def analysis_not_found_handler(
        request: Request, exc: AnalysisNotFoundError
    ) -> JSONResponse:
        return _error_response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", exc.message)

    @app.exception_handler(ConflictError)
    async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return _error_response(status.HTTP_409_CONFLICT, "CONFLICT", exc.message)

    @app.exception_handler(UnsupportedFormatError)
    async def unsupported_format_handler(
        request: Request, exc: UnsupportedFormatError
    ) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "UNSUPPORTED_FORMAT", exc.message
        )

    @app.exception_handler(FileTooLargeError)
    async def file_too_large_handler(request: Request, exc: FileTooLargeError) -> JSONResponse:
        return _error_response(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "FILE_TOO_LARGE", exc.message
        )

    @app.exception_handler(IngestionError)
    async def ingestion_error_handler(request: Request, exc: IngestionError) -> JSONResponse:
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "INGESTION_ERROR", exc.message)

    @app.exception_handler(InputValidationError)
    async def input_validation_handler(request: Request, exc: InputValidationError) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", exc.message
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(
        request: Request, exc: ConfigurationError
    ) -> JSONResponse:
        logger.error("Configuration error", error=exc.message)
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "CONFIGURATION_ERROR",
            "Service configuration error. Contact support.",
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
        logger.error("Database error", error=exc.message)
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "SERVICE_UNAVAILABLE",
            "Database unavailable. Please try again.",
        )

    @app.exception_handler(VectorStoreError)
    async def vector_store_error_handler(request: Request, exc: VectorStoreError) -> JSONResponse:
        logger.error("Vector store error", error=exc.message)
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "SERVICE_UNAVAILABLE",
            "Vector store unavailable. Please try again.",
        )

    @app.exception_handler(TrustRAGError)
    async def trustrag_error_handler(request: Request, exc: TrustRAGError) -> JSONResponse:
        logger.error("Unhandled domain error", error=exc.message, exc_info=True)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all: never expose raw stack traces to clients.
        Log the full error server-side for debugging.
        """
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        )


# ─── Request ID middleware ─────────────────────────────────────────────────────


async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """
    Attach a unique request ID to every request.
    Binds the ID to structlog context so all log lines include it.
    """
    from structlog.contextvars import bind_contextvars, clear_contextvars

    clear_contextvars()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── App factory ──────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TRUSTRAG API",
        description="AI Reliability Workbench — Retrieval, Verification, Diagnosis, Recovery",
        version="0.1.0",
        lifespan=lifespan,
        # Disable automatic /docs in production to reduce attack surface
        docs_url="/docs" if not settings.is_production() else None,
        redoc_url="/redoc" if not settings.is_production() else None,
        openapi_url="/openapi.json" if not settings.is_production() else None,
    )

    # ── Rate limiting ──────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ───────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=r"^https:\/\/([a-zA-Z0-9_\-]+\.)*(pages\.dev|vercel\.app|netlify\.app)$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Content-Type", "Content-Disposition"],
    )

    # ── Request ID ────────────────────────────────────────────────────────
    app.middleware("http")(request_id_middleware)

    # ── Defensive Security Headers ────────────────────────────────────────
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Exception handlers ────────────────────────────────────────────────
    _register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(api_router)

    return app


# ─── Entry point ──────────────────────────────────────────────────────────────

app = create_app()
