"""
TRUSTRAG — MongoDB Atlas client and collection registry.

Single source of all database access. No other module should
import pymongo or motor directly — always use this module.

Connection is established once at startup and reused.
All collection names are defined as constants — never scattered strings.

Authorization enforcement is the responsibility of service layers,
not the database layer.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import certifi
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import get_settings
from app.core.exceptions import DatabaseError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

logger = get_logger(__name__)

# Retry policy for the initial connection. Atlas M0 (free tier) clusters
# auto-pause when idle and take 30-90s to resume on the first request —
# while resuming, in-flight TLS handshakes get reset/aborted, which is
# indistinguishable on the wire from a network problem. A single 5s
# attempt (the old behavior) can never survive that; retrying with
# backoff for a couple of minutes does, with no user action needed.
_CONNECT_MAX_ATTEMPTS = 12
_CONNECT_INITIAL_BACKOFF_SECONDS = 3.0
_CONNECT_MAX_BACKOFF_SECONDS = 20.0

# ─── Collection name constants ────────────────────────────────────────────────
# These names must never be scattered as string literals through the codebase.


class Collections:
    USERS = "users"
    KNOWLEDGE_BASES = "knowledge_bases"
    DOCUMENTS = "documents"
    DOCUMENT_CHUNKS = "document_chunks"
    ANALYSES = "analyses"
    CLAIMS = "claims"
    EVIDENCE = "evidence"
    RECOVERY_RUNS = "recovery_runs"
    TRACE_EVENTS = "trace_events"
    EXPERIMENTS = "experiments"
    FEEDBACK = "feedback"


# ─── Client singleton ─────────────────────────────────────────────────────────

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    """
    Establish MongoDB connection.
    Called once during FastAPI lifespan startup.

    Retries with exponential backoff instead of failing on the first
    attempt — Atlas M0 clusters resuming from auto-pause, or a flaky
    first handshake, both look like a hard failure to a single attempt
    but succeed within a few retries.
    """
    global _client, _database
    settings = get_settings()

    logger.info(
        "Connecting to MongoDB",
        database=settings.mongodb_database,
    )

    backoff = _CONNECT_INITIAL_BACKOFF_SECONDS
    last_exc: Exception | None = None

    for attempt in range(1, _CONNECT_MAX_ATTEMPTS + 1):
        try:
            client_kwargs: dict[str, Any] = {
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 10000,
                "socketTimeoutMS": 30000,
                "retryWrites": True,
                "w": "majority",
                "tz_aware": True,
            }
            uri_lower = settings.mongodb_uri.lower()
            if "mongodb+srv" in uri_lower or "tls=true" in uri_lower or "ssl=true" in uri_lower:
                client_kwargs["tlsCAFile"] = certifi.where()

            candidate_client: AsyncIOMotorClient = AsyncIOMotorClient(
                settings.mongodb_uri,
                **client_kwargs,
            )
            candidate_db = candidate_client[settings.mongodb_database]
            # Ping to verify connection before startup completes
            await candidate_db.command("ping")

            _client = candidate_client
            _database = candidate_db
            logger.info(
                "MongoDB connection established",
                database=settings.mongodb_database,
                attempt=attempt,
            )
            return
        except PyMongoError as exc:
            last_exc = exc
            candidate_client.close()
            if attempt == _CONNECT_MAX_ATTEMPTS:
                break
            logger.warning(
                "MongoDB connection attempt failed, retrying",
                attempt=attempt,
                max_attempts=_CONNECT_MAX_ATTEMPTS,
                retry_in_seconds=backoff,
                error=str(exc),
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 1.5, _CONNECT_MAX_BACKOFF_SECONDS)

    logger.error(
        "MongoDB connection failed after all retries",
        attempts=_CONNECT_MAX_ATTEMPTS,
        error=str(last_exc),
    )
    raise DatabaseError(
        "Failed to connect to MongoDB after repeated retries",
        detail=str(last_exc),
    ) from last_exc


async def disconnect_db() -> None:
    """Close MongoDB connection. Called during FastAPI lifespan shutdown."""
    global _client, _database
    if _client is not None:
        logger.info("Closing MongoDB connection")
        _client.close()
        _client = None
        _database = None


def get_database() -> AsyncIOMotorDatabase:
    """Return the active database instance."""
    if _database is None:
        raise DatabaseError(
            "Database not initialized. Did startup fail?",
            detail="Call connect_db() during application lifespan.",
        )
    return _database


def get_collection(name: str) -> AsyncIOMotorCollection:
    """Return a named collection from the active database."""
    return get_database()[name]


# ─── Index creation ───────────────────────────────────────────────────────────


async def create_indexes() -> None:
    """
    Ensure all required indexes exist.

    Idempotent — safe to call on every startup.
    Creates indexes for:
      - Ownership (user_id foreign key on all user-owned collections)
      - Knowledge base membership (knowledge_base_id)
      - Status fields for filtering
      - Time-based queries (created_at descending)
      - Unique constraints
    """
    db = get_database()

    # ── users ──────────────────────────────────────────────────────────────
    await db[Collections.USERS].create_index(
        [("email", pymongo.ASCENDING)], unique=True, name="email_unique"
    )

    # ── knowledge_bases ────────────────────────────────────────────────────
    await db[Collections.KNOWLEDGE_BASES].create_index(
        [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
        name="kb_owner_time",
    )

    # ── documents ──────────────────────────────────────────────────────────
    await db[Collections.DOCUMENTS].create_index(
        [("knowledge_base_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
        name="doc_kb_time",
    )
    await db[Collections.DOCUMENTS].create_index(
        [("content_hash", pymongo.ASCENDING)], name="doc_content_hash"
    )
    await db[Collections.DOCUMENTS].create_index([("user_id", pymongo.ASCENDING)], name="doc_user")
    await db[Collections.DOCUMENTS].create_index(
        [("ingestion_status", pymongo.ASCENDING)], name="doc_ingestion_status"
    )

    # ── document_chunks ────────────────────────────────────────────────────
    await db[Collections.DOCUMENT_CHUNKS].create_index(
        [("document_id", pymongo.ASCENDING), ("chunk_index", pymongo.ASCENDING)],
        name="chunk_doc_index",
    )
    await db[Collections.DOCUMENT_CHUNKS].create_index(
        [("knowledge_base_id", pymongo.ASCENDING)], name="chunk_kb_id"
    )
    await db[Collections.DOCUMENT_CHUNKS].create_index(
        [("user_id", pymongo.ASCENDING)], name="chunk_user"
    )
    await db[Collections.DOCUMENT_CHUNKS].create_index(
        [("text_hash", pymongo.ASCENDING)], name="chunk_text_hash"
    )

    # ── analyses ───────────────────────────────────────────────────────────
    await db[Collections.ANALYSES].create_index(
        [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
        name="analysis_owner_time",
    )
    await db[Collections.ANALYSES].create_index(
        [("knowledge_base_id", pymongo.ASCENDING)], name="analysis_kb"
    )
    await db[Collections.ANALYSES].create_index(
        [("status", pymongo.ASCENDING)], name="analysis_status"
    )

    # ── claims ─────────────────────────────────────────────────────────────
    await db[Collections.CLAIMS].create_index(
        [("analysis_id", pymongo.ASCENDING)], name="claim_analysis"
    )
    # Claim documents store verdict under "state" (SUPPORTED/CONTRADICTED/NEUTRAL),
    # never "status" — index must match the actual field name to be useful.
    await db[Collections.CLAIMS].create_index([("state", pymongo.ASCENDING)], name="claim_state")

    # ── evidence ───────────────────────────────────────────────────────────
    await db[Collections.EVIDENCE].create_index(
        [("analysis_id", pymongo.ASCENDING)], name="evidence_analysis"
    )
    await db[Collections.EVIDENCE].create_index(
        [("document_id", pymongo.ASCENDING)], name="evidence_document"
    )

    # ── recovery_runs ──────────────────────────────────────────────────────
    await db[Collections.RECOVERY_RUNS].create_index(
        [("analysis_id", pymongo.ASCENDING), ("attempt", pymongo.ASCENDING)],
        name="recovery_analysis_attempt",
    )

    # ── trace_events ───────────────────────────────────────────────────────
    await db[Collections.TRACE_EVENTS].create_index(
        [("analysis_id", pymongo.ASCENDING), ("timestamp", pymongo.ASCENDING)],
        name="trace_analysis_time",
    )

    # ── experiments ────────────────────────────────────────────────────────
    await db[Collections.EXPERIMENTS].create_index(
        [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
        name="exp_owner_time",
    )

    logger.info("MongoDB indexes created/verified")


async def health_check() -> bool:
    """
    Ping MongoDB and return True if healthy.
    Used by the /health endpoint.
    """
    try:
        await get_database().command("ping")
        return True
    except Exception:
        return False
