# TRUSTRAG — Backend Audit v3
**Date:** 2026-08-29  
**Auditor:** Principal Backend Engineer (Automated)  
**Scope:** Full backend + business logic + API layer + frontend service wiring  
**Methodology:** INSPECT → TRACE → IDENTIFY → FIX → TEST → RE-AUDIT  

---

## Executive Summary

5 bugs were identified and fixed across the API layer, service layer, and data-integrity pipeline.  
Three were **CRITICAL** (startup-crashing import errors on newly added routes).  
Two were **HIGH** (silent data corruption in serialization and display).  
Zero MEDIUM/LOW issues required code changes — all were verified-correct by trace analysis.

All services verified healthy post-fix. API startup clean, no errors.

---

## Bug Register

### 🔴 CRITICAL — `evidence.py` · Wrong `get_current_user` import

| Field | Value |
|-------|-------|
| **File** | `apps/api/app/api/v1/evidence.py` |
| **Severity** | CRITICAL |
| **Status** | ✅ FIXED |
| **Type** | ImportError / Startup Crash |

**Root Cause:**  
`get_current_user` was imported from `app.api.v1.auth`, which is the *route module* for auth endpoints — it does **not** export `get_current_user`. The actual dependency lives in `app.api.deps`. This would cause a Python `ImportError` at module load time, crashing the FastAPI route registration for the entire `/evidence` prefix before any request could be served.

**Bad code:**
```python
from app.api.v1.auth import get_current_user  # ← auth.py doesn't export this
```

**Fix applied:**
```python
from app.api.deps import get_current_user
```

---

### 🔴 CRITICAL — `claims.py` · Wrong `get_current_user` import

| Field | Value |
|-------|-------|
| **File** | `apps/api/app/api/v1/claims.py` |
| **Severity** | CRITICAL |
| **Status** | ✅ FIXED |
| **Type** | ImportError / Startup Crash |

**Root Cause:** Same pattern — identical wrong import path. The `/claims` route would fail to register on startup.

**Fix applied:**
```python
from app.api.deps import get_current_user
```

---

### 🔴 CRITICAL — `conflicts.py` · Wrong `get_current_user` import

| Field | Value |
|-------|-------|
| **File** | `apps/api/app/api/v1/conflicts.py` |
| **Severity** | CRITICAL |
| **Status** | ✅ FIXED |
| **Type** | ImportError / Startup Crash |

**Root Cause:** Same pattern — all three newly-wired aggregate routes (`/evidence`, `/claims`, `/conflicts`) shared this bug because they were created in the same session without referencing the correct import path from the existing route modules.

**Fix applied:**
```python
from app.api.deps import get_current_user
```

---

### 🟠 HIGH — `analysis_service.py` · `serialize_evidence()` serializes `None` document_id as string `"None"`

| Field | Value |
|-------|-------|
| **File** | `apps/api/app/services/analysis_service.py` — `serialize_evidence()` |
| **Severity** | HIGH |
| **Status** | ✅ FIXED |
| **Type** | Data Integrity / Silent Corruption |

**Root Cause:**  
When evidence chunks have no traceable source document, `doc["document_id"]` is `None`.  
`str(None)` produces the literal string `"None"` — garbage data returned to clients.

**Bad code:**
```python
document_id=str(doc["document_id"]),
```

**Fix applied:**
```python
document_id=str(doc["document_id"]) if doc.get("document_id") else "",
```

---

### 🟠 HIGH — `analysis_service.py` · `list_all_user_conflicts()` always appends `"..."` truncation marker

| Field | Value |
|-------|-------|
| **File** | `apps/api/app/services/analysis_service.py` — `list_all_user_conflicts()` |
| **Severity** | HIGH |
| **Status** | ✅ FIXED |
| **Type** | Data Integrity / Display Corruption |

**Root Cause:**  
Code always appended `"..."` after truncating to 200 chars, even for short strings under 200 chars.

**Bad code:**
```python
"claim": e["text"][:200] + "...",
```

**Fix applied:**
```python
"claim": (e["text"][:200] + "...") if len(e["text"]) > 200 else e["text"],
```

---

## Systems Verified Correct (No Changes Required)

| System | Verified |
|--------|---------|
| JWT lifecycle (creation, decode, expiry handling) | ✅ |
| bcrypt timing-safe dummy hash for missing users | ✅ |
| Active-user account deactivation check on login | ✅ |
| KB ownership check on all resource paths (IDOR prevention) | ✅ |
| Analysis ownership check | ✅ |
| Chunker infinite-loop guard (chunk_overlap >= chunk_size) | ✅ |
| PDF parser with timezone-aware datetime extraction | ✅ |
| Qdrant client singleton + collection init idempotency | ✅ |
| Hybrid retrieval (dense + sparse + RRF) via asyncio.gather | ✅ |
| Temporal filtering with UTC-aware datetime comparison | ✅ |
| LangGraph agent (retrieval→generation→verification→recovery) | ✅ |
| Claim decomposition structured output + NLI verification | ✅ |
| SHA-256 integrity audit against document_chunks reference hashes | ✅ |
| SSE generator: polling, terminal event detection, timeout | ✅ |
| Rate limiting on /auth (20/min) and /analyses (10/min) | ✅ |
| Exception handlers: all domain exceptions mapped; catch-all guards | ✅ |
| MongoDB indexes: ownership + lookup coverage on all collections | ✅ |
| Ingestion pipeline: status lifecycle with rollback on failure | ✅ |
| CORS locked to configured origin allowlist (not wildcard) | ✅ |
| Raw exception details never sent to clients | ✅ |

---

## Post-Fix Verification

```
API startup:        ✅ No errors. TRUSTRAG API ready.
MongoDB:            ✅ Connected. Indexes verified.
Import smoke test:  ✅ evidence.py, claims.py, conflicts.py — all routes registered.
Health endpoint:    ✅ {"status":"ok","services":{"mongodb":"ok"}}
LLM model active:   gemini-3.5-flash-lite
```

---

## Recommendations (Non-Blocking)

1. **Compound user_id index on evidence + claims** via analysis_id for faster global aggregation.
2. **Pagination** on `list_all_user_evidence` and `list_all_user_claims` (currently hard-capped at 200).
3. **Make `document_id` nullable** (`str | None`) in `EvidenceResponse` schema instead of returning empty string.
4. **Integration tests** for the three new aggregate endpoints to prevent future import regressions.

---

*Previous audits: [`audit.md`](audit.md) · [`audit-v2.md`](audit-v2.md)*
