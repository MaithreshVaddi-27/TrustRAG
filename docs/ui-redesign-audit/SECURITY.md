# Security Audit — TrustRAG ui-redesign

**Scope reviewed:** auth core (`security.py`, `deps.py`), `config.py` (secrets, validators), app factory (`main.py` middleware/CORS/headers), auth routes + `auth_service.py`, rate limiter, models endpoints, filesystem/git secrets sweep (tracked files, `.env` hygiene, scripts).

**Coverage gaps (honest disclosure):** NOT audited — `documents.py` upload validation, `kb_service.py` IDOR on document/KB ownership, frontend token storage (`authStore.js`), Dockerfile/compose/CI secrets, `verifier.py`/MCP-server attack surface. Scores and severity below apply only to the reviewed surface.

---

## Critical

**None found in the reviewed surface.** No hardcoded secrets, no JWT secret fallback (the app refuses to boot without `jwt_secret`), no auth bypass. The auth core is built correctly.

## High

**[High] SSE access token in query string** (Likely — cross-confirmed by BACKEND.md and ARCHITECTURE.md)
- Location: `app/api/v1/analyses.py:118-135`
- Evidence: EventSource cannot set headers, so the endpoint takes the full 60-minute bearer JWT as `token: str | None = Query(...)`. Full-lifetime tokens land in access logs, proxy logs, and browser history.
- Impact: Credential leakage for the token's entire 60-minute validity, replayable against every other endpoint.
- Recommendation: Short-lived (30-60s TTL), single-use, single-analysis stream tickets — minted at POST /analyses, exchanged once for the SSE connection; scrub token query params from access logs as defense-in-depth.

## Medium

**[Medium] ~~All /models endpoints unauthenticated — includes a memory-GC trigger and host info~~** ✅ Partially Fixed
- Location: `models.py:18-19` (GET /providers), `:190-197` (GET /hardware), `:200-215` (POST /memory/trim)
- Fix: Added `Depends(get_current_user)` to GET /hardware and POST /memory/trim endpoints. GET /providers left unauthenticated (serves login page). `@limiter.limit` and base URL stripping remain TODO.

**[Medium] No token revocation, refresh, logout, or password reset — 60-minute bearer-only JWT** (Confirmed)
- Location: `auth.py:21-45` (only /register, /login, /me); `config.py:69` (`jwt_expiry_minutes=60`); `security.py:40-55` (payload has `exp`/`sub`/`iat`, no `jti`)
- Evidence: The `is_active` check in `deps.py:48-49` re-reads the user per request — a partial mitigation (disabling a user stops future requests) — but a leaked token is valid for its full lifetime, "logout" only deletes it client-side, and analyses + SSE streams can outlive a 60-minute token mid-session.
- Impact: No way to invalidate a compromised credential before expiry; UX breaks on long sessions.
- Recommendation: 10-15-minute access tokens + refresh tokens, `jti` + a small Mongo denylist checked in `get_current_user`, logout endpoint writing to the denylist. (Cross-ref ARCHITECTURE.md M8.)

**[Medium] Rate limiting covers only login/register/analyses** (Confirmed)
- Location: `config.py:138-139` (only two limit knobs); `auth.py:27,34`; no limiter import in `models.py` (or most other routers)
- Impact: Upload endpoints (CPU parse+chunk), search (web APIs), models, evidence/claims listing are all unthrottled — any single user can saturate the single-process server and the in-process model server.
- Recommendation: Default per-IP limit on all routers; stricter limits on LLM/embedding/upload paths.

**[Medium] ~~Rate-limit key is the raw client IP — broken behind a reverse proxy~~** ✅ Fixed
- Location: `rate_limiter.py:15`
- Fix: Replaced `get_remote_address` with custom `_get_client_ip` function that reads `X-Forwarded-For` (first untrusted hop) and `X-Real-IP` headers, falling back to `request.client.host`. Rate limiting now works correctly behind reverse proxies.

## Low

**[Low] Credentialed CORS wildcard for pages.dev/vercel.app/netlify.app tenants** (Confirmed) — `main.py:284-288`: origin regex `^https:\/\/([a-zA-Z0-9_\-]+\.)*(pages\.dev|vercel\.app|netlify\.app)$` + `allow_credentials=True` + wildcard methods/headers/expose. Any tenant of those hosts is an accepted origin. Low today (auth is Bearer, not cookies — a cross-origin page can't attach what it never receives), but becomes High the day cookie auth is added. Fix: explicit origin allowlist, drop `allow_credentials`.
**[Low] User enumeration via registration conflict message** (Confirmed) — `auth_service.py:52-55` returns "An account with this email already exists." Login does NOT leak (dummy bcrypt timing-equalized, :73) — well done there. Fix: generic "Invalid credentials or account exists" phrasing for register, or accept-and-noop registration of existing emails.
**[Low] No CSP header** (Confirmed) — `main.py:296-304` sets XCTO, X-Frame-Options DENY, Referrer-Policy, Permissions-Policy, HSTS-in-prod — a good set, but no Content-Security-Policy. Fix: start with `default-src 'self'` (+ `connect-src` for the API origin) and tighten.
**[Low] `.env` discovery walks up the tree** (Potential) — `config.py:54-55`: `env_file=(".env", "../.env", "../../.env")` — running the app from a nested directory can pick up an unexpected parent `.env`. Low practical risk in this layout; worth noting for deployment images.

## Verified positive (the security backbone — keep)

- HS256 pinned explicitly (`security.py:21,65`) — no alg-confusion surface.
- `jwt_secret` has NO default and a ≥32-character minimum enforced at startup (`config.py:68,171-179`).
- `QDRANT_API_KEY` required when `app_env=production` (`config.py:198-202`).
- `.env` hygiene: git tracks only `.env.example` files; the only secrets-bearing script tracked is `clear_qdrant.py` (no secrets); no secrets found in the filesystem/git sweep.
- bcrypt cost 12, constant-time, fail-safe verify (`security.py:27,32-37`).
- docs/OpenAPI disabled in production (`main.py:270-272`).
- The catch-all exception handler never leaks stack traces or internals (`main.py:220-236`).
- Per-request authz reload (`deps.py:44-49`) — deactivated users are cut off on their next request.

---

## Security Score: 6 / 10

**Justification:** The authentication core is genuinely well-built — no bypass, no secret fallback, pinned algorithm, strong-secret enforcement, constant-time failure path, per-request authz reload. The backend's never-leak exception discipline (BACKEND.md) reinforces it. What holds the score at 6: every credential is a non-revocable 60-minute bearer token; one of them rides in SSE query strings; the operational router (including a GC trigger) is open to anonymous users; throttling exists on exactly two endpoints; and the limiter's keying breaks the moment a reverse proxy enters the picture. Discounted for the unaudited surfaces listed above — upload validation, IDOR, frontend token storage, and container/CI secrets were not reviewed.

## Top 5 quick wins

1. **~~Auth + rate-limit the /models router~~** ✅ Partial — auth added to /hardware and /memory/trim; rate-limiting and /providers auth TODO.
2. **Replace the SSE query-param token with short-lived stream tickets** (analyses.py:118-135).
3. **Default per-IP limiter on all routers, keyed on the correct forwarded hop** (rate_limiter.py:15 + router registration).
4. **Add `jti` + a small denylist to `get_current_user`** — makes tokens revocable; unlock for real logout.
5. **CORS: explicit origin allowlist, drop `allow_credentials`** (main.py:284-288) — future-proofs against the cookie-auth mistake.
