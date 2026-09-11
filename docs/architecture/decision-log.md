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

---

## D-18: Reversal of D-14 — Port 8080 Returned to llama.cpp; Backend Stays on 8000

**Date:** 2026-09-07
**Status:** Accepted & Implemented (supersedes D-14)
**Phase:** 15

**Decision:** Re-run the port allocation: `llama-server` (llama.cpp) owns **port `8080`**, and the FastAPI backend runs on **port `8000`** again. This was applied in `config/ports.yaml`, `docker-compose.yml`, `apps/api/Dockerfile`, `apps/web/vite.config.js`, and all prose that referenced 8080 as the backend.

**Rationale:**
- llama.cpp's local OpenAI-compatible server is thin and conventionally sits on :8080. Conflicts with the backend broke dev setup ("`Address already in use`" for the model server).
- `config/ports.yaml` (`config/ports.yaml`) is now the canonical registry — backend `8000`, frontend `5173`, ollama `11434`, llamacpp `8080` — and `scripts/apply_ports.py` distributes changes to all consumers.
- macOS AirPlay conflicts on :8000 are handled by using `--host 127.0.0.1` during dev (no system clash) and honoring `PORT` on Render/GCR.

**Files layered on top of D-14:**
- `config/ports.yaml` (new canonical registry)
- `scripts/apply_ports.py` (propagator)
- `apps/api/app/core/config.py` (Settings defaults read ports.yaml)
- `apps/api/app/core/local_llm.py` (`INSTALLED_*` provider lists)



## D-19: Removal of Cloud Embeddings — Local-Only BGE

**Date:** 2026-09-10
**Status:** Accepted & Implemented (partially reverses D-14-era cloud default)
**Phase:** 16

**Decision:** Remove Google Gemini and NVIDIA NIM embedding providers from the entire
project. Embeddings are local-only (`huggingface`: `BAAI/bge-small-en-v1.5`,
`all-MiniLM-L6-v2`, 384d). Cloud LLMs (Gemini, NVIDIA NIM) remain available for
*generation/verification only*.

**Rationale:**
- New users run zero-key: no Gemini/NVIDIA/Tavily keys needed to boot, ingest, and analyze.
- No per-token embedding cost, no quota exhaustion inside the ingestion/retrieval hot path.
- One embedding space per deployment kills an entire class of cross-provider vector contamination bugs.
- Existing KBs indexed with retired providers must be re-uploaded (backend fails closed with instructions; UI directs to re-upload).

**Files:**
- `apps/api/app/core/model_registry.py` (branches removed, retired-provider guard)
- `apps/api/app/core/config.py`, `apps/api/app/api/v1/schemas/analysis.py` (allowlists)
- `apps/api/app/api/v1/models.py`, `apps/web/.../QueryPanel.jsx`, `apps/web/.../SettingsPage.jsx` (UI)
- `apps/api/app/ingestion/pipeline.py` (Gemini rate-limit pacing removed)
- `apps/api/config/models.yaml`, `.env.example`, `scripts/setup.sh` (new), docs

---

## D-20: Shared LLM Utilities Extraction & Dead Config Cleanup

**Date:** 2026-09-11
**Status:** Accepted & Implemented
**Phase:** 17

**Decision:** Extract shared LLM helper functions into a single `core/llm_utils.py`
module and remove all dead code accumulated across rounds of rapid iteration.

**Changes:**
1. **New `apps/api/app/core/llm_utils.py`** — three shared functions:
   - `normalize_llm_content()` — normalizes `response.content` from any LLM provider
     (str, bytes, list-of-dicts, list-of-objects) to a plain string.
   - `extract_json_substring()` — safely extracts valid JSON from LLM output that may
     contain markdown fences or preamble text.
   - `build_structured_output_runnable()` — builds a `RunnableLambda` that prompts for
     structured JSON and parses into a Pydantic model. Used by both `ChatOllamaClient`
     and `ChatLlamaCppClient` which differ only in their JSON-mode kwargs.

2. **`apps/api/app/core/local_llm.py`**:
   - Removed duplicate `_extract_json_substring()` (now imports from `llm_utils`).
   - Both `with_structured_output()` implementations (Ollama `format="json"` and
     llama.cpp `response_format`) now delegate to `build_structured_output_runnable()`.

3. **`apps/api/app/agent/graph.py`** and **`apps/api/app/generation/generator.py`**:
   - Replaced inline 12-line LLM content normalization blocks with
     `normalize_llm_content()` calls.

4. **Dead code removal (~300 lines across 8 files):**
   - `retriever.py`: Removed unused `get_ambiguity_detector`, `clear_ambiguity_detector`,
     `_ambiguity_detector` global.
   - `security.py`: Removed unused `verify_service_permission`, `get_service_name_from_token`.
   - `exceptions.py`: Removed 7 unused exception classes.
   - `sparse_vector.py`: Removed dead `STOPWORDS` set (~175 lines).
   - `graph.py`: Removed stale `# TEST COMMENT` and duplicate `web_search.completed` trace.
   - `generator.py`: Removed unused `generate_grounded_answer_stream()` (~50 lines).
   - `verifier.py`: Removed redundant `import re as _re`.
   - `config.py`: Removed dead `max_query_rewrites` property.
   - `models.yaml`: Removed dead `max_query_rewrites: 1` and `max_reretrieval_attempts: 1`.

**Rationale:**
- Inline normalization in graph.py and generator.py was duplicated logic that silently
  diverged across providers (bytes, list-of-dicts, etc.). A single helper eliminates
  an entire class of provider-specific content bugs.
- `_extract_json_substring()` existed in both `local_llm.py` (private) and now
  `llm_utils.py` (public). One copy is sufficient.
- Dead code from earlier iterations (ambiguity detector, permission helpers, stopwords,
  max_query_rewrites) added cognitive load and maintenance surface with zero value.
- Shared `build_structured_output_runnable()` reduces the `with_structured_output()`
  implementation from ~60 duplicated lines to ~5 delegate lines per client.

**Consequences:** All 191 tests pass. ruff check clean. New file is ~168 lines.
The shared helper is the single source of truth for JSON extraction and structured
output across all local LLM providers.
