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


class TokenError(TrustRAGError):
    """Raised for JWT validation failures."""


# ─── Resource ─────────────────────────────────────────────────────────────────


class NotFoundError(TrustRAGError):
    """Raised when a requested resource does not exist."""


class ConflictError(TrustRAGError):
    """Raised on duplicate resource creation (e.g., duplicate username)."""


# ─── Knowledge Base & Documents ───────────────────────────────────────────────


class KnowledgeBaseError(TrustRAGError):
    """Raised for knowledge-base-level operations."""


class DocumentError(TrustRAGError):
    """Raised for document upload/processing failures."""


class IngestionError(TrustRAGError):
    """Raised when document ingestion fails at any pipeline stage."""


class UnsupportedFormatError(IngestionError):
    """Raised when a document format is not in the supported list."""


class FileTooLargeError(IngestionError):
    """Raised when an uploaded file exceeds the configured size limit."""


class MaliciousDocumentError(IngestionError):
    """
    Raised when suspicious/potentially malicious content is detected.
    This is a best-effort defense — do not claim complete protection.
    """


# ─── AI / Retrieval ───────────────────────────────────────────────────────────


class RetrievalError(TrustRAGError):
    """Raised when retrieval from Qdrant fails."""


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


class ContextTooLargeError(GenerationError):
    """Raised when the assembled context exceeds the token limit."""


# ─── Infrastructure ───────────────────────────────────────────────────────────


class DatabaseError(TrustRAGError):
    """Raised for MongoDB operation failures."""


class VectorStoreError(TrustRAGError):
    """Raised for Qdrant operation failures."""


# ─── Analysis ─────────────────────────────────────────────────────────────────


class AnalysisError(TrustRAGError):
    """Raised for analysis-level failures."""


class AnalysisNotFoundError(NotFoundError):
    """Raised when an analysis ID does not exist for this user."""


# ─── Validation ───────────────────────────────────────────────────────────────


class InputValidationError(TrustRAGError):
    """Raised when API input fails domain-level validation beyond Pydantic."""


class RateLimitError(TrustRAGError):
    """Raised when a rate limit is exceeded."""
