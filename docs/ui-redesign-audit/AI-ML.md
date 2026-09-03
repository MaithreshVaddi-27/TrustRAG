# AI/ML Audit — TrustRAG ui-redesign

**Scope:** `apps/api/app` — agent graph, retrieval, reranking, verification, ingestion, generation, model registry, caches, config. READ-ONLY, evidence verified.

**Default stack** (from `apps/api/config/models.yaml`): Ollama `gemma4:e2b-it-qat` (temp 0.2, max_output 2048), verifier `gemma4:e2b` (temp 0.0, max_output 1024), embeddings `BAAI/bge-small-en-v1.5` 384d (actual — see Critical 3), reranker `ms-marco-MiniLM-L-6-v2` **disabled**, dense/sparse top_k 20, RRF k=60, fusion_top_k 20, max_context_chunks 8, chunk 512/64 chars, abstain_below 0.50, max 2 recovery attempts.

**Per-request LLM accounting (default path, confirmed):** happy path = 3 LLM calls (1 generation + 1 claim decomposition + 1 batched NLI) + **2 query embeddings (1 wasted — High 1)**. Worst case with 2 recovery attempts ≈ 11 LLM calls. Generation context: ~500-token system prompt + ≤5500-char pruned context — fits Ollama `num_ctx 4096`.

---

## Critical

**[Critical] Entire persistent embedding disk cache is dead code — never wired in** (Confirmed)
- Location: `app/core/disk_cache.py` (whole file); `app/core/model_registry.py:274-375` (`CachedEmbeddingsWrapper`)
- Evidence: Zero production callers — `get_cached_embedding`/`get_cached_embeddings_batch` are only defined and referenced inside `CachedEmbeddingsWrapper`, which `get_embedding_model()` (model_registry.py:378-561) never returns. `tests/test_local_llm.py:83-90` uses `isinstance(..., (OllamaEmbeddings, CachedEmbeddingsWrapper))`, so tests pass either way. disk_cache.py's own docstring: *"saving 100% of compute load on repeat or revision embeddings."*
- Impact: Every re-upload, revision, or self-heal re-embeds identical text from scratch. Ingestion (pipeline.py:111) calls `embed_model.embed_documents` directly with no cache lookup. Largest single waste in the repo.
- Recommendation: Return `CachedEmbeddingsWrapper(base)` from `get_embedding_model()` (pass-throughs already implemented). ~5-line change; SQLite WAL + sha256 keys already built.

**[Critical] Every uncached request embeds the same query twice** (Confirmed)
- Location: `app/agent/graph.py:701-705` vs `app/retrieval/retriever.py:51,67`
- Evidence: graph.py:703 `q_vec = await emb_model.aembed_query(query)` for the semantic-cache check calls the raw model, bypassing `QueryEmbeddingLRUCache` (1024 entries) which wraps only `dense_search`. On a miss, `dense_search` re-embeds the identical query through its own LRU.
- Impact: ~2x query-embedding compute on every uncached request; the graph-level embedding never populates the retrieval LRU.
- Recommendation: Resolve the query vector once through the cached wrapper (or pass `q_vec` into `hybrid_search`). Saves ~50% of per-request embedding calls.

**[Critical] models.yaml provider/model settings are unreachable — env defaults always win** (Confirmed)
- Location: `app/core/config.py:296-311` (embedding; same pattern for llm/verification)
- Evidence: `embedding_provider` does `settings.embedding_provider or fallback`, but `Settings.embedding_provider` defaults to `"huggingface"` (config.py:118-122) and is therefore always truthy — the models.yaml value can never apply. Same always-truthy bug for `llm_provider` ("ollama") and `verification_provider`.
- Impact: The declared models in models.yaml are fiction; operators editing it silently get no effect. All yaml-declared optimizations (prompt_caching, embedding choice, KV q4_0) are unreachable.
- Recommendation: Distinguish "unset" (None) from "default" in Settings; log the *resolved* provider/model triple at startup.

## High

**[High] Verifier is same model family as generator — self-verification bias** (Confirmed identity / Likely impact)
- Location: models.yaml — verification `ollama/gemma4:e2b` vs llm `ollama/gemma4:e2b-it-qat`
- Evidence: Generator and verifier are both Gemma-4 E2B; a generator that fabricates from weak context is checked by the same model family using the same evidence window. Real mitigations exist: 2-call design (decompose + batched NLI, verifier.py:263), coverage/contradiction thresholds (0.80/0.20), `reliability_score = coverage * (1 - contradiction_rate)` (graph.py:474), all-NEUTRAL fallback marks unsupported (verifier.py:310-320), genuine sha256 integrity audit.
- Impact: NLI verdicts likely inherit the generator's blind spots; "verified" label overstates independence.
- Recommendation: Default the verifier to a different family (nvidia `llama-3.3-70b` path, or a cross-encoder NLI model — deterministic and zero LLM cost).

