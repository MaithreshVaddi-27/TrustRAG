# TRUSTRAG — Project Roadmap & Remaining Steps

> Last updated: 2026-08-29  
> Current status: All 12 core phases complete + post-launch audit cycle complete (v3). Active work below.

---

## ✅ Completed Phases (1–12 + Post-Launch)

| Phase | Description | Verification |
|-------|-------------|--------------|
| 0 | Architecture, ADRs, threat model | `docs/architecture/` |
| 1 | Monorepo, centralized config, Docker, CI/CD | `.github/workflows/` |
| 2 | React frontend — workbench design system, all 11 pages | `apps/web/src/` |
| 3 | FastAPI CRUD routes, MongoDB Atlas, analysis lifecycle | `apps/api/app/api/` |
| 4 | JWT auth, bcrypt, IDOR prevention, rate limiting | `apps/api/app/core/security.py` |
| 5 | Document ingestion (PDF/TXT/MD), hybrid Qdrant indexing | `apps/api/app/ingestion/` |
| 6 | LangChain + Gemini + hybrid dense/sparse retrieval + RRF | `apps/api/app/retrieval/` |
| 7 | Claim decomposition + NLI verification | `apps/api/app/verification/` |
| 8 | SHA-256 evidence integrity + temporal validity | `apps/api/app/integrity/` |
| 9 | LangGraph agentic adaptive recovery | `apps/api/app/agent/graph.py` |
| 10 | SSE live execution trace streams | `apps/api/app/services/analysis_service.py` |
| 11 | Experiment configs, custom metrics, ablations | `apps/api/app/evaluation/` |
| 12 | Production hardening, cost controls | `docs/audits/audit-v3.md` |
| **P-L** | **Audit v1 → v3 cycle**: 5 bugs found & fixed — 3 CRITICAL import crashes (`/evidence`, `/claims`, `/conflicts`), 2 HIGH data-integrity issues (null `document_id` serialization, truncation marker bug) | `docs/audits/audit-v3.md` |
| **P-L** | **Global aggregate API routes** wired: `GET /api/v1/evidence`, `GET /api/v1/claims`, `GET /api/v1/conflicts` | `apps/api/app/api/v1/` |
| **P-L** | **Evidence, Claims, Conflicts** frontend pages built and connected to live data | `apps/web/src/pages/` |
| **P-L** | **LLM switched** to `gemini-3.5-flash-lite` for both generation and verification | `apps/api/config/models.yaml` |
| **P-L** | **`.gitignore`** expanded with env variants, AI tool dirs, bun lockfile, runtime files | `.gitignore` |
| **P-L** | **`.env.example`** rewritten with full per-variable documentation | `.env.example` |

---

## 🔴 IMMEDIATE (Must Do Before Sharing / Demo)

- [ ] **Set real values in `.env`** — copy `.env.example` → `.env` and fill in:
  - `JWT_SECRET` → `python -c "import secrets; print(secrets.token_hex(64))"`
  - `GEMINI_API_KEY` → https://aistudio.google.com/app/apikey
  - `MONGODB_URI` → your MongoDB Atlas connection string
- [ ] **Rotate MongoDB Atlas credentials** if the original `.env` credentials were ever committed or shared — Database Access → Edit User → Reset Password

---

## 🟠 HIGH PRIORITY (Next Sprint)

### Deployment

