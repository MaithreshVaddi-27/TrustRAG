# TRUSTRAG — Project Roadmap & Remaining Steps

> Last updated: 2026-08-27  
> Current status: All 12 core phases complete. Below are the remaining improvement, deployment, and polish tasks.

---

## ✅ Completed Phases (1–12)

All core phases from the spec are implemented and verified:

| Phase | Description | Verification |
|-------|-------------|--------------|
| 0 | Architecture, ADRs, threat model | docs/architecture/ |
| 1 | Monorepo, centralized config, Docker, CI/CD | .github/workflows/ |
| 2 | React frontend — workbench design system, all 11 pages | apps/web/src/ |
| 3 | FastAPI CRUD routes, MongoDB Atlas, analysis lifecycle | apps/api/app/api/ |
| 4 | JWT auth, bcrypt, IDOR prevention, rate limiting | apps/api/app/core/security.py |
| 5 | Document ingestion (PDF/TXT/MD), hybrid Qdrant indexing | apps/api/app/ingestion/ |
| 6 | LangChain + Gemini + hybrid dense/sparse retrieval + RRF | apps/api/app/retrieval/ |
| 7 | Claim decomposition + NLI verification | apps/api/app/verification/ |
| 8 | SHA-256 evidence integrity + temporal validity | apps/api/app/integrity/ |
| 9 | LangGraph agentic adaptive recovery | apps/api/app/agent/graph.py |
| 10 | SSE live execution trace streams | apps/api/app/services/analysis_service.py |
| 11 | Experiment configs, custom metrics, ablations | apps/api/app/evaluation/ |
| 12 | Production hardening, cost controls, security audit | docs/audits/audit-v2.md |

---

## 🔴 IMMEDIATE (Blocking)

These must be done before the system can run end-to-end:

- [ ] **Rotate MongoDB Atlas credentials** — Real credentials were found in `.env` and have been scrubbed. Go to MongoDB Atlas → Database Access → Edit User → reset password. Update your local `.env` with the new password.
- [ ] **Set real values in `.env`** — The current `.env` contains placeholder values:
  - `JWT_SECRET` → generate with `python -c "import secrets; print(secrets.token_hex(64))"`
  - `GEMINI_API_KEY` → obtain at https://aistudio.google.com/app/apikey
  - `MONGODB_URI` → paste your rotated Atlas connection string

---

## 🟠 HIGH PRIORITY (Next Sprint)

### Deployment