**[High] Web-search "both" mode returns 2x requested results into context** (Confirmed)
- Location: `app/services/search_service.py:246`; `app/agent/graph.py:237-239`; `app/services/analysis_service.py:337`
- Evidence: `final_results = combined[: max_results * 2]` (search_service.py:246). graph.py asks `max_results: 5` and forces `provider: "both"`; analysis-level default is `web_search_provider: "both"` (analysis_service.py:337). A request intending 5 web citations can inject up to 10 web chunks.
- Impact: ~2x web-grounding tokens per web-enabled request; dilutes the 8-chunk local context budget; Tavily+DDG both fired per query (2 API round trips).
- Recommendation: Cap the fused list at `max_results`; make "both" opt-in.

**[High] ~500-token system prompt re-sent on every generation and recovery attempt; no prompt caching on default paths** (Confirmed)
- Location: `app/generation/generator.py:19-48,123`; `app/core/local_llm.py:316` vs `136`
- Evidence: `GROUNDING_SYSTEM_PROMPT` (~500 tokens) prepended on every `ainvoke`, including all recovery rewrites. `cache_prompt=True` exists only in `ChatLlamaCppClient` (local_llm.py:316); Ollama (`ChatOllamaClient`, num_ctx 4096, keep_alive "5m", :136-152) and Gemini get nothing. models.yaml `optimization.prompt_caching: true` is declared but only implemented for llama.cpp.
- Impact: Worst-case request re-sends the identical system prompt 5+ times ≈ 2500+ wasted tokens of prefill; meaningful latency per turn for a 2B local model.
- Recommendation: Keep the prefix byte-identical (already is), leverage Ollama keep_alive KV caching between recovery attempts, reuse the unchanged context prefix in recovery re-renders.

**[High] Reranker threshold bug: raw logits gated at 0.80 without sigmoid; disabled-path heuristic truncates context too aggressively** (Confirmed code / Likely quality impact)
- Location: `app/retrieval/reranker.py:70` (raw CrossEncoder logits vs `>= 0.80`), `:40-42` (disabled path: top-1 dense ≥ 0.78 → cut to 4 chunks)
- Evidence: ms-marco MiniLM logits are unbounded. Since `reranker.enabled: false`, the ACTIVE path is the heuristic — BGE-small cosine scores cluster tightly, so a single 0.78 hit cuts context from 8 chunks to 4, discarding corroborating evidence the verifier needs for its 0.80 coverage threshold.
- Impact: Premature context truncation → more ABSTAIN/recovery loops → each recovery ≈ 3-4 extra LLM calls. Both a quality and a cost bug.
- Recommendation: Apply sigmoid before thresholding; in the heuristic path require top-1 ≥ 0.78 AND a score gap (top1 − top2 > 0.15) before truncating.

**[High] Web-search chunks are hard-coded "VERIFIED", bypassing the integrity audit** (Confirmed)
- Location: `app/agent/graph.py:262`
- Evidence: `"integrity_status": "VERIFIED"` set on every web chunk at construction → skips `audit_evidence_integrity` (genuine sha256 verification for local chunks, integrity.py:53-88) and enters `verified_chunks` directly (graph.py:265-266).
- Impact: Untrusted web snippets display with the same VERIFIED status as hash-audited KB text — provenance is partially theater for web citations; also feeds unverified content into NLI coverage scoring.
- Recommendation: Tag web chunks `WEB_UNVERIFIED`; let NLI be their only validation; surface the distinction in UI/traces.

**[High] Verification fallback drops request-scoped provider/model routing** (Confirmed)
- Location: `app/verification/verifier.py:378`
- Evidence: Per-claim fallback calls `verify_claim_nli(text, chunks)` with no provider/model args, while the primary batch path (:263) forwards them. A request routed to Gemini/NVIDIA silently falls back to default Ollama on batch failure.
- Impact: Unpredictable cost spikes and inconsistent verdict quality mid-request.
- Recommendation: Thread provider/model through the fallback like the batch path.

**[High] Decomposition failure verifies the whole answer as ONE claim** (Confirmed)
- Location: `app/verification/verifier.py:213-214` (`return [answer]`)
- Evidence: If structured output parsing fails once, the full multi-sentence answer becomes a single NLI claim — a single CONTRADICTED/NEUTRAL verdict collapses all nuance; coverage math becomes all-or-nothing.
- Impact: Verdict volatility exactly where verification matters most; triggers unnecessary full recovery loops (cost) or masks partial hallucination (quality).
- Recommendation: Fallback to the existing deterministic `extract_claim_triple_heuristic` (verifier.py:26-73) — already written, zero-cost, sentence-based.

