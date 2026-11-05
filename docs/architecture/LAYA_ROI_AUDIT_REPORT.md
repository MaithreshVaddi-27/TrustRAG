# TRUST RAG — READ-ONLY ENGINEERING & ROI AUDIT: LAYA & ALTERNATIVES

**Date:** 2026-11-05
**Role:** Principal AI Architect + Senior RAG Engineer + Open-Source Technology Evaluator
**Status:** READ-ONLY — No code modifications performed

---

## EXECUTIVE SUMMARY

| Candidate | Verdict | Primary Rationale |
|-----------|---------|-------------------|
| **Laya** | **EXPERIMENT** | Non-autoregressive typed decisions (choice/score/yes-no) in ~33ms could replace LLM-based routing, triage, and guardrails in TrustRAG's LangGraph workflow. Strong LangChain/LangGraph integration. Requires GPU for sub-40ms latency; CPU is 193-464ms. Apache 2.0. Active development. |
| **SetFit** | **SKIP** | Few-shot Sentence Transformer fine-tuning for classification. Not a runtime decision engine. No LangGraph integration. Solves a different problem (training custom classifiers with 8-16 examples). |
| **LLM Guard** | **SKIP** | **ARCHIVED** (no active development since 2026-07-08). Prompt/output scanners for injection, PII, toxicity. TrustRAG already has deterministic router, retrieval outage handling, and LLM ledger. |
| **DeepEval** | **ADOPT** | Comprehensive LLM evaluation framework with RAG-specific metrics (faithfulness, answer relevancy, contextual precision/recall). Directly addresses TrustRAG's Phase 11 evaluation requirements. Apache 2.0. Active. |
| **RAGAS** | **ADOPT** | Purpose-built RAG evaluation (faithfulness, answer relevancy, context precision/recall, entity recall). Aligns with TrustRAG's frozen 25-query baseline dataset and ablation methodology. Apache 2.0. Active. |

**Higher-ROI Priority:** Integrate **DeepEval + RAGAS** for evaluation harness → then **experiment with Laya** for routing/guardrail latency reduction if GPU available.

> **Current follow-up decision:** [`ONNX_GUARDRAIL_OPTIONS_REVIEW.md`](../security/ONNX_GUARDRAIL_OPTIONS_REVIEW.md) reassesses Laya against the repository's torch-free ONNX serving posture and recommends deterministic defenses now, with a measured Prompt Guard pilot only if its evidence gates are met.

---

## 1. TRUSTRAG ACTUAL ARCHITECTURE & VERIFIED GAPS

### 1.1 Core Architecture (from `TRUSTRAG_specs.md` + code exploration)

```
Query → Route (deterministic regex: SIMPLE/TEMPORAL/COMPARISON/COMPLEX)
      → Retrieve (Hybrid: Dense BGE-ONNX 384d + Sparse BM25/Qdrant IDF)
      → Fuse (RRF, k=60, fusion_top_k=20 enforced)
      → Optional Rerank (ONNX CrossEncoder int8, OFF by default)
      → Generate (LLM: llama.cpp/Ollama/MLX default, Gemini cloud optional)
      → Decompose Claims (fused decompose+verify, structured output)
      → Verify Claims (NLI: SUPPORTED/CONTRADICTED/NEUTRAL)
      → Integrity Audit (provenance, temporal, conflicts, suspicious)
      → Diagnose Failure (taxonomy: RETRIEVAL/EVIDENCE/GENERATION)
      → Adaptive Recovery (query_rewrite → re_retrieve → regenerate, max 2 rounds)
      → Re-verify → Grounded Answer / Abstain
```

### 1.2 Key Implementation Details (verified from source)

