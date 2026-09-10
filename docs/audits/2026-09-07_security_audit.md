# TrustRAG Security Audit

**Date:** 2026-09-07  
**Branch:** `ui-redesign`  
**Audit role:** Senior Security Engineer  
**Scope:** FastAPI backend, authentication, authorization, multi-tenant boundaries, URL ingestion and SSRF defenses, rate limiting, CORS, secrets, uploads, MCP surface, dependencies, Docker/local deployment.

## Executive summary

The repository already contains meaningful controls: bcrypt password hashing, JWT identifiers for revocation, tenant ownership checks, generic API errors, upload size limits, security headers, and some URL validation. The most urgent remaining risks are concentrated in network egress and authenticated-user abuse:

1. URL ingestion can be bypassed through allowlist prefix matching, non-canonical IP literals, DNS resolution gaps, and unvalidated redirects.
2. Rate limiting trusts client-supplied forwarding headers, allowing brute-force protection to be bypassed.
3. Authenticated users can pass arbitrary LLM/embedding provider and model identifiers. With open registration, this creates cost abuse, server-side model-loading risk, and denial-of-service potential.
4. Several internal or shared surfaces permit cross-tenant access or expose useful reconnaissance.

## Security fix update — 2026-09-07

The four remotely relevant High findings were fixed:

- SEC-H1 now uses exact origin matching for the server allowlist, intersects any request allowlist with the secure defaults, rejects non-canonical numeric host spellings, validates every DNS answer for public routability, and manually follows/revalidates redirects.
- SEC-H2 now honors `X-Forwarded-For` and `X-Real-IP` only when the immediate peer is in `TRUSTED_PROXY_IPS`; direct clients use their actual socket address. The setting is documented in `.env.example`.
- SEC-H3 now validates analysis provider/model overrides against an explicit server-enabled set. Local models are limited to the canonical installed model lists plus operator-managed environment overrides; cloud model IDs are bounded to the supported provider catalog. This prevents arbitrary Hugging Face repository loading and unbudgeted model invocation through the public analysis schema.
- SEC-M3 (Dependency builds not locked) is now fixed: Dockerfile builder stage uses `uv sync --locked` with `uv.lock` for reproducible, auditable dependency installation.

One Medium finding was also fixed:

- SEC-M6 (Upload/URL ingestion rate limits): added per-endpoint rate limits (10/minute default) and a per-process ingestion semaphore.

Remaining Medium findings still need product or deployment decisions before a safe code change: broad preview-origin CORS, public health detail, internal-service tenant binding, MCP tenant scoping, and prompt-injection controls.

## Findings

### SEC-H1: URL-ingestion SSRF protections are bypassable

- **Severity:** High
- **Files:**
  - `apps/api/app/services/search_service.py:140-176`
  - `apps/api/app/services/search_service.py:210-213`
  - `apps/api/app/api/v1/knowledge_bases.py:36`
- **Status:** Fixed on 2026-09-07
- **Residual note:** DNS is checked before each request and redirects are revalidated, but DNS answers can still change between validation and connect unless connection-time IP pinning is added later.
- **Issues:**
  - Allowlist checks use `url.startswith(prefix)`, so `https://api.github.com.attacker.example/...` can satisfy a prefix for `https://api.github.com`.
  - Validation parses only literal IP addresses and does not resolve DNS before fetch.
  - Decimal, hexadecimal, octal, and other non-canonical IP forms can evade literal parsing.
  - `follow_redirects=True` permits a redirect to an internal address without revalidation.
  - A requester can pass a custom allowlist that weakens the server policy.
- **Potential impact:** An authenticated user may read internal services, private network addresses, cloud metadata endpoints, Qdrant, MongoDB, Ollama, or llama.cpp and ingest their responses into a knowledge base.
- **Recommended minimal fix:**
  - Match allowlists by exact hostname or suffix hostname, not string prefix.
  - Reject non-canonical IP representations.
  - Resolve DNS once, validate every resolved address, and connect to the validated address or repeat validation immediately before connect.
  - Follow redirects manually and validate every redirect destination.
  - Do not let a request-level allowlist exceed the server-configured policy.

