# TRUSTRAG — Architecture Decision Log

Records material decisions made during development.
Any deviation from the specification must be logged here with rationale.

---

## D-01: LangChain as the sole AI abstraction layer

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** All LLM and embedding interactions go through LangChain interfaces (`ChatGoogleGenerativeAI`, `HuggingFaceEmbeddings`). No direct Google GenAI SDK or `requests` calls to Gemini.

**Rationale:** Spec §7 mandates `TRUSTRAG → LangChain → langchain-google-genai → Gemini API`. This enforces a clean swap boundary: changing the LLM provider requires updating `model_registry.py` only, not routes, services, or workflow nodes.

**Consequences:** Adds LangChain as a mandatory dependency. Abstractions slightly increase indirection. Accepted because the spec is explicit.

---

## D-02: LangGraph for recovery/Agentic-RAG workflows only

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** LangGraph is used exclusively for stateful workflows: the main RAG reliability loop, adaptive recovery, and optional Agentic-RAG. CRUD operations, helper functions, and ingestion use plain Python.

**Rationale:** Spec §18: "Do not use LangGraph for ordinary CRUD or deterministic helper functions." Prevents over-engineering simple operations.

---

## D-03: MongoDB Atlas (cloud M0) for all metadata and state

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** MongoDB Atlas M0 free-tier cluster is the only persistence for application data. Local MongoDB is NOT used — this enforces cloud-first from day one.

**Rationale:** Spec §8. Avoids divergence between local and deployed environments. Atlas M0 is free and sufficient for the MVP.

---

## D-04: Qdrant Cloud for production vectors; local Docker for development

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** `docker-compose.yml` runs Qdrant locally. `QDRANT_URL` environment variable switches between local and cloud. Production requires Qdrant Cloud free tier.

**Rationale:** Spec §10. Local Qdrant is identical to cloud for API compatibility. No code changes needed to switch.

---

## D-05: JWT HS256, short-lived access tokens, no refresh tokens for MVP

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** JWT authentication using HS256 (symmetric). Access token expiry is configurable (default 60 min). No refresh token for MVP — users re-authenticate on expiry.

**Rationale:** Spec §20 requires JWT auth but does not specify refresh strategy. Symmetric JWT avoids key management complexity for a portfolio project. Refresh tokens can be added in Phase 12.

**Risk:** Tokens cannot be individually revoked before expiry. Mitigated by short expiry window.

---

## D-06: SSE (Server-Sent Events) for live analysis traces

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** SSE via FastAPI `StreamingResponse`. Not WebSockets.

**Rationale:** Spec §23 specifies SSE explicitly. SSE is unidirectional (server → client) which matches the trace stream use case perfectly. Simpler than WebSockets; works through HTTP/1.1 proxies.

---

## D-07: Centralized `config/models.yaml` + `.env` separation

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** `.env` holds secrets and deployment-specific values. `models.yaml` holds model IDs, thresholds, retrieval config, and tuning parameters. A typed `ModelConfig` wrapper provides validated access. Zero model IDs are permitted in Python source files.

**Rationale:** Spec §6. Allows model changes without code review. Configuration is versioned and recorded per analysis run.

---

## D-08: No Redis, Celery, Kafka, or Kubernetes for MVP

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** Background processing uses FastAPI `BackgroundTasks` for ingestion. No message queue, no worker fleet.

**Rationale:** Spec §34 explicitly forbids these for MVP unless a demonstrated requirement exists. A portfolio MVP with moderate document volumes does not require distributed queuing.

**Future trigger:** If ingestion queue depth or SSE broadcasting becomes a bottleneck, Redis + a simple worker will be added with a new ADR.

---

## D-09: Tailwind CSS (spec override of Vanilla CSS default)

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** Frontend uses Tailwind CSS v3 as specified in the TRUSTRAG spec §3.

**Rationale:** Spec explicitly lists Tailwind CSS. This overrides the default Vanilla CSS guideline. Design tokens are centralized in `tailwind.config.js`.

---

## D-10: sentence-transformers/all-MiniLM-L6-v2 for embeddings (local, free)

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** Embeddings are generated locally using `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). No external embedding API. Model is downloaded once and cached.

**Rationale:** User requirement: no paid APIs. `all-MiniLM-L6-v2` is fast, well-understood, and free. Embedding model is configurable in `models.yaml` — swapping to a larger model requires only config change + re-indexing.

**Consequence:** Qdrant collections are configured for 384 dimensions. Changing the embedding model requires incrementing `embedding.version` in `models.yaml` and re-indexing all collections.

---

## D-11: "gemini-2.5-flash" as default LLM (user requested "Gemini 3.5 Flash")

**Date:** 2026-08-27  
**Status:** Accepted  
**Phase:** 0

**Decision:** The configured model ID is `gemini-2.5-flash`. The user requested "Gemini 3.5 Flash" which does not exist as a published model ID. `gemini-2.5-flash` is the current free-tier Flash generation model.

**Action required:** Verify the exact model ID at [Google AI Studio](https://aistudio.google.com/app/apikey) before deployment and update `models.yaml` if needed.