| Component | Implementation | Config (models.yaml v1.28) |
|-----------|----------------|---------------------------|
| **Embedding** | `BAAI/bge-small-en-v1.5` ONNX Runtime only (torch-free) | `embedding.model`, `onnx_path`, LRU cache 1024 |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` ONNX int8 | `reranker.enabled: true`, `use_onnx: true` |
| **LLM (default)** | llama.cpp `LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M` on :9931 | `llm.provider: llama_cpp` |
| **Verification LLM** | Same as generation LLM (configurable separate) | `verification.provider: llama_cpp` |
| **Retrieval Timeouts** | 45s dense / 45s sparse / 60s hybrid (hard `RetrievalOutageError`) | `retrieval.timeouts` |
| **Recovery Budget** | 2 attempts, 2000 tokens, 180s latency | `recovery.*` |
| **Cost Controls** | Per-analysis LLM call cap (24 for cloud), wall-clock 600s | `cost_controls.*` |
| **Reliability Thresholds** | Coverage ≥0.80, Contradiction ≤0.20, Abstain <0.50 | `reliability.*` |

### 1.3 Verified Gaps (from spec §35 acceptance criteria vs current state)

| Gap | Spec Requirement | Current State |
|-----|------------------|---------------|
| **Evaluation Harness** | Phase 11: frozen 25-query baseline, ablations, experiment UI | `apps/api/tests/eval/` exists but methodology docs show "PENDING operator execution — no measured rows may be invented" |
| **Reranker Validation** | "Evaluation must determine the useful configuration" | Enabled by default but no comparative metrics captured |
| **Recovery Effectiveness** | "Measured improvement over assumed improvement" | Recovery loop implemented but no A/B metrics on recovery success rate |
| **Citation Correctness** | "Does cited evidence actually support the claim?" | NLI verification exists but no citation-level correctness metric |
| **Latency Budgets** | Per-stage observability | SSE traces exist but no automated SLO alerting |

### 1.4 Security Posture (from threat model + code)

- **Prompt Injection**: No dedicated scanner; relies on `RetrievalOutageError` distinction, LLM ledger, and deterministic router (no LLM in routing)
- **PII/Secrets**: No anonymization/deanonymization pipeline
- **Rate Limiting**: JWT auth + per-analysis LLM call budget (cloud tiers only)
- **Supply Chain**: `pip-audit` in CI, pinned dependencies in `pyproject.toml`

---

## 2. LAYA DEEP EVALUATION

### 2.1 What Laya Actually Is

**Laya** = Non-autoregressive "System 1" decision engine (ModernBERT-family encoders) producing **typed decisions** in a single forward pass:

| Decision Type | Output Schema |
|---------------|---------------|
| `choice` | Pick one label from enum + `probabilities` + `prediction_set` (conformal) + `abstain` + `unbound` (OOD) + `route` |
| `score` | Ordinal level (0..N) + expected value + confidence |
| `noul` (yes/no) | P(true) ∈ [0,1] |

**Checkpoints:**
- `laya` (ModernBERT-large, 421M, 512 ctx) — English
- `laya-multilingual` (mmBERT-base, 322M, 1024→8192 ctx) — 100+ languages
- `laya-typed-decisions` (ModernBERT-large, 421M, 1024 ctx) — Fine-tuned for typed workflows

**Router:** Auto-selects checkpoint by script/language/workflow in <1ms (pure Python).

**VegaML (optional):** Frozen 0.8B universal reader (`nandakishorm/vega-U`) behind same API, supports 73K tokens, images, audio, video. Adds conformal prediction sets, abstention, OOD detection, calibrated routing.

### 2.2 Latency & Hardware Reality (from README benchmarks)

| Deployment | `laya-multilingual` (1 question) | `laya` (1 question) | Batch (10 Q) |
|------------|----------------------------------|---------------------|--------------|
| **T4 GPU** | **32.8 ms** | 39.5 ms | 72.3 ms |
| **Apple MPS** | **121 ms** (30 ms/Q) | 146 ms | — |
| **CPU (28 threads)** | 192 ms (48 ms/Q) | 453 ms | 1586 ms |

**Critical for TrustRAG (M2 Mac, 8GB RAM):**
- CPU-only: **193-464 ms per decision** — too slow for inline routing/guardrails in a 600s analysis budget
- MPS (Apple Silicon GPU): **~30-37 ms/Q** — viable for routing/guardrails
- Requires PyTorch + transformers + HF Hub downloads (~2-3 GB checkpoints)

### 2.3 LangChain/LangGraph Integration (from `docs/langchain.md`)

| Node | Purpose | TrustRAG Mapping |
|------|---------|------------------|
| `LayaRouter` | Conditional edge routing (~33ms) | Replace deterministic regex router with learned routing? |
| `LayaGuardrail` | Prompt injection/jailbreak/PII screening (<40ms) | **Gap:** TrustRAG has no dedicated prompt injection scanner |
| `LayaTriage` | Intent/urgency/frustration/churn in one pass | Could enrich `recovery_node` diagnosis |
| `LayaEvaluator` | Rubric-based grading, hallucination eval | **Direct fit for Phase 11 evaluation harness** |
| `LayaDecision` | JSON Schema / Pydantic → typed decisions | Could structure `AgentState` transitions |

**Integration Modes:**
- **Local in-process** (requires PyTorch, GPU for speed)
- **Remote HTTP** (`laya-serve` on separate GPU host) — lightweight clients

### 2.4 Calibration & Reliability (Critical Gap)

- **Shipped uncalibrated**: `laya-multilingual` ships `temperature: [1.0, 1.0, 1.0]`, no `temperature_by_options`
- **English checkpoint** clamp refuses `choice:11+` with warning "treat as uncalibrated"
- **Conformal prediction sets** require `fit()` + `calibrate()` on **your labeled data** (minimum 35 rows, ~50+ for review lines)
- **Threshold gating** (`confidence_threshold`, `fallback`) **must be validated on held-out data** at your option counts
- **README explicitly states**: "Fit and validate the threshold on held-out data at the option counts your workload uses"

### 2.5 Licensing & Maintenance

- **License**: Apache 2.0 ✅
- **Active**: Pushed 2026-11-05, 35K stars, 3.1K forks, 105 open issues
- **Python**: 3.10+, deps: `torch>=2.14`, `transformers>=5.x`, `huggingface_hub>=1.x`
- **ONNX export**: Supported via `laya[onnx]` extra (TileLang GPU fast path via `laya[fast]`)

### 2.6 Integration Points in TrustRAG

| TrustRAG Component | Laya Node | Integration Effort | ROI Potential |
|--------------------|-----------|-------------------|---------------|
| **Query Router** (`router.py`) | `LayaRouter` | Medium (replace regex with learned) | Low-Med: Current router is deterministic, fast, auditable |
| **Prompt Injection Defense** | `LayaGuardrail` | Low (new node in graph) | **High**: Fills verified security gap |
| **Recovery Diagnosis** (`recovery_node`) | `LayaTriage` | Medium (enrich diagnosis_type) | Medium: Could improve strategy selection |
| **Evaluation Harness** (Phase 11) | `LayaEvaluator` | Low (new eval metrics) | **High**: Directly addresses missing evaluation |
| **Structured State Transitions** | `LayaDecision` | Medium (schema-driven graph edges) | Low: Current `AgentState` is already typed |

---

## 3. ALTERNATIVES COMPARISON

### 3.1 SetFit (huggingface/setfit)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Few-shot fine-tuning of Sentence Transformers for classification (8-16 examples/class) |
| **Runtime** | Inference via `SetFitModel.predict()` — standard encoder + classifier head |
| **LangGraph Integration** | None |
| **Prompt Injection** | No |
| **Evaluation** | No |
| **License** | Apache 2.0 |
| **Maintenance** | Active (pushed 2026-11-03) |
| **Verdict** | **SKIP** — Solves training custom classifiers, not runtime decisions. TrustRAG's router is deterministic by design; classification needs (if any) are already served by BGE embeddings + reranker. |

### 3.2 LLM Guard (protectai/llm-guard) ⚠️ ARCHIVED

| Aspect | Detail |
|--------|--------|
| **Status** | **ARCHIVED** — "no longer under active development or maintained" (since 2026-07-08) |
| **Scanners** | 15 input (PromptInjection, Secrets, PII, Toxicity, Code, etc.) + 20 output |
| **LangGraph Integration** | None documented |
| **License** | MIT |
| **Verdict** | **SKIP** — Archived. TrustRAG's deterministic router + retrieval outage handling + LLM ledger already provide defense-in-depth. If prompt injection scanning needed, use active alternative (e.g., `laya.LayaGuardrail` or custom). |

### 3.3 DeepEval (confident-ai/deepeval)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Comprehensive LLM evaluation framework (unit-test style) |
| **RAG Metrics** | Faithfulness, Answer Relevancy, Contextual Precision/Recall, Contextual Relevancy |
| **Other Metrics** | Hallucination, Bias, Toxicity, Summarization, Agentic workflows |
| **LangGraph Integration** | Native `deepeval.integrations.langgraph` |
| **CI/CD** | `deepeval test run` with thresholds, JUnit XML, GitHub Actions |
| **License** | Apache 2.0 |
| **Maintenance** | Very active (pushed 2026-11-05, 19.3K stars) |
| **Verdict** | **ADOPT** — Directly addresses TrustRAG Phase 11 "evaluation harness & frozen dataset" requirement. Can replace custom eval scripts with standardized, CI-integrable metrics. |

### 3.4 RAGAS (vibrantlabsai/ragas)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Purpose-built RAG evaluation (reference-free where possible) |
| **Core Metrics** | Faithfulness, Answer Relevancy, Context Precision, Context Recall, Context Entity Recall |
| **Synthetic Data** | Test set generation from documents |
| **LangGraph Integration** | Via `ragas.integrations.langgraph` |
| **License** | Apache 2.0 |
| **Maintenance** | Active (pushed 2026-02-24, 16.2K stars) — note: repo moved from `explodinggradients` to `vibrantlabsai` |
| **Verdict** | **ADOPT** — Aligns perfectly with TrustRAG's 25-query frozen baseline (`baseline_v1.jsonl`) and ablation methodology (Dense vs Hybrid vs Hybrid+Rerank vs Verified vs Recovery). |

---

## 4. COMPARATIVE ENGINEERING ROI RANKING

| Rank | Candidate | Practical Benefit | Necessity | Implementation Effort | Resource Overhead (M2 8GB) | Maintenance Risk | Net ROI |
|------|-----------|-------------------|-----------|----------------------|---------------------------|------------------|---------|
| 1 | **DeepEval** | **High** — Standardized RAG + LLM metrics, CI/CD ready | **High** — Fills Phase 11 gap | Low — `pip install deepeval`, add test file | Low (eval-time only, no runtime) | Low (active, Apache 2.0) | ⭐⭐⭐⭐⭐ |
| 2 | **RAGAS** | **High** — RAG-specific metrics, synthetic test gen | **High** — Complements DeepEval | Low — `pip install ragas`, integrate with eval dataset | Low (eval-time only) | Low (active, Apache 2.0) | ⭐⭐⭐⭐⭐ |
| 3 | **Laya (Guardrail/Evaluator)** | **Medium-High** — Sub-40ms injection screening + rubric eval | **Medium** — Security gap + eval gap | Medium — Requires GPU for latency claims; CPU 200-400ms | **High** — 2-3GB VRAM/RAM, PyTorch stack | Medium (active but calibration burden on you) | ⭐⭐⭐ |
| 4 | **Laya (Router/Triage)** | Low-Medium — Learned routing vs deterministic | Low — Current router works, auditable | Medium — Schema design, calibration, validation | High (same as above) | Medium | ⭐⭐ |
| 5 | **SetFit** | None for TrustRAG | None | N/A | N/A | N/A | ⭐ |
| 6 | **LLM Guard** | None (archived) | None | N/A | N/A | **High (unmaintained)** | ⭐ |

---

## 5. VERDICT PER CANDIDATE

### ✅ ADOPT — DeepEval
**Reason:** Directly implements TrustRAG Phase 11 acceptance criteria (evaluation harness, frozen dataset, ablations, experiment UI). Provides:
- `FaithfulnessMetric` — claim support verification (aligns with NLI verification)
- `AnswerRelevancyMetric` — answer quality
- `ContextualPrecisionMetric` / `ContextualRecallMetric` — retrieval quality
- `HallucinationMetric` — unsupported claim detection
- CI/CD integration with thresholds (`deepeval test run --threshold 0.7`)

**Integration:** Add `apps/api/tests/eval/deepeval_integration.py`, wire into `scripts/run_baseline_eval.py`, configure GitHub Action.

### ✅ ADOPT — RAGAS
**Reason:** Complementary RAG-specific metrics (Context Entity Recall, reference-free Faithfulness). Synthetic test generation from KBs aligns with TrustRAG's document ingestion pipeline.

**Integration:** Same eval harness as DeepEval; run both for cross-validation.

### 🧪 EXPERIMENT — Laya (Guardrail + Evaluator nodes only)
**Reason:**
- **Guardrail**: Fills verified prompt injection / PII gap with ~33ms latency (GPU) — but **CPU is 200-400ms**, which adds meaningful latency to TrustRAG's 60s hybrid retrieval budget.
- **Evaluator**: Rubric-based grading could augment DeepEval/RAGAS for custom criteria.
- **Calibration burden**: You must `fit()` + `calibrate()` on your labeled data (minimum 35 rows per question, 50+ for review lines). Shipped checkpoints are **uncalibrated**.
- **GPU requirement**: Sub-40ms claims require T4/MPS/CUDA. On M2 8GB CPU-only, latency is 5-10x higher.

**Experiment Scope:**
1. `pip install "laya[langgraph]"`
2. Add `LayaGuardrail(action="annotate")` as first node in `build_agent_graph()` (before retrieval)
3. Add `LayaEvaluator` to evaluation harness for custom rubrics
4. Benchmark on M2 Mac (CPU + MPS) vs current latency budget
5. **Gate**: Only adopt if MPS latency <50ms and calibration achieves >0.9 precision on your labeled data

### ❌ SKIP — Laya (Router / Triage / Decision)
**Reason:**
- TrustRAG's deterministic regex router is **fast (<1ms), auditable, requires no calibration, handles 4 routes cleanly**. Learned routing adds calibration burden, OOD risk, and opacity for marginal gain.
- `LayaTriage` enriches diagnosis but TrustRAG's `DiagnosisType` taxonomy (7 types) is already structured and mapped to recovery strategies.
- `LayaDecision` duplicates Pydantic `AgentState` validation.

### ❌ SKIP — SetFit
**Reason:** Wrong problem. SetFit = training custom classifiers with few shots. TrustRAG needs runtime decisions, not classifier training.

### ❌ SKIP — LLM Guard
**Reason:** **Archived, unmaintained**. Security tooling must be actively maintained. TrustRAG's existing defenses (deterministic router, retrieval outage distinction, LLM ledger, JWT auth) are production-appropriate.

---

## 6. EXACT INTEGRATION POINTS (If Experimenting with Laya)

### 6.1 Guardrail Node Insertion Point
```python
# apps/api/app/rag/agent/graph.py - build_agent_graph()
builder = StateGraph(AgentState)