- [ ] **Deploy backend to a free host** — Options verified for free tier:
  - [Render.com](https://render.com) — free web service tier (spins down after 15min idle)
  - [Railway.app](https://railway.app) — $5 free credit/month
  - [Fly.io](https://fly.io) — free tier with `flyctl deploy`
  - Self-hosted with [Coolify](https://coolify.io)
- [ ] **Deploy frontend to Vercel or Netlify** — both are free, just `npm run build` and push
- [ ] **Set `APP_ENV=production` in deployment environment** — enables QDRANT_API_KEY enforcement, disables `/docs`
- [ ] **Provision Qdrant Cloud** — free 1GB cluster at https://cloud.qdrant.io — set `QDRANT_URL` and `QDRANT_API_KEY` in prod env

### Testing

- [ ] **Add integration tests** — tests that actually hit MongoDB + Qdrant (currently all mocked)
- [ ] **Add end-to-end tests** — Playwright or Cypress for the React frontend flows
- [ ] **Add test for rate limiting** — verify `@limiter.limit()` decorators actually block at threshold
- [ ] **Add test for `_sanitize_label()`** — verify filename injection is blocked
- [ ] **Add test for max_length=2000 query constraint** — verify 422 returned on overlong input

### Frontend Polish

- [ ] **Add loading skeletons** for analysis list and KB document list pages
- [ ] **Handle SSE `connection closed` gracefully** — show a reconnect button instead of blank trace
- [ ] **Add document ingestion status polling** — show `processing` → `completed` transition without page refresh
- [ ] **Add file drag-and-drop** to the document upload area
- [ ] **Add analysis comparison view** — side-by-side reliability scores across experiments

---

## 🟡 MEDIUM PRIORITY (Upcoming)

### Architecture Improvements

- [ ] **Named Qdrant vectors** — migrate from implicit unnamed dense vector to explicit `NamedVectorParams`. Needed when adding multi-vector configurations (e.g., different embedding models per KB).
- [ ] **Pagination** for analyses list, documents list, claims list — add `limit`/`offset` query params
- [ ] **Background task queue** — replace FastAPI `BackgroundTasks` with Celery + Redis for production reliability (tasks survive restarts, can be monitored)
- [ ] **Token counting before Gemini calls** — estimate input tokens and enforce `max_input_tokens` from `models.yaml` before calling the API
- [ ] **Streaming generation** — pipe Gemini streaming output through SSE for faster perceived response
- [ ] **SSE authentication upgrade** — consider a short-lived SSE ticket token (exchanged via authenticated REST call) to avoid passing the JWT in the URL query string

### Observability

- [ ] **Structured log aggregation** — ship structlog JSON output to Datadog, Loki, or Papertrail
- [ ] **Sentry integration** — add Sentry SDK for error tracking and performance monitoring
- [ ] **Prometheus metrics** — expose `/metrics` endpoint with request counts, latency histograms, and analysis pipeline stage durations
- [ ] **Cost tracking** — log Gemini API token usage per analysis run; expose aggregated cost in experiment results

### Security

- [ ] **Refresh tokens** — implement short-lived access tokens (15min) + long-lived refresh tokens (7 days) for better session security
- [ ] **Account lockout** — lock account after N failed login attempts (e.g., 5 attempts → 15min lockout)
- [ ] **Audit logging** — log all resource creation, deletion, and access events to a separate `audit_log` collection
- [ ] **Content-Security-Policy headers** — add CSP, X-Frame-Options, and HSTS headers to the FastAPI responses
- [ ] **File upload virus scanning** — integrate ClamAV or similar for uploaded PDFs before parsing

---

## 🟢 LOW PRIORITY (Future Enhancements)

### RAG Quality

- [ ] **Upgrade embedding model** — evaluate `all-mpnet-base-v2` (768-dim) or `bge-small-en-v1.5` for better retrieval quality at comparable cost
- [ ] **Cross-encoder reranker tuning** — evaluate different CrossEncoder models for the reranker step
- [ ] **Query expansion pre-processing** — HyDE (Hypothetical Document Embeddings) or multi-query expansion before retrieval
- [ ] **Chunk overlap tuning** — expose chunk_size and chunk_overlap as per-KB settings (currently global)
- [ ] **Multi-language support** — add language detection to parser and use multilingual embedding model

### Product Features

- [ ] **Knowledge Base sharing** — allow KBs to be shared between users (requires team/org model)
- [ ] **Scheduled analysis runs** — periodic re-verification of documents as knowledge base changes
- [ ] **Webhook notifications** — notify external systems when analysis completes or reliability drops below threshold
- [ ] **PDF annotation export** — export analysis results as annotated PDF with claim evidence highlighted
- [ ] **LangSmith tracing** — integrate LangSmith for detailed LangGraph node execution tracing

### Developer Experience

- [ ] **Fix pyproject.toml Ruff deprecation warnings** — migrate `[tool.ruff]` `ignore`/`select`/`per-file-ignores` to `[tool.ruff.lint]` section
- [ ] **Pre-commit hooks** — add `.pre-commit-config.yaml` running ruff + mypy + pytest --co
- [ ] **Type stubs for motor** — add `motor-stubs` to improve type checking coverage
- [ ] **Makefile** — add `make dev`, `make test`, `make lint`, `make build` shortcuts

---

## Deployment Checklist

Use this when deploying to production:

```
☐ .env values set (JWT_SECRET, GEMINI_API_KEY, MONGODB_URI)
☐ APP_ENV=production
☐ QDRANT_URL pointing to Qdrant Cloud
☐ QDRANT_API_KEY set
☐ CORS_ORIGINS set to actual frontend domain
☐ MongoDB Atlas credentials rotated
☐ Backend deployed and /api/v1/health returns 200
☐ Frontend built (npm run build) and deployed
☐ Frontend VITE_API_URL set to backend URL
☐ CI/CD workflows passing on main branch
```

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
