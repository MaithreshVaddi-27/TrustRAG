"""
TRUSTRAG API — top-level API router.

All route modules must be registered here.
Routes are versioned under /api/v1/.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    analyses as analysis_module,
)
from app.api.v1 import (
    auth as auth_module,
)
from app.api.v1 import (
    claims as claim_module,
)
from app.api.v1 import (
    conflicts as conflict_module,
)
from app.api.v1 import (
    documents as doc_module,
)
from app.api.v1 import (
    evidence as evidence_module,
)
from app.api.v1 import (
    experiments as experiment_module,
)
from app.api.v1 import (
    health as health_module,
)
from app.api.v1 import (
    knowledge_bases as kb_module,
)
from app.api.v1 import (
    models as model_module,
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

# ── Models & Providers ────────────────────────────────────────────────────
api_router.include_router(model_module.router)

# ── Evidence ───────────────────────────────────────────────────────────────
api_router.include_router(evidence_module.router)

# ── Claims ─────────────────────────────────────────────────────────────────
api_router.include_router(claim_module.router)

# ── Conflicts ──────────────────────────────────────────────────────────────
api_router.include_router(conflict_module.router)

# ── Experiments ────────────────────────────────────────────────────────────
api_router.include_router(experiment_module.router)
