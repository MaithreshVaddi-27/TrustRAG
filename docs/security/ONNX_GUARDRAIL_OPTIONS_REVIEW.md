# TrustRAG Guardrail Options — Engineering Decision Review

**Date:** 2026-11-05
**Scope:** prompt-injection screening for the FastAPI/LangGraph RAG path
**Decision status:** no runtime integration approved without a measured pilot

## Executive decision

**Do not add Laya or another runtime guardrail model to TrustRAG production now.**

The best production-suitable option is the existing **deterministic, defense-in-depth path**, strengthened and measured through the existing red-team and evaluation suites:

1. Treat retrieved evidence as untrusted data using the existing prompt fence.
2. Keep retrieval and query routing deterministic and local.
3. Reject/abstain when verification cannot ground claims.
4. Keep the grounding gate from displaying unverified generated prose.
5. Expand and run the existing adversarial test corpus before selecting a learned classifier.

This is the only option that is currently compatible with the repository's deliberate ONNX-only, torch-free serving posture, no-new-service default, deterministic fallback requirement, and M2/8 GB resource target.

A learned classifier can be useful later, but only as an **annotate-only, opt-in pilot** with a pinned artifact and measured false-positive/false-negative rates.

## Confirmed project constraints

| Constraint | Evidence | Engineering consequence |
|---|---|---|
| Production runtime is intentionally torch-free | `apps/api/pyproject.toml` uses ONNX Runtime for embeddings/reranking and comments explicitly preserve a torch-free runtime | Do not add a PyTorch guardrail dependency to the API process. |
| ONNX sessions already have a shared RAM-safe factory | `apps/api/app/llm/onnx_runtime.py` uses capped threads, sequential execution, and configurable memory arenas | Any future classifier must reuse this factory rather than create another inference configuration. |
| Existing RAG security controls are real enforcement points | `apps/api/app/rag/generation/generator.py`, `graph.py`, and `tests/test_redteam.py` provide untrusted-data fencing, no tool execution, NLI verification, grounding gates, abstention, and outage distinction | A classifier must complement these controls, never replace them. |
| Retrieved content can be long | Prompt Guard 86M documents a 512-token context window | Classifier scanning would require bounded per-query/per-chunk processing and a defined aggregation policy. |
| No fresh authenticated baseline or labeled guardrail corpus is available | Evaluation work is blocked on operator-provided live stack credentials/fixture KB; existing red-team tests are behavioral, not a calibrated labeled corpus | No defensible block/allow threshold can be selected now. |

## Options assessed

### 1. Existing deterministic controls + evaluation expansion — **recommended now**

**What it is**

Use the controls already in TrustRAG: prompt fencing of untrusted evidence, deterministic routing, no implicit tool execution from retrieved text, claim verification, grounding gate, and abstention. Expand `tests/test_redteam.py` with representative attack categories and validate them alongside the existing evaluation harness.

**Why it wins now**

- No additional model, dependency, artifact download, network endpoint, license workflow, or calibration process.
- Deterministic behavior is auditable and remains available during model/server faults.
- It protects the actual trust boundaries already exercised in the pipeline.
- It aligns with the current ONNX-first resource budget.

**Limit**

It is defense in depth, not a statistical injection classifier. It must be validated with adversarial behavioral tests and real evaluation data.

**Decision:** production default.

### 2. Meta Prompt Guard / Prompt Guard 2 — **best future classifier pilot**

**What it is**

Prompt Guard 86M is a dedicated text classifier for benign, prompt-injection, and jailbreak categories. Its documented intended use includes screening user dialogue and untrusted third-party content such as tool/web outputs.

**Strengths**

- Directly addresses prompt injection rather than general safety judging.
- Far smaller than 8B/12B generative safety judges.
- Purpose aligns with scanning both user input and retrieved evidence.
- Prompt Guard 2 is documented by Meta as the newer preferred generation for most uses.

**Blocking concerns**

- Meta model access is gated; the project must complete its license/access process before model acquisition.
- Prompt Guard 86M is under the Llama 3.1 Community License, not Apache-2.0.
- Public documentation retrieved for Prompt Guard 2 does not establish a supported ONNX artifact or ONNX Runtime deployment path.
- Prompt Guard 86M has a 512-token context window, requiring a measured chunking/aggregation policy.
- The application must establish a labeled held-out corpus before any threshold alters analysis flow.

**Safe pilot shape**

- Run out of process or offline first; do not add PyTorch to API serving.
- Start annotate-only: persist a trace annotation, but do not block, rewrite, or change retrieval.
- Pin the exact model revision and checksum.
- Test input queries and retrieved chunks independently; never scan system prompts.
- Compare detector results with manually labeled red-team and benign examples.
- Promote only if it improves detection without unacceptable false positives or latency.

**Decision:** top future experiment, not a current integration.

### 3. Protect AI DeBERTa-v3-base Prompt Injection v2 — **not recommended**

**What it is**

A roughly 0.2B English binary prompt-injection classifier with documented ONNX assets and Apache-2.0 licensing.

**Strengths**

- Closest technical fit for TrustRAG's existing ONNX Runtime architecture.
- Documented ONNX assets avoid adding PyTorch to the serving process.
- Smaller than LLM judges and simple binary output.

