"""
TRUSTRAG — security and authentication capability package.

Re-exports from the canonical submodules so ``app.security`` behaves as a
single package:

- ``app.security.exceptions`` — TrustRAGError and typed subclasses
- ``app.security.security`` — hash_password, verify_password, create_access_token,
  decode_access_token, create_service_token, decode_service_token, jti_key,
  ALGORITHM, BCRYPT_MAX_PASSWORD_BYTES, SERVICE_TOKEN_TYPE, SERVICE_TOKEN_TTL_HOURS
"""

from __future__ import annotations

from app.security.exceptions import (  # noqa: F401
    AnalysisNotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ConfigurationError,
    DatabaseError,
    FileTooLargeError,
    GenerationError,
    IngestionError,
    InputValidationError,
    LLMUnavailableError,
    NotFoundError,
    RetrievalOutageError,
    TrustRAGError,
    UnsupportedFormatError,
    VectorStoreError,
)
from app.security.security import (  # noqa: F401
    ALGORITHM,
    BCRYPT_MAX_PASSWORD_BYTES,
    SERVICE_TOKEN_TYPE,
    SERVICE_TOKEN_TTL_HOURS,
    create_access_token,
    create_service_token,
    decode_access_token,
    decode_service_token,
    hash_password,
    jti_key,
    verify_password,
)

__all__ = [
    "AnalysisNotFoundError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "ConfigurationError",
    "DatabaseError",
    "FileTooLargeError",
    "GenerationError",
    "IngestionError",
    "InputValidationError",
    "LLMUnavailableError",
    "NotFoundError",
    "RetrievalOutageError",
    "TrustRAGError",
    "UnsupportedFormatError",
    "VectorStoreError",
    "ALGORITHM",
    "BCRYPT_MAX_PASSWORD_BYTES",
    "SERVICE_TOKEN_TYPE",
    "SERVICE_TOKEN_TTL_HOURS",
    "create_access_token",
    "create_service_token",
    "decode_access_token",
    "decode_service_token",
    "hash_password",
    "jti_key",
    "verify_password",
]
