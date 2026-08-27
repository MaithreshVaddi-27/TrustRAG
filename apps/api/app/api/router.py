"""
TRUSTRAG API — top-level API router.

All route modules must be registered here.
Routes are versioned under /api/v1/.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health as health_module

api_router = APIRouter(prefix="/api/v1")

# ── Health ─────────────────────────────────────────────────────────────────
api_router.include_router(health_module.router)

# Future phases will register here:
# from app.api.v1 import auth, knowledge_bases, documents, analyses, ...
# api_router.include_router(auth.router, prefix="/auth")
# api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases")
# api_router.include_router(documents.router, prefix="/documents")
# api_router.include_router(analyses.router, prefix="/analyses")
# api_router.include_router(claims.router, prefix="/claims")
# api_router.include_router(evidence.router, prefix="/evidence")
# api_router.include_router(traces.router, prefix="/traces")
# api_router.include_router(conflicts.router, prefix="/conflicts")
# api_router.include_router(experiments.router, prefix="/experiments")