- [ ] **Backend** — Deploy to a free host:
  - [Render.com](https://render.com) (spins down after 15min idle on free tier)
  - [Railway.app](https://railway.app) — $5/month free credit
  - [Fly.io](https://fly.io) — `flyctl deploy`
  - Self-hosted via [Coolify](https://coolify.io)
- [ ] **Frontend** — Deploy to [Vercel](https://vercel.com) or [Netlify](https://netlify.com) (both free), set `VITE_API_URL` env var
- [ ] **Set `APP_ENV=production`** — disables `/docs`, enforces `QDRANT_API_KEY`
- [ ] **Qdrant Cloud** — provision free 1 GB cluster at https://cloud.qdrant.io; set `QDRANT_URL` + `QDRANT_API_KEY`

### Testing

- [ ] **Integration tests** for `/evidence`, `/claims`, `/conflicts` routes — currently no coverage for the new aggregate endpoints (see audit-v3 recommendation)
- [ ] **Integration tests** against real MongoDB + Qdrant (all current tests use mocks)
- [ ] **E2E tests** — Playwright or Cypress covering the Playground, Evidence, Claims, and Conflicts flows
- [ ] **Rate limit test** — verify `@limiter.limit()` on `/analyses` and `/auth` blocks at threshold
- [ ] **Sanitization test** — verify `_sanitize_label()` strips control characters from filenames

### Data Layer (from audit-v3 recommendations)

- [ ] **Pagination** on `/evidence`, `/claims`, `/conflicts` — currently hard-capped at 200 records; add `limit`/`offset` or cursor pagination
- [ ] **Compound index** on `evidence` and `claims` collections for the `(user_id → analysis_id → created_at)` query path used by global aggregate endpoints
- [ ] **Make `document_id` nullable** (`str | None`) in `EvidenceResponse` schema instead of returning empty string for orphaned evidence chunks

### Frontend Polish

- [ ] **Loading skeletons** for analysis list, KB document list, Evidence, Claims pages
- [ ] **SSE reconnect button** — show when `connection closed` instead of blank trace
- [ ] **Document ingestion status polling** — `processing` → `completed` without page refresh
- [ ] **File drag-and-drop** on upload area
- [ ] **Analysis comparison view** — side-by-side reliability scores across experiments

---

## 🟡 MEDIUM PRIORITY

### Architecture

- [ ] **Named Qdrant vectors** — migrate from implicit unnamed dense vector to `NamedVectorParams`
- [ ] **Background task queue** — replace `BackgroundTasks` with Celery + Redis for production (survives restarts, monitorable)
- [ ] **Token counting** before Gemini calls — enforce `max_input_tokens` from `models.yaml`
- [ ] **Streaming generation** — pipe Gemini streaming through SSE for faster response perception
- [ ] **SSE auth upgrade** — short-lived SSE ticket token instead of JWT in URL query param

### Observability

- [ ] **Log aggregation** — ship structlog JSON to Datadog, Loki, or Papertrail
- [ ] **Sentry** — error tracking and performance monitoring
- [ ] **Prometheus `/metrics`** — request counts, latency histograms, pipeline stage durations
- [ ] **Cost tracking** — log Gemini token usage per analysis; surface in experiment results

### Security

- [ ] **Refresh tokens** — short-lived access (15 min) + long-lived refresh (7 days)
- [ ] **Account lockout** — N failed logins → temporary lockout (e.g. 5 attempts → 15 min)
- [ ] **Audit log collection** — log all resource creates, deletes, access to `audit_log` collection
- [ ] **Security headers** — CSP, X-Frame-Options, HSTS on all FastAPI responses
- [ ] **PDF virus scanning** — ClamAV or similar before parsing uploaded files

---

## 🟢 LOW PRIORITY (Future)

### RAG Quality

- [ ] **Upgrade embedding model** — evaluate `all-mpnet-base-v2` (768-dim) or `bge-small-en-v1.5`
- [ ] **Reranker model tuning** — evaluate alternative CrossEncoder models
- [ ] **Query expansion** — HyDE or multi-query before retrieval
- [ ] **Per-KB chunk settings** — expose `chunk_size`/`chunk_overlap` per knowledge base
- [ ] **Multi-language support** — language detection + multilingual embedding model

### Product Features

- [ ] **KB sharing** — share knowledge bases between users (requires org/team model)
- [ ] **Scheduled re-verification** — periodic analysis runs as KB documents change
- [ ] **Webhook notifications** — alert external systems on analysis completion or reliability drop
- [ ] **PDF annotation export** — export annotated PDF with evidence highlights
- [ ] **LangSmith tracing** — detailed LangGraph node execution traces

### Developer Experience

- [ ] **Ruff migration** — move `[tool.ruff]` `ignore`/`select` to `[tool.ruff.lint]` (deprecation warning)
- [ ] **Pre-commit hooks** — `.pre-commit-config.yaml` with ruff + mypy + pytest --co
- [ ] **motor type stubs** — add `motor-stubs` for better async type coverage
- [ ] **Makefile** — `make dev`, `make test`, `make lint`, `make build` shortcuts

---

## Deployment Checklist

```
☐ .env filled in (JWT_SECRET, GEMINI_API_KEY, MONGODB_URI)
☐ APP_ENV=production
☐ QDRANT_URL → Qdrant Cloud endpoint
☐ QDRANT_API_KEY set
☐ CORS_ORIGINS → actual frontend domain(s)
☐ MongoDB Atlas credentials rotated
☐ Backend /api/v1/health returns {"status":"ok"}
☐ Frontend built (npm run build) and deployed
☐ Frontend VITE_API_URL → backend URL
☐ CI/CD workflows passing on main branch
```

---

## Audit History

| Version | Date | Findings | Status |
|---------|------|----------|--------|
| `audit-v3.md` | 2026-08-29 | 3 CRITICAL (import crashes), 2 HIGH (data integrity) | ✅ All fixed |

> `audit.md` and `audit-v2.md` have been consolidated into `audit-v3.md` and removed.

---

## CI/CD Status

| Workflow | Jobs | Status |
|----------|------|--------|
| CI | Backend Config Validation | ✅ |
| CI | Frontend Lint | ✅ |
| CI | Frontend Build | ✅ |
| Security | Python SAST (Bandit) | ✅ |
| Security | Python Dependency Audit (pip-audit) | ✅ |
| Security | Frontend NPM Audit | ✅ |
| Security | Secret Scanning | ✅ |
