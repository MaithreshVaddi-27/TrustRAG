# TRUSTRAG — Security Controls

**Version:** 1.0 | **Phase:** 0 (Updated incrementally per phase)

---

## Authentication & Authorization

| Control | Implementation | Status |
|---------|---------------|--------|
| Password hashing | `passlib[bcrypt]` — bcrypt with work factor ≥ 12 | Phase 4 |
| JWT authentication | `python-jose[cryptography]` — HS256, configurable expiry | Phase 4 |
| JWT secret strength | Minimum 32-char enforced in Settings validation | Phase 1 ✓ |
| Protected routes | FastAPI dependency injection (JWT required) | Phase 4 |
| IDOR prevention | Every DB query includes `user_id` ownership filter | Phase 4 |
| Cross-user KB isolation | Authorization in knowledge base service | Phase 4 |

## Input & MCP Search Security

| Control | Implementation | Status |
|---------|---------------|--------|
| File size limit | Enforced in upload handler before parsing | Phase 5 ✓ |
| Format allowlist | PDF, TXT, MD, DOCX, CSV, JSON, HTML, XLSX | Phase 5 ✓ |
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
| Rate limiting | SlowAPI per-IP on all endpoints | Phase 1 ✓ |
| Exception sanitization | Domain exceptions → clean HTTP response | Phase 1 ✓ |
| Secret management | `.env` only; never in code or `models.yaml` | Phase 1 ✓ |
| Sensitive log scrubbing | structlog processor removes sensitive keys | Phase 1 ✓ |
| Non-root container | Docker `USER trustrag` (UID 1001) | Phase 1 ✓ |
| Docs disabled in production | `/docs`, `/redoc` disabled when `APP_ENV=production` | Phase 1 ✓ |

## AI Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Prompt injection defense | Evidence labeled as UNTRUSTED DATA in prompt | Phase 6 |
| Bounded recovery | `max_recovery_attempts` from models.yaml | Phase 9 |
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
