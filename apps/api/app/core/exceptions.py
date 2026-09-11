"""
TRUSTRAG — domain exceptions.

All application-level errors should raise one of these typed exceptions.
FastAPI exception handlers in main.py translate these to HTTP responses.
Raw stack traces must NEVER reach the client.
"""

from __future__ import annotations


class TrustRAGError(Exception):
    """Base exception for all TRUSTRAG domain errors."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail  # Internal detail — NOT sent to client


# ─── Configuration ────────────────────────────────────────────────────────────


class ConfigurationError(TrustRAGError):
    """Raised when models.yaml or settings are invalid or inconsistent."""


# ─── Authentication & Authorization ───────────────────────────────────────────


class AuthenticationError(TrustRAGError):
    """Raised when credentials are invalid or missing."""


class AuthorizationError(TrustRAGError):
    """Raised when the authenticated user lacks permission for a resource."""


# ─── Resource ─────────────────────────────────────────────────────────────────


class NotFoundError(TrustRAGError):
    """Raised when a requested resource does not exist."""


class ConflictError(TrustRAGError):
    """Raised on duplicate resource creation (e.g., duplicate username)."""


# ─── Knowledge Base & Documents ───────────────────────────────────────────────


class IngestionError(TrustRAGError):
    """Raised when document ingestion fails at any pipeline stage."""


class UnsupportedFormatError(IngestionError):
    """Raised when a document format is not in the supported list."""


class FileTooLargeError(IngestionError):
    """Raised when an uploaded file exceeds the configured size limit."""


# ─── AI / Retrieval ───────────────────────────────────────────────────────────


class RetrievalError(TrustRAGError):
    """Raised when retrieval from Qdrant fails."""


class RetrievalOutageError(TrustRAGError):
    """
    Raised when the retrieval infrastructure itself is unavailable.

    Distinct from a normal empty result: an empty candidate list means the
    knowledge base genuinely contains no matching evidence, while this error
    means Qdrant / the embedding service could not be reached at all (a
    transient infrastructure outage). Callers MUST NOT conflate the two.
    """


class EmbeddingError(TrustRAGError):
    """Raised when embedding generation fails."""


class GenerationError(TrustRAGError):
    """Raised when LLM generation fails."""


class VerificationError(TrustRAGError):
    """Raised when claim verification encounters an error."""


class RecoveryError(TrustRAGError):
    """Raised when the recovery workflow encounters an unrecoverable error."""


class LLMUnavailableError(GenerationError):
    """Raised when the Gemini API is unavailable or rate-limited."""


# ─── Infrastructure ───────────────────────────────────────────────────────────


class DatabaseError(TrustRAGError):
    """Raised for MongoDB operation failures."""


class VectorStoreError(TrustRAGError):
    """Raised for Qdrant operation failures."""


# ─── Analysis ─────────────────────────────────────────────────────────────────


class AnalysisNotFoundError(NotFoundError):
    """Raised when an analysis ID does not exist for this user."""


# ─── Validation ───────────────────────────────────────────────────────────────


class InputValidationError(TrustRAGError):
    """Raised when API input fails domain-level validation beyond Pydantic."""