**Why it is rejected**

- The model/project is archived and no longer actively maintained.
- It is English-only and does not cover jailbreak detection as its main use case.
- A security control that will process evolving adversarial inputs needs an active maintenance and response posture.

**Decision:** do not adopt in production. It may only be used as a short-lived offline baseline comparator against a maintained candidate.

### 4. Laya Guardrail / Laya ONNX — **defer**

**What it is**

A general typed-decision engine with LangGraph integration. The guardrail supports raise, filter, and annotate actions; remote mode can avoid local PyTorch/checkpoint downloads.

**Strengths**

- First-class LangGraph integration.
- Supports annotate mode and remote operation.
- Potentially useful for richer classification/routing work.

**Why it is not the best fit**

- It is a general decision engine, not the smallest specialized prompt-injection control.
- Safe blocking requires calibration on a labeled target corpus and a held-out validation set.
- No Laya artifact, serving endpoint, calibration set, or benchmark exists in this deployment.
- Remote mode adds availability, credential, data-egress, and latency trust boundaries.
- Local operation conflicts with the project’s torch-free constrained-host posture unless an independently verified ONNX artifact is used.

**Decision:** defer until a Prompt Guard-style pilot and baseline measurements establish a need that deterministic defenses cannot cover.

### 5. IBM Granite Guardian 3.3 8B — **offline/remote evaluator only**

**What it is**

An Apache-2.0 judge model that can score jailbreak and RAG-quality criteria.

**Why it is not an inline guardrail**

- 8B BF16 deployment is unsuitable for the local M2/8 GB low-latency API posture.
- It is a judge model, not a compact deterministic classifier.
- Remote use creates the same network and data-boundary concerns as remote Laya.

**Decision:** possible later evaluator for offline, controlled quality review—not a retrieval-path guardrail.

### 6. Meta Llama Guard 4 12B — **reject for this use**

**Why rejected**

- 12B multimodal safety model requires GPU-oriented deployment.
- Its own model documentation points to Prompt Guard 2 for prompt-attack detection.
- It is gated under the Llama 4 Community License.

**Decision:** not suitable for TrustRAG's constrained local RAG path.

## Ranking

| Rank | Candidate | Production fit now | Reason |
|---|---|---:|---|
| 1 | Existing deterministic controls + red-team/eval expansion | High | Already deployed, auditable, no added runtime, deterministic fallback. |
| 2 | Prompt Guard 2 / 86M annotate-only pilot | Medium, conditional | Most direct specialized classifier, but gated and ONNX support/quality must be proven. |
| 3 | Granite Guardian remote evaluator | Low inline / medium offline | Useful offline judge, but too heavy for local synchronous serving. |
| 4 | Laya guardrail | Low | Broader than needed; calibration and runtime/endpoint burden remain unproven. |
| 5 | Protect AI DeBERTa v2 ONNX | Low | Technically compatible but archived; unsuitable as a maintained security dependency. |
| 6 | Llama Guard 4 12B | Low | Too large and not the primary prompt-attack tool. |

## Required evidence before any learned guardrail changes behavior

Do not enable block/filter/abstain behavior until all gates pass:

1. **Artifact:** exact model revision, license acceptance, checksum, source URL, and reproducible load test are recorded.
2. **Runtime:** a bounded inference deployment fits the target memory and latency budget without introducing PyTorch into the API runtime.
3. **Corpus:** a labeled corpus includes benign user queries, direct jailbreaks, indirect injection in retrieved documents, encoded/obfuscated attacks, tool-call bait, and multilingual cases if the product accepts them.
4. **Metrics:** held-out precision, recall, false-positive rate, p95 latency, memory impact, and failure behavior are reported. No scores may be fabricated.
5. **Fallback:** inference timeout, artifact failure, or remote endpoint failure must preserve existing deterministic behavior and must never silently allow a new unsafe mode.
6. **Rollout:** annotate-only first; compare results against human labels; then a narrow opt-in policy if the gate is passed.

## Recommended next action

Do not start another model integration. Complete the current evaluation prerequisites and test coverage first. Then run a bounded Prompt Guard pilot outside the production request path and decide from measured evidence whether an ONNX artifact and annotate-only adapter are justified.

## Sources

- [TrustRAG shared ONNX Runtime session factory](../apps/api/app/llm/onnx_runtime.py)
- [TrustRAG red-team tests](../apps/api/tests/test_redteam.py)
- [Meta Prompt Guard 86M model card](https://huggingface.co/meta-llama/Prompt-Guard-86M)
- [Meta Purple Llama Prompt Guard repository](https://github.com/meta-llama/PurpleLlama/tree/main/Prompt-Guard)
- [Protect AI DeBERTa Prompt Injection v2 model card](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)
- [Laya LangGraph integration documentation](https://github.com/nandhakishorm/laya/blob/main/docs/langchain.md)
- [IBM Granite Guardian 3.3 8B model card](https://huggingface.co/ibm-granite/granite-guardian-3.3-8b)
- [Meta Llama Guard 4 12B model card](https://huggingface.co/meta-llama/Llama-Guard-4-12B)
- [NVIDIA NeMo Guardrails repository](https://github.com/NVIDIA-NeMo/Guardrails)