## Medium

**[Medium] Self-healing re-index: 1000 chunks in one giant embed batch, N+1 `find_one`, no cache** (Confirmed)
- Location: `app/agent/graph.py:103-210` (`.to_list(1000)` :134; single `embed_documents` :151-153; per-chunk `find_one` :142)
- Impact: ~1001 sequential Mongo round trips plus full re-embedding that the dead disk cache would eliminate.
- Recommendation: Batched `find` projection, one `find` for documents, route embeddings through the wired disk cache — a healed index should be nearly free after the first time.

**[Medium] Semantic cache is O(n) pure-Python cosine with pop(0) eviction, process-local** (Confirmed)
- Location: `app/core/semantic_cache.py:28-29,69-78,109`
- Evidence: Module-level list, max 500 entries, linear cosine scan in Python per lookup, `pop(0)` O(n), per-process (lost on restart, unshared across workers).
- Impact: Cache hit rate resets on every deploy/worker recycle — the "0% compute load" fast path (graph.py:694) is unreliable.
- Recommendation: Numpy matrix (stack+normalize on write, one dot product on read) or a Qdrant cache collection (durable, shared).

**[Medium] Structured output injects the full JSON schema into every prompt** (Confirmed)
- Location: `app/core/local_llm.py:199-218`
- Evidence: `with_structured_output` appends an indented `json.dumps(schema)` to every decompose/NLI call — hundreds of constant tokens re-serialized per request; also breaks prompt-prefix caching stability.
- Recommendation: Cache serialized schema per (tool, schema); prefer Ollama native `format=` JSON mode.

**[Medium] Ingestion: no chunk dedup before embedding; inter-batch pacing only for google_genai** (Confirmed)
- Location: `app/ingestion/pipeline.py:105-128`
- Evidence: `text_hash` (sha256, :84) computed but never used to skip embedding (:111); batches of 20 with `sleep(1.0)` gated on `cfg.embedding_provider == "google_genai"`.
- Impact: Duplicate pages/boilerplate re-embedded repeatedly; HF/NVIDIA providers get no rate pacing.
- Recommendation: Dedup on `text_hash` within the upload set; consult the disk cache (Critical 1).

**[Medium] Chunker: 512-char character windows with no sentence alignment** (Confirmed design)
- Location: `app/ingestion/chunker.py:33-70` (512/64, `text[start:end].strip()`)
- Impact: Mid-sentence splits fragment NLI evidence (degrades coverage → more recovery loops); 64-char overlap ≈ 12.5% duplicated text re-embedded per document.
- Recommendation: Snap windows to sentence terminators (deterministic regex); consider 800-1000 chars to cut chunk count ~40% at max_context_chunks 8.

**[Medium] Sparse vectors are hashed TF with no IDF — "BM25" claim is misleading** (Confirmed)
- Location: `app/ingestion/sparse_vector.py:1-241` (docstring says "BM25 fallback"; `xxhash.xxh32(token) % 1_000_000` zone-boosted raw TF, :222-241)
- Impact: The sparse half cannot down-weight ubiquitous terms — recall skews toward boilerplate-heavy chunks; dense effectively does the ranking.
- Recommendation: Maintain a small per-KB IDF map at ingestion (deterministic), or rename to what it is.

**[Medium] Qdrant `get_collection()` round trip on every dense search for dimension alignment** (Confirmed)
- Location: `app/retrieval/retriever.py:79-91`
- Impact: +1 network round trip per query per node; silently absorbs dimension mismatches (384→768 would degrade recall invisibly).
- Recommendation: Cache collection dims per name; hard-error on mismatch.

**[Medium] SSE progress is 1 Hz Mongo polling per client** (Confirmed)
- Location: `app/services/analysis_service.py:310` (`asyncio.sleep(1.0)`, no_event_ticks < 120)
- Impact: 10 concurrent viewers = 10 queries/sec against Mongo for up to 2 minutes per analysis.
- Recommendation: Mongo change streams, or a single poller broadcasting to subscribers.