### SEC-H2: Rate limiting trusts spoofable forwarding headers

- **Severity:** High
- **File:** `apps/api/app/core/rate_limiter.py:16-34`
- **Status:** Fixed on 2026-09-07
- **Issue:** The rate limiter prefers the first `X-Forwarded-For` or `X-Real-IP` header without a trusted-proxy boundary.
- **Potential impact:** A remote client can rotate forwarding headers and receive a fresh bucket for login, registration, or other rate-limited endpoints.
- **Recommended minimal fix:** Use `request.client.host` by default. Trust forwarding headers only when the immediate peer is in an explicit trusted-proxy CIDR list, and validate the parsed address.

### SEC-H3: Authenticated users can request arbitrary provider/model IDs

- **Severity:** High
- **Files:**
  - `apps/api/app/api/v1/schemas/analysis.py:29-50`
  - `apps/api/app/core/model_registry.py:61`
  - `apps/api/app/core/model_registry.py:403`
- **Status:** Fixed on 2026-09-07 for the public analysis API; service/internal callers should still move to a centralized policy module before broader exposure
- **Issues:**
  - Provider and model fields are free-form strings.
  - Server-owned Gemini/NVIDIA keys can be directed to arbitrary model IDs.
  - Local Hugging Face/sentence-transformers paths can download and load arbitrary repositories.
  - Repeated unique model selections can consume RAM, disk, and network resources.
- **Potential impact:** Cost abuse, model-loading denial of service, and unsafe code/model loading from untrusted repositories.
- **Recommended minimal fix:** Enforce server-side enums for provider and model selection; ignore or reject unlisted values; never pass raw user input to model-loading libraries.

### SEC-M1: CORS permit list is broader than necessary

- **Severity:** Medium
- **File:** `apps/api/app/main.py:371-379`
- **Status:** Open at audit-file creation
- **Issue:** `allow_origin_regex` accepts arbitrary `vercel.app`, `netlify.app`, and `pages.dev` subdomains with credentials enabled.
- **Potential impact:** Any third-party deployment on these shared platforms is treated as an allowed origin.
- **Recommended minimal fix:** Enumerate exact frontend origins and remove broad hosted-platform patterns outside preview environments.

### SEC-M2: Public health response exposes operational details

- **Severity:** Medium
- **File:** `apps/api/app/api/v1/health.py:29-61`
- **Status:** Open at audit-file creation
- **Issue:** The unauthenticated health endpoint exposes environment, model/provider configuration, key-presence flags, file support, and hardware details.
- **Potential impact:** Reconnaissance for targeted attacks.
- **Recommended minimal fix:** Return only `status` and version publicly; keep provider/model/hardware diagnostics behind authentication.

### SEC-M3: Dependency builds are not locked in the API image

- **Severity:** Medium
- **Files:**
  - `apps/api/pyproject.toml`
  - `apps/api/Dockerfile`
- **Status:** Fixed on 2026-09-07
- **Fix:** Updated Dockerfile builder stage to use `uv sync --locked` with `uv.lock` for reproducible, auditable dependency installation. The lockfile is committed to the repository and used as the single source of truth for dependency versions.
- **Issue:** Runtime dependencies used broad lower bounds, and the Docker build installed the project without consuming the lockfile as the source of truth.
- **Potential impact:** Builds were not reproducible and could pull unaudited packages.

### SEC-M4: Internal ingestion endpoint trusts caller-provided tenant fields

- **Severity:** Medium
- **File:** `apps/api/app/api/v1/internal.py:56-77`
- **Status:** Open at audit-file creation
- **Issue:** The endpoint accepts `user_id` and `kb_id` from the request body under a service-token model.
- **Potential impact:** A service token can write into another tenant's knowledge base unless token scope explicitly binds tenant identity.
- **Recommended minimal fix:** Bind service tokens to tenants/scopes, remove caller-selected ownership fields, and validate payloads with strict schemas.

### SEC-M5: MCP stdio server is not tenant scoped

