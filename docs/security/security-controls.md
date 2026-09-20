# TRUSTRAG — Security Controls

**Version:** 1.2 | **Phase:** RAG quality 0–11 + recovery/security/observability (Updated incrementally per phase)

---

## Authentication & Authorization

| Control | Implementation | Status |
|---------|---------------|--------|
| Password hashing | `passlib[bcrypt]` — bcrypt with work factor ≥ 12 | Phase 4 |
| JWT authentication | `python-jose[cryptography]` — HS256, configurable expiry, `iss`/`aud` issued + verified on both user and service tokens | RAG Phase 9 ✓ |
| Token revocation | JTI blocklist in `revoked_tokens` (recorded on logout until `exp`, checked per request) | RAG Phase 9 ✓ |
| JWT secret strength | Minimum 32-char enforced in Settings validation | Phase 1 ✓ |
| Protected routes | FastAPI dependency injection (JWT required) | Phase 4 |
| IDOR prevention | Every DB query includes `user_id` ownership filter | Phase 4 |
| Cross-user KB isolation | Authorization in knowledge base service | Phase 4 |
| Service-token tenant binding | Optional `bound_kb_id`/`bound_user_id` claims enforced (403) on internal ingest (M-2) | RAG Phase 9 ✓ |
| Login lockout | In-memory per-email window: 5 attempts / 900s, cleared on success | RAG Phase 9 ✓ |

## Input & MCP Search Security

| Control | Implementation | Status |
|---------|---------------|--------|
| File size limit | Enforced in upload handler before parsing | Phase 5 ✓ |
| Format allowlist | PDF, TXT, MD, DOCX, CSV, JSON, HTML, HTM (8 formats) | Phase 5 ✓ |
| Magic-bytes + zip-bomb guards | Format signature validation + per-format decompression ratios | Phase 15 ✓ |
| Upload AV hook | EICAR-signature block + best-effort `pyclamd` scan (fail-open, no new dep), runs before magic-byte validation | RAG Phase 9 ✓ |
| OCR density-gate fail-open | Scanned pages OCR'd; engine failure keeps native text, never kills ingest | RAG OCR ✓ |
| Query length boundary | Hard cap at 500 chars (`MAX_QUERY_LENGTH`) in search service | Phase 14 ✓ |
| SSRF URL sanitization | `sanitize_url` restricts to HTTP/HTTPS, blocks private IP ranges | Phase 14 ✓ |
| MCP tool validation | Schema validation + tool name allowlist before execution | Phase 14 ✓ |
| Prompt architecture | SYSTEM / QUERY / UNTRUSTED_EVIDENCE separation | Phase 6 ✓ |
| Max input tokens | Hard limit before LLM invocation | Phase 6 ✓ |
| Suspicious content detection | Evidence integrity analysis & temporal verification | Phase 8 ✓ |

## Infrastructure Security

| Control | Implementation | Status |
|---------|---------------|--------|
| CORS restriction | Locked to configured origins only | Phase 1 ✓ |
| Rate limiting | SlowAPI per-client ceilings (analyses/auth/upload/url-ingest) | Phase 1 ✓ |
| Exception sanitization | Domain exceptions → clean HTTP response | Phase 1 ✓ |
| Secret management | `.env` only; never in code or `models.yaml` | Phase 1 ✓ |
| Sensitive log scrubbing | structlog processor removes sensitive keys | Phase 1 ✓ |
| Non-root container | Docker `USER trustrag` (UID 1001) | Phase 1 ✓ |
| Docs disabled in production | `/docs`, `/redoc` disabled when `APP_ENV=production` | Phase 1 ✓ |

## AI Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Prompt injection defense | Evidence labeled as UNTRUSTED DATA in prompt | Phase 6 |
| Citation provenance check | Unserved `[Segment N]` refs stripped post-generation | RAG Phase 4 ✓ |
| Claim-retrieval budget | NEUTRAL-only re-retrieval, `max_claim_retrievals: 3` | RAG Phase 5 ✓ |
| Router fan-out ceiling | `max_sub_queries: 3`, partial-outage degrade | RAG Phase 6 ✓ |
| Snapshot/rollback ownership | `user_id` checks on snapshot, rollback, and restore; 409 on vector-less snapshots | RAG Phase 8 ✓ |
| Bounded recovery | Diagnose-then-act, ≤2 attempts, token (2000) + latency (180s) budgets, abstain on exhaustion | RAG Phase 8 ✓ |
| Pre-request token budget | Query estimate (`len//4`) vs `max_input_tokens` → 422, kill-switchable | RAG Phase 10 ✓ |
| Red-team suite | 24 tests: injection-as-data, tool-call non-execution, conflict handling, tenant isolation (`tests/test_redteam.py`) | RAG Phase 9 ✓ |
| Metrics exposition | Public `GET /api/v1/metrics` (counters only, no secrets, no new deps) | RAG Phase 10 ✓ |
| Bounded retries | LLM `max_retries` from models.yaml | Phase 1 ✓ |
| No shell/code execution | LLM never drives shell or eval() | All phases |
| Tool call validation | Schema validation + authorization before execution | Phase 9 |

## CI/CD Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Python CVE scanning | `pip-audit` in security.yml | Phase 1 ✓ |
| NPM CVE scanning | `npm audit` in security.yml | Phase 1 ✓ |
| SAST | Bandit static analysis on Python | Phase 1 ✓ |
| Secret scanning | CI checks for committed `.env` and secrets in YAML | Phase 1 ✓ |
| `.env` gitignore | Verified in security workflow | Phase 1 ✓ |