**[Medium] MCP `local_llm_chat` is an ungrounded, uncapped raw prompt passthrough** (Confirmed code / Potential cost abuse)
- Location: `app/mcp/server.py:227-236` — `llm.ainvoke(prompt)` with no token cap, no KB grounding, no rate limit; errors include `str(exc)` (:289)
- Impact: Any connected MCP client can drive unbounded local LLM compute and read internal error strings.
- Recommendation: Cap input length (like search's 500-char guard), require grounding or a use-flag, sanitize errors.

**[Medium] Sync CrossEncoder inference would block the event loop if the reranker is enabled** (Potential — disabled by default)
- Location: `app/retrieval/reranker.py:58` (`model.predict(pairs)` synchronous, called from async graph)
- Recommendation: `asyncio.to_thread` (pattern already used elsewhere).

## Low

**[Low] TavilyClient constructed per search call** (Potential) — `search_service.py:99`; stateless client, module-level singleton suffices.
**[Low] `llama-server --cache-list` appears to be a nonexistent flag** (Potential) — `local_llm.py:595-617`; verify against installed llama-server `--help`.
**[Low] NLI re-sends the full ≤5500-char context per verification call** (Confirmed) — `verifier.py`; per-claim top-3 lexically-relevant chunks (infra exists in sparse_vector.py) would cut verification tokens substantially.
**[Low] Stale docstring claims MiniLM embeddings** (Confirmed, trivial) — `pipeline.py:37`; actual default is `BAAI/bge-small-en-v1.5`.
**[Low] Recovery rewrites re-verify unchanged claims** (Confirmed) — `graph.py:418+`; hash (claims, evidence_ids) and short-circuit — skips 2 LLM calls on many recoveries.

---

## AI/ML Score: 5.5 / 10

**Justification:** Genuinely good engineering: deterministic normalization/hashing instead of LLM (chunker, integrity sha256, sparse vectors, heuristic claim triples), a real 2-call batched NLI verifier with coverage/contradiction thresholds and ABSTAIN discipline, hybrid dense+sparse with RRF, contextual chunk prefixes at zero LLM cost, hardware-aware concurrency semaphore (default 2), config-driven cost controls, lru_cache on model clients, traced recovery loop — that architecture earns ~7 on design.

What drags it down: the flagship efficiency feature (persistent embedding cache) is dead code, every uncached request wastes a duplicate query embedding, the config layer silently ignores models.yaml, no effective prompt caching on the default Ollama path, the verifier is the generator's sibling model (partially theater), web evidence is stamped VERIFIED without verification, and the active rerank heuristic *increases* recovery-loop LLM spend. Well-architected, but its efficiency and independence guarantees are unimplemented or inverted.

## Top 10 load-reduction optimizations (ranked by estimated savings)

1. **Wire `CachedEmbeddingsWrapper`/disk_cache into `get_embedding_model()`** — eliminates 100% of repeat embedding compute (re-uploads, revisions, self-heal). ~5-line change.
2. **Share one query embedding between the semantic-cache check and `dense_search`** (graph.py:703-705) — halves query-embedding compute on every uncached request.
3. **Fix the always-truthy provider defaults in config.py:296-311** — makes every yaml-declared optimization actually reachable; today none of the model routing works.
4. **Cap hybrid web search at `max_results`, not `max_results * 2`** (search_service.py:246) — halves web-grounding tokens and drops one of two concurrent search-engine calls per query.
5. **Stabilize prompt prefixes + leverage Ollama keep_alive KV caching across recovery attempts** — saves ~500 tokens of prefill per repeat; worst case currently re-sends it 5+ times.
6. **Claim-scoped NLI context instead of full ≤5500-char context** (verifier.py) — top-3 lexically-relevant chunks per claim; est. 40-60% token reduction on verification calls (2 of 3 happy-path LLM calls).
7. **Fix reranker sigmoid/threshold and gate the 0.78 heuristic on a score gap** (reranker.py:40-42,70) — fewer premature truncations → fewer ABSTAIN-triggered recovery loops (3-4 LLM calls each).
8. **Skip re-verification of unchanged claims after recovery** (graph.py:418+) — hash (claims, evidence_ids), short-circuit.
9. **Ingestion chunk dedup by `text_hash` + sentence-aligned chunking at ~800-1000 chars** — est. 30-50% fewer embeddings for overlapping corpora; better NLI evidence cohesion.
10. **Numpy-matrix (or Qdrant-backed) semantic cache** — O(500) Python cosine → one dot product; durable/shared cache raises the hit rate of the fast path that today resets on every restart.

**Per-request arithmetic:** happy path today = 3 LLM calls + 2 embeddings; after items 2, 5, 6 → 3 smaller LLM calls + 1 embedding. Worst-case recovery drops from ~11 LLM calls to ~5-7 with items 5-8; repeat ingestion/self-heal approaches zero embedding cost with item 1.
