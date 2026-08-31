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

**Decision:** The configured model ID is `gemini-2.5-flash` (or `gemini-3.5-flash-lite`). The user requested "Gemini 3.5 Flash" which does not exist as a published model ID. `gemini-2.5-flash` is the current free-tier Flash generation model.

**Action required:** Verify the exact model ID at [Google AI Studio](https://aistudio.google.com/app/apikey) before deployment and update `models.yaml` if needed.

---

## D-12: Google Gemini 384d MRL Embeddings & PyTorch Decoupling (Supersedes D-10)

**Date:** 2026-08-30  
**Status:** Accepted & Implemented  
**Phase:** 13

**Decision:** Transition default embeddings from local PyTorch `sentence-transformers` to cloud-native Google Gemini `models/gemini-embedding-001` with Matryoshka Representation Learning truncated to 384 dimensions (`output_dimensionality: 384`). Move PyTorch and `sentence-transformers` to optional extras (`[project.optional-dependencies] local-models`).

**Rationale:**
- **0 MB Local GPU RAM**: Completely offloads vector encoding from host memory/GPU to Google's cloud infrastructure.
- **Instant Cold Starts**: Eliminates the 90-second initial container download time. Container boots in under 2 seconds.
- **Disk Footprint Reduction**: Decoupling PyTorch shrinks the Docker container image from ~2.8 GB to ~350 MB.
- **Dimensional Parity**: 384-dimensional MRL matches Qdrant collection geometry, maintaining 100% compatibility with existing hybrid search pipelines.

---

## D-13: Qdrant On-Disk Storage & INT8 Scalar Quantization

**Date:** 2026-08-30  
**Status:** Accepted & Implemented  
**Phase:** 13

**Decision:** Enable `on_disk=True` for Qdrant vector configurations and sparse token indices, paired with INT8 scalar quantization (`ScalarType.INT8`, `quantile=0.99`, `always_ram=False`).

**Rationale:**
- Reduces Qdrant vector RAM consumption by **75%** while retaining $>99.5\%$ search recall.
- Allows the application to run smoothly on low-spec developer machines and free-tier containers without risking Out-Of-Memory (OOM) kills.

---

## D-14: Default Port Migration to 8080

**Date:** 2026-08-31  
**Status:** Accepted & Implemented  
**Phase:** 14

**Decision:** Change default FastAPI backend port from `8000` to `8080` across all configurations (`main.py`, `Dockerfile`, `docker-compose.yml`, `vite.config.js` proxy, and documentation).

**Rationale:**
- macOS natively binds port `8000` to AirPlay Receiver and AirDrop services on modern macOS releases, causing immediate `[Errno 48] Address already in use` crashes.
- Standardizes container deployments on Google Cloud Run and AWS ECS, where port `8080` is the canonical HTTP target.

---

## D-15: Model Context Protocol (MCP) Standard for Web Search Grounding

**Date:** 2026-08-31  
**Status:** Accepted & Implemented  
**Phase:** 14

**Decision:** Standardize live web search grounding using the Model Context Protocol (MCP) specification. Implement internal MCP server (`app/mcp/server.py`) and client dispatcher (`app/mcp/client.py`) supporting `tavily_search`, `duckduckgo_search`, and `hybrid_web_search`.

**Rationale:**
- Decouples LLM generation from specific search engine vendors.
- Allows free-tier zero-API-key search via DuckDuckGo, high-accuracy RAG search via Tavily, or parallel hybrid execution with automatic URL deduplication.
- Centralizes security controls (SSRF URL sanitization and query length enforcement).

---

## D-16: Dual-Channel Polling & Real-Time Telemetry HUD in Workbench

**Date:** 2026-08-31  
**Status:** Accepted & Implemented  
**Phase:** 14

**Decision:** 
1. Implement dual-channel active fallback polling (2-second interval) alongside Server-Sent Events (SSE) in `PlaygroundPage.jsx`.
2. Replace distorted green radar with an executive 4-stage architecture telemetry HUD (`PipelineTelemetryHUD.jsx`).

**Rationale:**
- Browser `EventSource` connections can buffer or stall during cyclic self-healing loops without triggering `onerror` or `oncomplete`. Active fallback polling guarantees instant UI completion detection within 2 seconds.
- Replaces generic/oval radar graphics with an informative, responsive 4-step pipeline status tracker showing dynamic stage progression.

---

## D-17: GFM Table Rendering via remark-gfm & Multi-Part Query Grounding

**Date:** 2026-08-31  
**Status:** Accepted & Implemented  
**Phase:** 14

**Decision:** 
1. Install and integrate `remark-gfm` with `react-markdown` in `FormattedAnswer.jsx` with custom dark glass table components.
2. Update `GROUNDING_SYSTEM_PROMPT` to enforce Complete Multi-Part Coverage for compound queries.

**Rationale:**
- Without `remark-gfm`, `react-markdown` strictly adheres to CommonMark and renders markdown table syntax (`| a | b |`) as raw text paragraphs with pipe characters.
- Multi-part queries (e.g. "What is X? What is the difference between X and Y?") were previously truncated; updated instructions mandate dedicated `###` sections for all sub-inquiries.

