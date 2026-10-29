# TrustRAG — RAG & Agentic Workflow Audit & Fix Summary

**Date:** 2026-10-29
**Role:** Senior RAG & Agent Engineer
**Scope:** Full backend RAG/agent path — retrieval → generation → claim decomposition → NLI verification → recovery → verdict persistence → response presentation, plus backend bugs found during the audit.

## Symptom investigated

> "Claim verification is not happening as expected — even when a claim is related to the query it is marked `NEUTRAL`."

`NEUTRAL` is the correct *uncertainty* label when evidence is genuinely insufficient; it is **not** a finding that the claim is false. A related claim marked `NEUTRAL` means the verifier could not ground it in the served evidence. Root causes are therefore in **evidence quality delivered to NLI** (retrieval/reranker) and **NLI-call resilience**, not in the verdict math itself.

## Findings & fixes applied in this session

### 1. FIXED — Reranker early termination padded unscored candidates with `0.0`
**File:** `apps/api/app/rag/retrieval/reranker.py` (`_rerank_sync`)

When the cross-encoder early-termination fired (confident top result + score gap), candidates not yet scored were assigned a fabricated `0.0`, sorted into the ranked list, and could appear in the top context slice ahead of genuinely-scored (including negatively-scored) chunks. That displaced real evidence from the generation/verification context window, so NLI saw incomplete evidence and returned `NEUTRAL` for supported claims.

**Fix:** track which candidates actually received a score (`scored_mask`). Rank scored candidates first (by score desc), then unscored. Unscored candidates never outrank a scored chunk, so early termination cannot evict real evidence from the head of the context window. Only scored candidates receive `rerank_score` (no fake `0.0`).

**Regression test:** `tests/test_reranker.py::test_rerank_early_termination_excludes_unscored_from_head` — verifies early-termination runs only one batch, the head contains only scored candidates, and unscored chunks never appear in the top slice.

### 2. CONFIRMED ALREADY FIXED (in working tree, pre-10-29 audit) — verification node no longer reports `PASS` on timeout/error
**File:** `apps/api/app/rag/agent/graph.py` (`verification_node`)

Previously, when NLI verification timed out or raised at the recovery-attempt limit, the error branch set `verdict_status = "PASS"`, letting a run with no completed verification look successful. Both timeout and exception paths now remain `FAIL`, independent of retry count. Coverage added in `tests/test_agent.py`.

### 3. CONFIRMED ALREADY FIXED — missing Qdrant collection no longer bypasses Mongo self-heal
**File:** `apps/api/app/rag/retrieval/retriever.py` (`dense_search`, `sparse_search`)

Dense and sparse retrieval now treat only Qdrant's typed HTTP 404 (`UnexpectedResponse`, status 404) as an empty/missing-index result; other Qdrant errors remain outages. This lets the existing agent self-heal inspect Mongo chunks, initialize the missing collection, and rebuild vectors. Coverage added in `tests/test_retrieval.py`.

### 4. CONFIRMED ALREADY FIXED — structured-output rescue for malformed small-model NLI JSON
**File:** `apps/api/app/llm/llm_utils.py` (`_rescue_schema_from_text`, wired into `build_structured_output_runnable`)

Small (≤3B) local models routinely emit truncated or free-form NLI output, which previously became a `ValidationError` → every claim `NEUTRAL`. The structured-output runnable now rescues verdict/batch/decomposition schemas from free-form text (verdict aliasing, segment extraction, claim list parsing) before re-raising. This is the main reason related claims stop being false-`NEUTRAL` on small local models.

### 5. CONFIRMED ALREADY FIXED — citation regex accepts `[N]` and `[Segment N]`
**File:** `apps/api/app/rag/generation/generator.py` (`_CITATION_RE`)

Small models emit `[2]`; the extractor now accepts both `[2]` and `[Segment 2]`, so inline citations link claims to evidence instead of being silently dropped.

### 6. CONFIRMED ALREADY FIXED — `models.yaml` tier/topology corrections
- `sparse_top_k: 0 → 20` (hybrid sparse leg was dead; exact identifiers/dates/part numbers were missed by dense-only retrieval).
- `max_analysis_seconds: 120 → 600` (recovery loop was unreachable inside one LLM timeout).
- `ocr.dpi: 200 → 300` (OCR accuracy floor).
- `retrieval.quantization.enabled: false` (INT8 gated off until recall measured).
- `fused_decompose_verify: true` (fast path; auto-falls back to two-step).
- `max_output_tokens: 1024 → 512` (grounded-answer cap).
- `max_individual_nli_fallback` floored at 8 so every claim is individually tried when batch NLI fails.