# NEW: Guardrail as first node (before retrieval)
builder.add_node("guardrail", LayaGuardrail(action="annotate", state_key="query"))
builder.set_entry_point("guardrail")
builder.add_edge("guardrail", "retrieval")

# Existing nodes unchanged
builder.add_node("retrieval", retrieval_node)
# ...
```

### 6.2 Evaluator in Evaluation Harness
```python
# apps/api/tests/eval/laya_evaluator.py
from laya.integrations.langchain import LayaEvaluator

evaluator = LayaEvaluator(
    rubric={
        "factual_accuracy": "Is the answer factually correct based on evidence?",
        "citation_correctness": "Do citations actually support the claims?",
        "completeness": "Does the answer address all parts of the query?",
    },
    state_key="analysis_detail"  # Full trace + answer + claims
)
```

### 6.3 Remote Mode for M2 8GB (Recommended)
```python
# Deploy laya-serve on GPU host (separate machine/colab)
# TrustRAG M2 Mac connects via HTTP — no PyTorch/GPU RAM locally
router = LayaRouter(
    base_url="http://gpu-host:8000",
    api_key="...",
    criteria={...}  # Your guardrail/evaluator criteria
)
```

---

## 7. HIGHER-ROI IMPROVEMENTS TO PRIORITIZE INSTEAD

| Priority | Improvement | Spec Reference | Effort | Impact |
|----------|-------------|----------------|--------|--------|
| **P0** | **Complete Phase 11 Evaluation Harness** — Wire DeepEval + RAGAS to frozen 25-query baseline, capture ablation metrics (Dense vs Hybrid vs +Rerank vs +Verification vs +Recovery) | §25, §35-21 | 2-3 days | **Measured quality signal** — replaces "PENDING operator execution" |
| **P0** | **Reranker A/B Validation** — Measure recall@k / latency tradeoff with `reranker.enabled: true/false` on baseline queries | §10, §35-12 | 1 day | **Data-driven config** — currently enabled by default without evidence |
| **P1** | **Recovery Effectiveness Metrics** — Track `recovery_success_rate`, `recovery_strategy_distribution`, `post_recovery_reliability_delta` in MongoDB | §17, §26 | 1 day | **Validates primary differentiator** |
| **P1** | **Citation Correctness Metric** — NLI verification already produces `supporting_segments`; aggregate into per-analysis citation precision | §14, §35-10 | 1 day | **Closes "citation ≠ support" gap** |
| **P2** | **Prompt Injection Test Suite** — Add adversarial prompts to security tests (§27.4) using existing `test_redteam.py` patterns | §21, §32 | 0.5 day | **Verifies defense-in-depth** |
| **P2** | **SLO Alerting** — Prometheus rules for `retrieval_latency_p95 > 45s`, `recovery_rounds > 2`, `abstain_rate > threshold` | §26, §35-16 | 1 day | **Production observability** |
| **P3** | **Context Compression Evaluation** — Benchmark `context_compression_enabled: true` vs false on long-context KBs (currently off by default per audit B-7) | `optimization.context_compression_*` | 1 day | **Cost/latency optimization** |

---

## 8. FINAL RECOMMENDATION SEQUENCE

```
Week 1:  ADOPT DeepEval + RAGAS → Complete Phase 11 evaluation harness
Week 2:  RUN baseline ablations → Capture measured metrics for all 5 configurations
Week 3:  PRIORITIZE P0/P1 improvements above based on actual data
Week 4:  EXPERIMENT Laya Guardrail (remote/MPS) → Benchmark latency + calibration on your attack corpus
         → ADOPT only if: (a) MPS <50ms, (b) calibrated precision >0.9, (c) integrates cleanly
         → Otherwise SKIP and rely on deterministic router + retrieval outage handling
```

**Bottom Line:** TrustRAG's architecture is already production-coherent. The highest ROI is **measurement infrastructure (DeepEval/RAGAS)** to validate what you've built, not adding new runtime dependencies. Laya's guardrail/evaluator are worth a **time-boxed experiment** only if you have GPU capacity for the latency claims and labeled data for calibration.

---

*Report generated from read-only inspection of TrustRAG source (`apps/api/`, `docs/TRUSTRAG_specs.md`, `models.yaml`), Laya GitHub repo + docs, and public metadata for SetFit, LLM Guard, DeepEval, RAGAS. No code was modified.*