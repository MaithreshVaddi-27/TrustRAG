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

from typing import TYPE_CHECKING

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.exceptions import DatabaseError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

logger = get_logger(__name__)

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
    """
    global _client, _database
    settings = get_settings()

    logger.info(
        "Connecting to MongoDB Atlas",
        database=settings.mongodb_database,
    )

    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=30000,
            # Recommended for Atlas
            retryWrites=True,
            w="majority",
        )
        _database = _client[settings.mongodb_database]
        # Ping to verify connection before startup completes
        await _database.command("ping")
        logger.info("MongoDB connection established", database=settings.mongodb_database)
    except Exception as exc:
        logger.error("MongoDB connection failed", error=str(exc))
        raise DatabaseError("Failed to connect to MongoDB Atlas", detail=str(exc)) from exc


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
    await db[Collections.DOCUMENTS].create_index(
        [("ingestion_status", pymongo.ASCENDING)], name="doc_ingestion_status"
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
    await db[Collections.CLAIMS].create_index([("status", pymongo.ASCENDING)], name="claim_status")

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
