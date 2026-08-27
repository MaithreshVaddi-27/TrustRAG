"""
TRUSTRAG API — top-level API router.

All route modules must be registered here.
Routes are versioned under /api/v1/.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    health as health_module,
    auth as auth_module,
    knowledge_bases as kb_module,
    documents as doc_module,
    analyses as analysis_module,
    experiments as experiment_module,
)

api_router = APIRouter(prefix="/api/v1")

# ── Health ─────────────────────────────────────────────────────────────────
api_router.include_router(health_module.router)

# ── Auth & Users ───────────────────────────────────────────────────────────
api_router.include_router(auth_module.router)

# ── Knowledge Bases ────────────────────────────────────────────────────────
api_router.include_router(kb_module.router)

# ── Documents ──────────────────────────────────────────────────────────────
api_router.include_router(doc_module.router)

# ── Analyses ───────────────────────────────────────────────────────────────
api_router.include_router(analysis_module.router)

# ── Experiments ────────────────────────────────────────────────────────────
api_router.include_router(experiment_module.router)