## Backend bugs found & fixed in this session (beyond the claim→NEUTRAL path)

| # | File | Bug | Fix |
|---|------|-----|-----|
| B-1 | `reranker.py` | Early termination fabricated `0.0` scores for unscored candidates | Score-only tracking; scored-first ranking (see #1 above) |
| B-2 | `llm_utils.py` | `E501` line-too-long in structured-output repair block | Wrapped long lines (lint-clean now) |

## Root-cause verdict on the reported `NEUTRAL` symptom

The `NEUTRAL` marking for query-related claims is **not a single logic bug**. It is the compounded result of:

1. **Retrieval quality** — sparse leg was off (`sparse_top_k: 0`), so rare identifiers/dates never reached NLI. Fixed in working tree (#6).
2. **Reranker eviction of evidence** — early termination padded `0.0` and could evict scored chunks from context. Fixed (#1).
3. **Small-model NLI fragility** — ≤3B models emit unparseable verdict JSON, cascading to `NEUTRAL`. Mitigated by rescue + batch-retry + per-claim individual fallback (#4).
4. **Conservative-by-design default** — when batch NLI fails and the per-claim fallback budget is spent, remaining claims intentionally stay `NEUTRAL` (never inflate trust). This is correct behavior; tune `cost_controls.max_individual_nli_fallback` / `max_claim_retrievals` if you need more attempts.

**There is no code path that intentionally converts `SUPPORTED` → `NEUTRAL`.** `NEUTRAL` arises only when (a) the NLI model cannot find support in the served context, or (b) the NLI call failed/timed out and no retry budget remains.

## Verification performed

- Backend suite: `705 passed, 3 failed, 1 skipped`, coverage `78.40%` (≥ 78% minimum).
- The 3 failures are pre-existing environment issues in `tests/test_search_mcp.py` (`ModuleNotFoundError: tavily`) — Tavily is a cloud extra not installed by default; unrelated to RAG/agent.
- `ruff check app/ tests/` — **all checks passed**.
- `ruff format --check` on all changed files — clean (2 pre-existing unformatted files in `verifier.py`/`test_verification.py` are out of scope — they were uncommitted working-tree changes before this session).

## Manual end-to-end test (per README)

Not run in this session: it requires Ollama/llama.cpp/MLX, MongoDB 7, Qdrant, and ONNX model weights fetched via `scripts/bootstrap.py`. Per the README:

```bash
cd TrustRAG
cp .env.example .env   # set JWT_SECRET
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,local-models]"
python ../../scripts/bootstrap.py   # fetch ONNX weights
# Terminal: start MongoDB + Ollama (ollama pull gemma3:1b) + ./scripts/start_local_llm.sh
uvicorn app.main:app --reload --port 8000
# Terminal: cd apps/web && npm install && npm run dev   (http://localhost:5173)
curl http://localhost:8000/api/v1/health   # → {"status":"ok"}
```

Efficiency note: the default stack is fully local (no API keys). Use `LLM_PROVIDER=llama_cpp` + `LFM2.5-1.2B` (≤3B lean tier) for the fastest local loop; prefer `gemini` only with `GEMINI_API_KEY` set (cloud tier). Verification time is dominated by local LLM latency, not code.

## Recommended next steps (out of scope for this session)

1. Run a labeled evaluation set (≥200 claim/evidence pairs: supported, contradicted, absent) against the real corpus/model to measure `SUPPORTED` precision before tuning `minimum_evidence_coverage` / `maximum_contradiction_rate` (currently 0.80 / 0.20 — engineering defaults, not calibrated probabilities).
2. Consider enabling `fused_decompose_verify` for capable models (already `true` in yaml; skipped for ≤3B in code) to cut a verification round-trip.
3. If `NEUTRAL` rate stays high on small models, raise `cost_controls.max_individual_nli_fallback` and/or `max_claim_retrievals` (currently 8 / 3).
4. Format the 2 pre-existing unformatted files (`verifier.py`, `test_verification.py`) if enforcing the full `ruff format --check` gate.
