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
import re
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_model_config, get_settings
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
    LLMUnavailableError,
    NotFoundError,
    TrustRAGError,
    UnsupportedFormatError,
    VectorStoreError,
)
from app.core.hardware import get_cached_hardware_profile
from app.core.logging import configure_logging, get_logger
from app.core.model_registry import get_embedding_model
from app.core.rate_limiter import limiter
from app.core.tracing import init_tracing, tracing_middleware
from app.db.mongodb import connect_db, create_indexes, disconnect_db

logger = get_logger(__name__)


# ─── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application startup and shutdown.

    Startup:
      1. Configure structured logging
      2. Connect to MongoDB
      3. Create/verify all indexes
      4. Start non-blocking model and hardware warmup

    Shutdown:
      1. Close local-LLM HTTP connection pools
      2. Close MongoDB connection
    """
    # ── Startup ──────────────────────────────────────────────────────────
    configure_logging()
    settings = get_settings()

    # Enforce strict offline operation for all auxiliary tools & telemetry.
    # Offline model loading is only forced when the embedding weights are
    # already cached — a fresh machine must be allowed to download them once.
    import os

    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    _model_cached = False
    try:
        cfg_probe = get_model_config()
        if cfg_probe.embedding_provider in ("huggingface", "local", "splade"):
            from pathlib import Path as _Path

            hub_snapshot = (
                _Path.home()
                / ".cache"
                / "huggingface"
                / "hub"
                / ("models--" + cfg_probe.embedding_model.replace("/", "--"))
            )
            cache_dir = _Path(cfg_probe.embedding_cache_dir)
            # Real weight files only — a stray config.json must not count as cached.
            has_weights = hub_snapshot.exists() or (
                cache_dir.exists()
                and any(cache_dir.rglob(p) for p in ("*.safetensors", "*.bin", "*.pt"))
            )
            if has_weights:
                _model_cached = True
        else:
            _model_cached = True  # cloud embeddings need no local weights
    except Exception:
        _model_cached = False
    if _model_cached:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    else:
        logger.info("Embedding weights not cached — allowing one-time model download")

    if settings.hf_token:
        os.environ["HF_TOKEN"] = settings.hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token

    logger.info("TRUSTRAG API starting (Local Offline Mode)", env=settings.app_env)

    # BE-H3: Log the EFFECTIVE model configuration at startup.
    # Env vars take precedence over models.yaml, so this log line removes any
    # ambiguity about which provider/model is actually running.
    cfg = get_model_config()
    logger.info(
        "Effective model configuration (env overrides models.yaml)",
        llm_provider=cfg.llm_provider,
        llm_model=cfg.llm_model,
        embedding_provider=cfg.embedding_provider,
        embedding_model=cfg.embedding_model,
        verification_provider=cfg.verification_provider,
        verification_model=cfg.verification_model,
    )

    # The model registry owns one cached embedding instance. A separate startup
    # manager used to load a second copy that no serving path consumed.
    await connect_db()
    await create_indexes()

    # Seed the local-model discovery cache from the persisted snapshot so a
    # pre-run `scripts/discover_local_models.py` (or any earlier process) is
    # honored before the server answers its first request.
    from app.core.local_llm import load_discovery_snapshot, seed_local_model_discovery

    load_discovery_snapshot()

    logger.info("TRUSTRAG API ready")

    # Initialize tracing (LangSmith, OpenTelemetry, etc.)
    init_tracing()

    # Schedule non-blocking model warmup in background task so Uvicorn binds port INSTANTLY.
    # Embedding warmup (model load + first encode) and the hardware probe run
    # concurrently — they are independent and the probe shells out to subprocesses.
    async def _warmup_embeddings() -> None:
        try:
            embed_model = get_embedding_model()
            await asyncio.to_thread(embed_model.embed_query, "warmup")
            logger.info("Embedding model pre-warmed and resident in memory")
        except Exception as warm_err:
            logger.warning(
                "Embedding model warmup deferred to first query",
                error=str(warm_err),
            )

    async def _warmup_hardware() -> None:
        # OPT-H9: Run the expensive hardware probe once at startup so the first
        # /models/* request never pays the subprocess cost.
        try:
            await asyncio.to_thread(get_cached_hardware_profile)
        except Exception as hw_err:
            logger.warning("Hardware profile warmup deferred", error=str(hw_err))

    async def _async_warmup() -> None:
        # Live-refresh discovery (fast CLI subprocesses) alongside the heavier
        # embedding warmup and hardware probe; discovery re-persists the snapshot
        # so already-running processes / future restarts stay in sync.
        await asyncio.gather(_warmup_embeddings(), _warmup_hardware(), seed_local_model_discovery())

    warmup_task = asyncio.create_task(_async_warmup())

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    if not warmup_task.done():
        warmup_task.cancel()
    logger.info("TRUSTRAG API shutting down")
    from app.core.local_llm import close_local_llm_clients
    from app.core.model_registry import close_all_llm_instances

    await close_local_llm_clients()
    close_all_llm_instances()
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

    @app.exception_handler(LLMUnavailableError)
    async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError) -> JSONResponse:
        # Actionable by design: the message names only the configured base URL
        # plus the start command (no secrets) so the UI can alert the user to
        # start their local inference server instead of timing out silently.
        logger.warning("Local LLM server unavailable", error=exc.message)
        return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, "LLM_UNAVAILABLE", exc.message)

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
# SEC: validate/truncate client-supplied X-Request-ID to prevent log forgery/trace confusion
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-]{1,64}$")


async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """
    Attach a unique request ID to every request.
    Binds the ID to structlog context so all log lines include it.
    Validates and truncates client-supplied X-Request-ID.
    """
    from structlog.contextvars import bind_contextvars, clear_contextvars

    clear_contextvars()
    client_id = request.headers.get("X-Request-ID")
    if client_id and _REQUEST_ID_PATTERN.fullmatch(client_id):
        request_id = client_id
    else:
        request_id = str(uuid.uuid4())
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
        # NOTE: no custom default_response_class — FastAPI ≥0.115 serializes
        # typed endpoints directly to JSON bytes via Pydantic (faster than a
        # custom ORJSONResponse, which is deprecated and warns per request).
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
    # SEC-H-A: In production, only explicit CORS_ORIGINS allowed.
    # Wildcard platform regex (vercel.app, netlify.app, pages.dev) only for dev/staging.
    cors_kwargs = {
        "allow_origins": settings.cors_origins_list,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Request-ID", "Content-Type", "Content-Disposition"],
    }
    if not settings.is_production():
        cors_kwargs["allow_origin_regex"] = (
            r"^https:\/\/([a-zA-Z0-9_\-]+\.)*(pages\.dev|vercel\.app|netlify\.app)$"
        )
    app.add_middleware(CORSMiddleware, **cors_kwargs)

    # ── GZip compression (threshold 1KB, skips small responses) ──────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Request ID ────────────────────────────────────────────────────────
    app.middleware("http")(request_id_middleware)

    # ── Tracing ────────────────────────────────────────────────────────────
    app.middleware("http")(tracing_middleware)

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