- **Severity:** Medium
- **File:** `apps/api/app/mcp/server.py:171-238`
- **Status:** Open at audit-file creation
- **Issue:** MCP tools can list all knowledge bases and search arbitrary KB IDs without an authenticated principal.
- **Potential impact:** A local MCP client can access cross-tenant data on a shared database.
- **Recommended minimal fix:** Require a configured service identity, enforce KB ownership or explicit allowed-KB scopes, and gate MCP startup behind an explicit setting.

### SEC-M6: Uploads and URL ingestion lack their own rate/concurrency limits

- **Severity:** Medium
- **Files:**
  - `apps/api/app/api/v1/knowledge_bases.py`
  - `apps/api/app/ingestion/pipeline.py`
- **Status:** Fixed on 2026-09-07
- **Fix:** Added per-endpoint rate limits (`rate_limit_upload_per_minute` and `rate_limit_url_ingest_per_minute`, default 10/minute) to both upload endpoints via SlowAPI. Ingestion background jobs are serialized per API process via a dedicated semaphore in `ingestion/pipeline.py`.
- **Issue:** Ingestion endpoints were not covered by endpoint-specific limits, and background embedding jobs were not globally capped.
- **Potential impact:** One authenticated user could monopolize CPU, RAM, embeddings, Qdrant, and MongoDB.

### SEC-M7: Prompt-injection controls rely mostly on prompt text

- **Severity:** Medium
- **Files:**
  - `apps/api/app/generation/generator.py`
  - `apps/api/app/verification/verifier.py`
- **Status:** Open at audit-file creation
- **Issue:** User-uploaded and web-sourced evidence remains untrusted text, but structural filtering is prompt-level and can be weakened by context pruning.
- **Potential impact:** A poisoned chunk can steer the generated answer or contaminate verification output.
- **Recommended minimal fix:** Keep delimiters intact during pruning, enforce output sanitization, label web evidence separately, and retain source/integrity provenance.

## Low-risk and hygiene findings

1. **Local compose exposure:** Qdrant and MongoDB are exposed without production-grade authentication/TLS in local development configuration. Bind to loopback or require credentials where practical.
2. **Password maximum length:** Add a maximum password length aligned with bcrypt's 72-byte effective input limit.
3. **JWT audience/issuer:** Add `aud` and `iss` claims and consider separate signing secrets for user and service tokens.
4. **Sensitive logging:** Avoid logging full claim or document text on failure paths.
5. **Frontend token storage:** JWTs stored in web storage remain vulnerable if XSS is later introduced; prefer HTTP-only cookies or short-lived access tokens with refresh isolation.

## Missing security regression tests

Add blackbox and whitebox tests for:

- Suffix-domain allowlist bypass.
- Decimal/hex/octal IP URL forms.
- DNS names that resolve to private or loopback addresses.
- Redirects to private addresses and cloud metadata.
- Spoofed `X-Forwarded-For` rate-limit bypass.
- Rejection of unsupported provider/model IDs.
- Cross-tenant MCP tool access.
- Cross-tenant internal ingestion.
- Public health response information leakage.

## Verification commands

```bash
cd apps/api
python -m ruff check app --select S,B
python -m pytest tests -q --no-cov
```

Final verification on 2026-09-07:

- `ruff check app tests`: pass
- `ruff format --check app tests`: pass
- `pytest tests -q --no-cov`: **133 passed**
- New regressions cover suffix-domain allowlist rejection, custom-allowlist privilege widening, redirect-to-private-host rejection, private DNS answers, trusted and spoofed forwarding-header behavior, and arbitrary model/repository rejection.
- Live remote exploitation was not attempted; tests use mocked network transport and fake DNS answers.

When a local server is running:

```bash
curl -i -X OPTIONS http://localhost:8000/api/v1/auth/login
curl -s http://localhost:8000/api/v1/health
```

## Priority order

1. Fix URL-ingestion SSRF validation and redirect handling.
2. Fix trusted-proxy rate-limit keying.
3. Add a server-side provider/model allowlist.
4. Restrict internal ingestion and MCP tools to explicit tenant scopes.
5. Reduce public health disclosure and broaden upload limiting.
6. Pin/freeze dependency installation in the API image.
