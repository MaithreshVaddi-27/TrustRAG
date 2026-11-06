# Reliability Phase 1 — Gemma + CRAFT Abstention Audit

**Date:** 2026-11-06
**Author:** Senior RAG Engineer / Software Architect (read-only investigation; no code, config, model, or dataset change was made)
**Subject:** the six Gemma 3 1B + CRAFT abstentions on the frozen 27-query baseline — `q003`, `q006`, `q016`, `q017`, `q022`, `q024`
**Baseline under audit:** Experiment 1 (`gemma3:1b`, `config_version 1.28`), KB `6aec8b8514772d6c3cc8c597`
**Status:** findings + proposed fixes only. **Implementation is deliberately NOT started — awaiting approval.**

---

## 1. Executive summary

| # | Finding | Evidence | Severity |
|---|---|---|---|
| 1 | **`q022` and `q024` abstained because their claims were never verified, not because the evidence was insufficient.** Every one of the 12 claims behind those two abstentions carries the stored explanation *"Verification skipped: batch NLI unavailable and the per-claim fallback budget is exhausted."* | MongoDB `claims` collection + `trace_events` (§4); reproduction in RC-1/RC-2 | **Critical — false abstention with a false diagnosis** |
| 2 | **The previous audit's root cause for `q022`/`q024` is factually wrong.** `POST_IMPLEMENTATION_QUALITY_AUDIT_2026-11-05.md` §1.2 attributes the abstention to "CRAFT contrastive negative grounding caused … to fail NLI verification (`NEUTRAL`)". The NLI call never ran. | `claims.explanation` text; trace has no NLI verdict for those rounds | **Critical — documentation must be corrected** |
| 3 | **`q003` and `q006` are generator-side refusals** (gold chunk served rank 1 in all 3 retrieval rounds), and **`q006` is a dataset label defect**: the corpus states no contact person, and three different models abstain on it. | traces + 3-model comparison (§4) | High |
| 4 | **Batch NLI structured output fails deterministically for `gemma3:1b`** (8/8 reproductions) with a key typo (`vericits`) plus template placeholders; the JSON-repair alias list does not cover it. | live reproduction (RC-2) | **Critical — chronic, model-wide** |
| 5 | **The grounding gate has no answer-responsiveness check.** 3 of 20 delivered answers in Exp 1 are grounded but answer the *wrong* fact, and were served as `TRUSTED`. Answer coverage 17/20 = **0.8500** (17/24 = **0.7083** over answerable queries). | keyword audit against the frozen dataset (§6) | **Critical — unsupported answers reach the user as trusted** |
| 6 | **"Citation correctness 1.0000" is a range check, not a support check.** Real semantic citation quality is **12/21 = 0.5714**; 9 cited clauses point at a segment that does not contain them. | §6, RC-4 | High |
| 7 | **Recovery query rewrites accept junk** (`"xml query: deletion time"`, `"Expand: …"`) and burn rounds. | traces + unit-level check (RC-5) | Medium |
| 8 | **Three pre-existing test failures**, all test-side staleness, none a production regression. | §8 | Medium |
| 9 | **The eval harness measures no false-abstention rate, no answer coverage, no verification-availability signal, and no semantic citation quality.** | §6 | Medium |

**Bottom line:** the six abstentions split into **2 genuine false abstentions (`q003`, `q024`)**, **1 dataset label defect (`q006`)**, **1 correct outcome from a defective mechanism (`q022`)**, and **2 correct abstentions (`q016`, `q017`)**. The single defect that most damages reliability is **RC-1**: a failed structured-output call is silently converted into "the evidence was insufficient", which both fabricates abstentions and corrupts the LOW_COVERAGE diagnosis the whole trust story rests on.

---

## 2. Investigation method and evidence provenance

### 2.1 What was inspected
- Git state, architecture docs, `docs/evaluation/*`, `docs/architecture/MULTI_MODEL_ARCHITECTURE_REVIEW_2026-11-05.md`, `README`, specs.
- Full backend pipeline source: `apps/api/app/rag/agent/graph.py`, `retrieval/retriever.py`, `retrieval/reranker.py`, `generation/generator.py`, `verification/verifier.py`, `verification/verdict.py`, `services/analysis_service.py`, `llm/llm_utils.py`, `llm/local_llm.py`, `llm/llm_ledger.py`.
- Eval harness `scripts/run_baseline_eval.py`, `apps/api/tests/eval/metrics.py`.
- The preserved run artifacts in `docs/evaluation/results/` (llama_cpp, mlx).
- **The live MongoDB record of the actual Exp 1 / Phase 0 / Exp 2 / Exp 3 runs** (`trustrag_db`), which still contained every analysis, claim, evidence record, recovery run and trace event.
- A live reproduction of the verification path against the locally installed `gemma3:1b` (Ollama) using the frozen fixture corpus.

### 2.2 Provenance and its limits
- The four raw experiment JSON artifacts cited in the previous audit (`/tmp/trustrag-model-experiments/exp*.json`, `/tmp/trustrag-phase0/*`) **no longer exist** (tmp cleaned). All per-query numbers below therefore come from the **database record**, which is strictly better: it holds claim texts, claim explanations, evidence linkage, recovery strategies and full traces.
- **Code-version caveat:** the eval run executed 2026-11-05 15:07–15:13 UTC, while `apps/api/app/rag/agent/graph.py` was last committed at 22:24 IST (16:54 UTC) the same day. The running build therefore predates HEAD for `graph.py`. Where the recorded trace contradicts current-code behaviour (RC-5) this is stated explicitly.
- No file was modified. Services started for the investigation (`mongod` on the existing data dir, `ollama serve`) were stopped afterwards; no model, dependency, or configuration was installed or changed.

---

## 3. Environment state at start

| Item | State |
|---|---|
| Branch | `ui-redesign`, up to date with `origin/ui-redesign` |
| Uncommitted | `apps/api/tests/eval/metrics.py` + `tests/eval/test_eval_metrics.py` — the abstained-claims-scoring fix from the previous session (left in place, reviewed, agreed: correct but ineffective, see RC-1) |
| Untracked | `docs/evaluation/POST_IMPLEMENTATION_QUALITY_AUDIT_2026-11-05.md` |
| Test suite | **3 failed, 731 passed** in 34.66 s (failures are test-side staleness — §8) |
| Frozen baseline | `baseline_v1.jsonl` unchanged (27 queries: 14 factual, 3 temporal, 3 conflicting, 2 missing_evidence, 5 adversarial) |
| Production config | `gemma3:1b` + CRAFT, reranker disabled, `config_version 1.29` — **unchanged** |
| Live services | none running at start (API, Qdrant, Ollama, MongoDB all down) |

---

## 4. The six abstentions, traced end to end

All figures below are read from the Exp 1 analyses (`llm_model=gemma3:1b`, `2026-11-05 15:05–15:16 UTC`).

### 4.1 Per-query outcome table

| Query | Expected | Actual | Reliability | Diagnosis | Claims | Recovery rounds |
|---|---|---|---|---|---|---|
| `q003` token revocation speed | completed | **abstained** | ABSTAINED (0.0) | RETRIEVAL_FAILURE | 0 | query_rewrite → re_retrieve |
| `q006` deletion contact | completed | **abstained** | ABSTAINED (0.0) | RETRIEVAL_FAILURE | 0 | query_rewrite → re_retrieve |
| `q016` contractor parental leave | abstained | abstained ✔ | ABSTAINED (0.0) | RETRIEVAL_FAILURE | 0 | regenerate (skipped) → re_retrieve |
| `q017` organisation founder | abstained | abstained ✔ | ABSTAINED (0.0) | RETRIEVAL_FAILURE | 0 | query_rewrite → re_retrieve |
| `q022` garbled query | abstained | abstained ✔ | **FAILED (0.0)** | **LOW_COVERAGE** "Only 0/5 claims supported" | 10 NEUTRAL (never verified) | query_rewrite → regenerate |
| `q024` deletion duration | completed | **abstained** | **FAILED (0.0)** | **LOW_COVERAGE** "Only 0/1 claims supported" | 2 NEUTRAL (never verified) | query_rewrite → re_retrieve |

### 4.2 Retrieval → prompting → generation → NLI → grounding → abstention

**`q003` "How quickly does token revocation take effect?"**
```
R1 retrieval: 4 segments — Segment 1 service-api.md (score 0.0328, rank 1 in both legs)
              "Token revocation takes effect within 60 seconds of the revoke call."
R1 generation: 2491 ms → refusal → is_refusal_answer gate (graph.py:964-990) → 0 claims,
              diagnosis RETRIEVAL_FAILURE, verdict FAIL
R2 (query_rewrite): rewritten = "Expand: How quickly does token revocation take effect?"
              → retrieval returns the SAME 4 segments (service-api.md still rank 1)
R2 generation: 1491 ms → refusal again
R3 (re_retrieve, top_k=21): same 4 segments; generation 137 ms → refusal
Final: verdict PASS-on-refusal (compute_verdict total==0 + is_refusal_answer → ABSTAINED),
       stored _UNVERIFIED_ANSWER, status "abstained", answer_cited = None
```
**Root cause:** the gold evidence was retrieved and served in every round; the 1B model refused. The refusal path is deterministic and correct *for genuinely missing evidence*, but here it fires on a rank-1, exactly-matching chunk. Cross-model control: the same query **completed (TRUSTED)** under `qwen3:1.7b` (15:26 UTC), under `LiquidAI/LFM2.5-1.2B` (llama_cpp run), and under `mlx-community/Qwen3-4B`.

**`q006` "Who must be contacted to complete a deletion request?"**
```
R1: Segment 1 = retention-policy.md (0.0328) — contains "Deletion requests are completed within 5 business days"
    but NO contact person anywhere in the 7-document corpus.
3 rounds, refusal each time → abstained (0 claims)
```
**Root cause: not a pipeline defect — a dataset label defect.** The gold snippet answers "how long", the question asks "who". Evidence that this is a labelling error rather than a model failure: **all three models abstain** (`gemma3:1b` 15:08, `qwen3:1.7b` 15:28, `mlx Qwen3-4B` in the preserved mlx artifact, which also abstains with 12 evidence records), and Phase 0 "completed" it by producing an ungrounded answer. Finishing action: keep the abstention, fix the label (Fix F-9).

**`q016` and `q017` (correct abstentions)**
- `q016`: rank-1 = `leave-policy.md` — adjacent topic, no contractor fact. Recovery round 1 correctly downgraded to `regenerate` (empty rewrite on already-refused evidence → `retrieval.reused`, `generation.skipped`, 0 ms) — the cheap path works as designed.
- `q017`: rank-1 = `thermal-runoff-study.txt`; 2 bounded recovery cycles; refusal preserved. Correct and the intended behaviour (the only correct Phase 0 abstention too).

**`q022` "flibbertygibbet zzzwarranty tokenlifetime" (correct outcome, defective mechanism)**
```
R1: 6 segments → retrieval.capped at 5 (lean tier max_context_chunks=5)
    generation 1369 ms → draft with 5 decomposed "claims"
    claims.started → claims.verified: 0 supported / 5 neutral
    → those 5 claims are label fragments: "Effective from:", "Maximum payload size:",
      "Default request rate limit:", "Strict endpoints limit callers to:", "The Account Service API"
R2 (query_rewrite → junk "Expand: …" → regenerate): same segments, regeneration 2730 ms
    → 5 more NEUTRAL claims
Final: 0/5 → FAILED, score 0.0 → grounding gate (analysis_service.py:750-801) → abstained
```
The 10 stored claim explanations are all *"Verification skipped: batch NLI unavailable and the per-claim fallback budget is exhausted."* The abstention is **correct**, but it was produced without any verification, and the claim set is garbage that a naive fix would deliver as grounded (see the RC-2 reproduction).

**`q024` "How long does a deletion request take to complete?" (false abstention)**
```
R1: Segment 1 = retention-policy.md (0.0328) with "Deletion requests are completed within 5 business days."
    generation 1631 ms → refusal → 0 claims → RETRIEVAL_FAILURE
R2 (query_rewrite): rewritten = "xml query: deletion time"   ← junk echo, accepted
    retrieval: retention-policy.md STILL rank 1 (0.0328)
    generation 1829 ms → real draft → claims.started → claims.verified: 1 claim
    claim (attempt=1): "Records under a legal hold are exempt from all deletion"   ← the wrong fact
    explanation: "Verification skipped: batch NLI unavailable and the per-claim fallback budget is exhausted."
R3 (re_retrieve): generation 1631 ms → claim "Backups expire after 7 days" → same skip
Final: 0/1 → FAILED, score 0.0 → grounding gate → abstained
```
Two compounding defects, both confirmed: **(a)** the single extracted claim is a *different* fact from the served policy than the one the question asks for, and **(b)** even that claim was never verified. Fixing only (b) risks delivering "records under legal hold are exempt" as a grounded answer to "how long does a deletion take" — see RC-3.

### 4.3 Cross-run control matrix (same KB, same dataset)

| Query | Phase 0 (pre-CRAFT) | Exp 1 `gemma3:1b` | Exp 2 `qwen3:1.7b` | Exp 3 `gemma3:1b`+reranker | llama_cpp `LFM2.5-1.2B` | mlx `Qwen3-4B` |
|---|---|---|---|---|---|---|
| `q003` | completed ✔ | abstained ✗ | completed ✔ | abstained (LOW_COVERAGE, 2 unverified claims) | completed ✔ | completed ✔ |
| `q006` | completed (ungrounded) | abstained ✗ | abstained | abstained | completed | abstained |
| `q024` | completed ✔ | abstained ✗ | completed ✔ | abstained (LOW_COVERAGE, unverified) | completed ✔ | completed ✔ |
| `q022` | completed (hallucination) | abstained ✔ | completed ✗ | abstained ✔ | completed (hallucination) | completed ✗ |

Reading: `q003`/`q024` are answerable by 4 of 5 generators; `q006` is unanswerable by 3 of 4 that were tested; `q022` is the adversarial case where CRAFT prompting fixed a Phase 0 hallucination (a **win** for the prompt change, not a regression).

---

## 5. Confirmed root causes

### RC-1 — Critical: unverified claims are recorded as `NEUTRAL` and then reported as "insufficient evidence"

**Mechanism (file:line):**
1. `verifier.py:1436-1445` — `fallback_budget` is force-zeroed whenever `attempt > 0`:
   ```python
   fallback_budget = max(0, int(cfg.max_individual_nli_fallback or 0))
   if attempt > 0 and fallback_budget:
       logger.info("Skipping individual-NLI fallback after failed recovery batches", ...)
       fallback_budget = 0
   ```
2. `verifier.py:1500-1508` — a claim with no verdict is persisted as `NEUTRAL` with the explanation *"Verification skipped: batch NLI unavailable and the per-claim fallback budget is exhausted."*
3. `verdict.py:134-171` — `NEUTRAL` is indistinguishable from "the evidence does not say this": `coverage = supported/total` → 0.
4. `analysis_service.py:750-801` — `_presentable_answer` + grounding gate withhold the answer and store `status="abstained"`.

**Measured blast radius:**
- Exp 1 (`gemma3:1b`): 12 of 53 claims — **all** claims on the two gated abstentions, 0 on the 21 delivered answers.
- Across the whole `trustrag_db` history: **84 claims** carry that explanation, on 5 different models and 3 dates (`gemma3:1b` 38+2, `LFM2.5-1.2B-GGUF` 7, `Llama-3.2-1B` 20, `LFM2.5-2.6B` 10, `LFM2.5-1.2B-OptiQ` 6, `qwen3:1.7b` 1). This is chronic, not incident-specific.
- Every one of those abstentions is reported to the operator and the user as **LOW_COVERAGE / "retrieved segments did not contain sufficient factual evidence"** — a false statement about the retrieval stage.

**Why the `attempt > 0` guard is not defensible:** the loop already carries the real spend guard — `llm_budget_exhausted()` (`verifier.py:1470`, `llm_ledger.py:97-110`), which is *deliberately inert for local tiers* ("Local tiers are never capped", `llm_ledger.py:80-83`). The blanket disable therefore removes the only fallback on exactly the tiers that have no cost excuse, and it converts one malformed model response into a user-visible false abstention. Measured cost of the fallback: **9/9 successful individual NLI calls, ~1 s each** (RC-2 reproduction).

### RC-2 — Critical: batch NLI structured output fails deterministically for `gemma3:1b`

Live reproduction against the installed model, driving the production function with the real fixture corpus:

```
batch_verify_claims_nli(claims, chunks, provider="ollama", model="gemma3:1b")
→ ValidationError: 1 validation error for BatchNLIVerdict
  verdicts  Field required
  [input_value={'vericits': ['VERDICT_1', 'VERDICT_2']}]
```
8 of 8 attempts failed identically. The model:
1. echoes the shape template appended by `build_structured_output_runnable` (`llm_utils.py:196-219`) with **placeholder values** (`"VERDICT_1"`), and
2. **typos the top-level key** (`vericits` for `verdicts`).

The repair path then cannot recover:
- `llm_utils.py:262-276` — the alias whitelist is `("results", "claims", "items", "data", "verdicts", "statements")`. **`vericits` is absent.**
- `_rescue_schema_from_text` (`llm_utils.py:82-170`) requires `1: SUPPORTED`-shaped lines; the payload is a JSON object, so `Case 2` finds nothing.

Note the schema-level asymmetry: `NLIVerdict`, `ClaimVerdict` and `FusedClaimVerdict` all carry tolerant `field_validator`s for aliases/shapes (`verifier.py:531-539, 564-577, 645-653`), while `BatchNLIVerdict` (`verifier.py:580-617`) has none — the one schema that needs it most.

**Consequence that explains Exp 1's headline metric:** the batch path fails for `gemma3:1b`, so the 41 `SUPPORTED` claims were produced by the **per-claim individual fallback** (all 41 are at `attempt=0`, all carry real NLI explanations, all link evidence). In other words, "1.0000 claim support" was delivered entirely by the fallback path that RC-1 disables on recovery rounds. Exp 3's lower 0.7551 is the same defect with more recovery rounds.

### RC-3 — Critical: the grounding gate checks grounding but not answer responsiveness

`verdict.py:92-179` computes coverage/contradiction over decomposed claims only. Nothing compares the answer to the question. Measured on Exp 1's 21 delivered answers (keyword check against the frozen dataset's `gold_answer_keywords`):

| Query | Question | Delivered answer (TRUSTED, 1 `SUPPORTED` claim) | Correct fact |
|---|---|---|---|
| `q001` | How long are bearer tokens valid? | "Backups expire after 7 days and are then unrecoverable." | 30 days |
| `q005` | How long are user records retained after an account is closed? | "Records under a legal hold are exempt from all deletion." | 30 days |
| `q009` | Above what sediment yield threshold did it rise? | "The study covered 12 catchments over 4 years." | 18 °C |

Each of those answers is **fully grounded in the served context** (claims marked `SUPPORTED`, 0 `CONTRADICTED` anywhere in the run), so NLI and the grounding gate both pass it. (`q018`, which also lacks gold keywords, is **not** in this list: its delivered answer does quote the scratch notes including the injection line and is responsive.)

**Answer coverage (gold keyword present in the delivered answer): 17/20 = 0.8500** over the delivered answers that have gold keywords (20 of the 21 completed; `q018` has none and is not scorable). Against the 24 answerable queries that is **17/24 = 0.7083** delivered-and-correct. Zero contradicted claims does **not** mean zero unsupported answers: 3 grounded-but-unresponsive answers were served as `TRUSTED`, and 12 claims were never verified at all.

### RC-4 — High: "citation correctness" measures the index range, not support

`scripts/run_baseline_eval.py:269`:
```python
citation_supporting = [1 <= n <= len(evidence) for n in cited]
```
Semantic re-audit of Exp 1 (segment order taken from the authoritative `retrieval.completed` trace; a citation is *supported* iff ≥80 % of the cited clause's content words occur in the cited segment):

| Metric | Value |
|---|---|
| Syntactic validity (what the harness reports as 1.0000) | 21/21 = 1.0000 |
| **Semantic support (cited segment contains the cited clause)** | **12/21 = 0.5714** |
| Clearly mis-cited (coverage < 0.5) | 5/21 |

Examples: `q001` cites `[Segment 4]` = `leave-policy.md` for a sentence that exists only in `retention-policy.md` (`[Segment 3]`); `q020` cites `[Segment 3]` = `retention-policy.md` for "Request payloads are limited to 10 megabytes" (a `service-api.md` sentence); `q015` cites `[Segment 4]` = `leave-policy.md` for "Strict endpoints limit callers to 20 requests per second" (a `limits-2026.txt` sentence).

Two related instrumentation defects:
- **Claim→evidence linkage is not a quality signal.** `verifier.py:1527-1535` links *every* served evidence record when a `SUPPORTED` claim's segment numbers do not map. Observed: `q027`'s claim "Backups expire after 7 days" is linked to `service-api.md`, not the `retention-policy.md` that contains it. `claims_with_evidence_rate` is therefore always 1.0.
- **Retrieval recall is measured over all persisted evidence**, including later recovery rounds and targeted claim retrievals (`analysis_service.py` `/detail` evidence list), so a chunk the model never saw can still score as "retrieved".

### RC-5 — Medium: junk recovery rewrites are accepted

Recorded rewrites: `"Expand: How quickly does token revocation take effect?"` (q003), `"Expand query: Who must be contacted…"` (q006), `"xml query: deletion time"` (q024), `"Expand: flibbertygibbet…"` (q022). These are echoed prompt scaffolding, and they pass because:
- `_sanitize_rewritten_query` (`graph.py:1119-1129`) strips only the exact prefixes in `_REWRITE_META_PREFIXES`; `"Expand query:"` and `"xml query:"` are not in the list, and a decorated output (`"**Expand:** …"`) defeats `startswith`.
- `_is_effectively_identical_query` then sees extra tokens (`expand`, `xml`, `query`) and calls the rewrite "informative".

Unit-level check with current HEAD: `"Expand: How quickly…"` **is** stripped and correctly detected as identical (`identical=True`) — while the recorded trace shows it was *not* stripped at run time, confirming the running build predates HEAD's `graph.py` (§2.2). `"xml query: deletion time"` is still **not** stripped at HEAD. Impact is bounded here (RRF still ranked the gold document 1st), but it wastes a full recovery round and pollutes `recovery_runs`.

### RC-6 — Medium: the pre-gate draft is discarded, so false abstentions are undiagnosable after the fact

`analysis_service.py:750-811` stores `answer_cited = _UNVERIFIED_ANSWER` and overwrites `answer`. For `q024` the model's actual draft text is therefore unrecoverable from the database — only its single extracted claim survives. Any future abstention audit will hit the same wall.

### RC-7 — Medium: evaluation harness metric gaps

`tests/eval/metrics.py` + `run_baseline_eval.py` currently produce no:
- **false-abstention rate** (expected `completed`, actual `abstained`) — computed ad hoc here as 3/24 = 0.125;
- **answer coverage** against `gold_answer_keywords` (only `outcome_match`, which conflates abstention correctness with answer correctness);
- **verification-availability signal** ("claims were never checked"), which is what would have exposed RC-1 automatically;
- **semantic citation quality** (RC-4).

---

## 6. Audit of the four requested quality axes (Exp 1, recomputed from live data)

| Axis | Metric | Value | Note |
|---|---|---|---|
| **Answer coverage** | delivered answers containing a gold keyword | **17/20 = 0.8500** | over the 24 answerable queries: **17/24 = 0.7083** (`q018` has no gold keywords and is unscorable) |
| **False-abstention rate** | expected `completed`, actual `abstained` | **3/24 = 0.125** (`q003`, `q006`, `q024`) | +1 dataset defect (`q006`) ⇒ 2/24 = 0.083 genuine pipeline false abstentions |
| **Unsupported answers** | contradicted claims | **0/53 = 0.0** | misleading: **3/20** delivered answers are non-responsive (RC-3); 12/53 claims were never verified at all |
| **Semantic citation quality** | cited segment contains the cited clause | **12/21 = 0.5714** (5 clearly wrong) | harness reports 1.0000 (range check only) |
| Claim support (as reported) | supported / total | 41/41 = 1.0000 | all produced by the per-claim fallback, all on `attempt=0` |
| Retrieval recall@8 (as reported) | 24/27 = 0.8889 | verified: the gold chunk is dense+sparse rank 1 for all three target queries | measured over all persisted evidence (RC-4) |

---

## 7. Root-cause chain (one line)

```
gemma3:1b emits a typo'd/placeholder batch-NLI JSON
  → repair alias list misses "vericits"            (llm_utils.py:262-276)
  → batch raises twice (verifier.py:1334-1356)
  → attempt>0 zeroes the per-claim fallback        (verifier.py:1437-1445)
  → claims auto-NEUTRAL with a "not verified" text (verifier.py:1500-1508)
  → coverage 0/N → FAILED, "insufficient evidence" (verdict.py:134-171)
  → grounding gate withholds the answer            (analysis_service.py:750-801)
  → FALSE ABSTENTION + false LOW_COVERAGE diagnosis (q022, q024)
```

---

## 8. Unresolved issues found (pre-existing, unrelated to the abstentions)

`pytest` → **3 failed, 731 passed**. All three are test-side staleness, no production defect:

| Test | Failure | Cause | Proposed fix |
|---|---|---|---|
| `tests/test_analyses.py::test_create_analysis` | `assert 'ollama' == 'llama_cpp'` | hard-codes the v1.28 default provider; `models.yaml` v1.29 defaults to `ollama` and `.env` sets `AI_PROVIDER=ollama` | parametrise over `get_model_config().llm_provider` |
| `test_wave2_cloud_resilience.py::test_effective_cloud_model_is_validated_even_when_request_omits_it` | `AttributeError: '_CfgStub' object has no attribute 'deep_reasoning_model'` | validator now reads `cfg.deep_reasoning_model`; stub is stale | add the attribute to `_CfgStub` |
| `test_wave2_cloud_resilience.py::test_verification_model_allowlist_rejects_unbudgeted_cloud_model` | same | same | same |

No test covers the batch-NLI alias repair or the `attempt>0` fallback disable.

---

## 9. Proposed minimal fixes (for approval — **not implemented**)

Ordered by (evidence strength × reliability impact) ÷ blast radius. Each is independently reversible and changes no model, no config value and no frozen artifact.

### F-1 — Never present "not verified" as "evidence insufficient" *(fixes RC-1; required for q022/q024 honesty)*
`verifier.py:1436-1445` + `verdict.py` + `analysis_service.py`.
- Stop force-zeroing `fallback_budget` on `attempt > 0`; keep the existing `llm_budget_exhausted()` + decrement guards.
- Persist an explicit **`UNVERIFIED`** claim state (or an `unverified: true` flag) for claims with no verdict, exclude them from `coverage`, and surface `diagnosis_type` `VERIFICATION_UNAVAILABLE` instead of `LOW_COVERAGE`, so a verifier outage can never be reported as an evidence failure (mirrors the existing `RETRIEVAL_OUTAGE` discipline).
- Effect: one malformed call costs one honest "verification unavailable" outcome instead of a silent false abstention; Exp 1's q022/q024 would have been reported correctly even before any model-side improvement.

### F-2 — Make batch NLI survive key typos and template placeholders *(fixes RC-2)*
`llm_utils.py:262-276` + `verifier.py:580-617`.
- Add a tolerant `field_validator` on `BatchNLIVerdict.verdicts` accepting the observed alias family (`vericits`, `verdict`, `results`, `items`, `data`) — consistent with every other verdict schema.
- Reject placeholder verdict tokens (`VERDICT_1`, `<array>`, `SUPPORTED/CONTRADICTED/NEUTRAL` template echoes) instead of letting the repair invent them.
- Measured expectation: removes the 8/8 deterministic batch failure; the batch path stops being dead code for ≤3B models.

### F-3 — Reject label-fragment claims before they can be delivered *(fixes the q022 hazard)*
`verifier.py:211-241` `_filter_degenerate_claims`.
- Also drop colon-terminated label fragments (`"Effective from:"`, `"Maximum payload size:"`) and title-case heading lines without terminal punctuation. Deterministic, no model, no new dependency.
- Necessary companion to F-1: with the fallback re-enabled, `q022`'s fragments are individually judged `SUPPORTED` (measured in the RC-2 reproduction) and would otherwise be delivered as a grounded answer.

### F-4 — Add a responsiveness check before an answer may be `TRUSTED` *(fixes RC-3, the largest quality gap)*
Cheapest evidence-backed option, in order of preference:
1. **Prompt-side**: add one CRAFT rule — "answer the question actually asked; if the premise answers a different fact about the same document, state only what it says about the asked fact, or ABSTAIN" — plus reuse of the existing contrastive example format.
2. **Deterministic post-check**: require each delivered answer to share ≥1 content token (or a numeric literal) with the query *or* with a gold-keyword-equivalent from the served context; otherwise downgrade to UNCERTAIN rather than TRUSTED.
Recommend (1) first with (2) gated behind a measurement, because (2) is a heuristic that will misfire on legitimately indirect answers. This is the only fix that addresses the 4 wrong-but-grounded answers.

### F-5 — Make citation validity semantic, not syntactic *(fixes RC-4)*
- Extend the existing `strip_invalid_citations` (`generator.py:894-901`) to also drop a `[Segment N]` whose segment text does not contain the cited clause (lexical containment, no new model). Keep the range check as the first pass.
- Fix the claim→evidence linkage fallback (`verifier.py:1527-1535`) so it links the *specific* segments the claim's own citation markers name, never "all evidence".
- Add `semantic_citation_quality` to `metrics.py`/`run_baseline_eval.py` and keep the syntactic check as a separate reported field.

### F-6 — Stop accepting echoed scaffolding as a query rewrite *(fixes RC-5)*
`graph.py:1106-1179`.
- Broaden the meta-prefix list (`expand query:`, `xml query:`, `search query:`, optional markdown decoration) and treat a rewrite whose only new tokens are instruction-echo words (`expand`, `query`, `xml`, `search`, `rewrite`) as uninformative → keep the original query. No behavioural change to the recovery graph.

### F-7 — Preserve the pre-gate draft for auditability *(fixes RC-6)*
`analysis_service.py` — persist the withheld draft (e.g. `answer_withheld`) alongside `answer_cited` when the grounding gate fires. Storage-only, no user-facing change, and it makes every future abstention audit possible.

### F-8 — Close the eval-harness metric gaps *(fixes RC-7)*
`tests/eval/metrics.py` + `scripts/run_baseline_eval.py`: add `false_abstention_rate`, `answer_coverage` (keyword match against delivered answers), `verification_availability_rate`, `semantic_citation_correctness`; report retrieval recall over the *served* (round-1) context as well as all persisted evidence.

### F-9 — Fix the `q006` dataset label *(needs explicit approval: touches the frozen baseline)*
`baseline_v1.jsonl` — either reword `q006` to "How long does a deletion request take to complete contact?" (it duplicates `q024`) or relabel it `expected_outcome: abstained` with a note. **Do not edit `baseline_v1.jsonl`** — add a `baseline_v2.jsonl` alongside it and re-baseline, so v1 stays frozen and comparable.

### F-10 — Fix the three stale tests (§8). Test-only, no product change.

**Recommended Phase-1 slice:** F-1 + F-2 + F-3 + F-10 as one change set (all four are small, mutually dependent for safety, and together eliminate the false-abstention mechanism), then re-run the frozen baseline before deciding on F-4/F-5/F-9. F-6, F-7, F-8 are cheap and can follow.

---

## 10. Regression tests to add (with each fix)

| Fix | Test | Assertion |
|---|---|---|
| F-1 | `test_verification_marks_unverified_claims_distinctly` | a claim with no NLI verdict is `UNVERIFIED`, never counted in `coverage`; diagnosis is `VERIFICATION_UNAVAILABLE`, not `LOW_COVERAGE` |
| F-1 | `test_per_claim_nli_fallback_runs_on_recovery_rounds` | with `attempt=2` and a failing batch, the individual fallback is invoked for each missing claim |
| F-2 | `test_batch_nli_tolerates_key_typo` | `{"vericits": [...]}` parses into `BatchNLIVerdict` |
| F-2 | `test_batch_nli_rejects_template_placeholders` | `["VERDICT_1"]` does **not** become a verdict |
| F-3 | `test_filter_degenerate_claims_drops_label_fragments` | `"Effective from:"`, `"Maximum payload size:"`, `"Eligibility"` are dropped; `"Deletion requests are completed within 5 business days."` survives |
| F-4 | `test_unresponsive_answer_is_not_trusted` | an answer sharing no content with the query is not `TRUSTED` |
| F-5 | `test_citation_stripped_when_segment_lacks_sentence` | a `[Segment N]` pointing at a segment without the clause is stripped; the range check still passes valid refs |
| F-6 | `test_junk_rewrite_is_treated_as_uninformative` | `"xml query: deletion time"` → original query retained |
| F-8 | `test_metrics_report_false_abstention_and_answer_coverage` | scores an abstained-with-evidence case and a wrong-but-grounded case distinctly |
| — | `test_gemma_batch_nli_failure_is_recoverable_end_to_end` | integration: a stubbed failing batch + `attempt=2` still yields verified claims (guards RC-1 permanently) |

Plus a **re-baseline acceptance gate**: after F-1..F-3, re-run `scripts/run_baseline_eval.py` on the same frozen KB/dataset and require *false-abstention rate ≤ 1/24*, *claim support ≥ 1.0*, *no `SUPPORTED` degenerate claims*, and *p50 latency within +10 %* of the Exp 1 value (6,899 ms). Any regression on `q016`/`q017`/`q022` (which must stay abstained) blocks the change.

---

## 11. Constraints honoured

- Frozen baseline, fixture corpus, `models.yaml` values, model set, and production serving configuration **unchanged**.
- No new models, dependencies, installations, cloud calls, or unrelated refactoring.
- Read-only investigation only; the two commit-worthy items already in the working tree were reviewed, not reverted.
- Services started for the investigation (`mongod`, `ollama serve`) were stopped after use; no data was written to either.

## 12. Reproduction commands (for re-verification during implementation)

```bash
# evidence source of truth (read-only)
mongosh trustrag_db --eval 'db.analyses.find({query:"How long does a deletion request take to complete?",
  llm_model:"gemma3:1b"}).sort({created_at:-1}).limit(1).pretty()'
mongosh trustrag_db --eval 'db.claims.find({explanation:/batch NLI unavailable/}).count()'   # 84

# root-cause reproduction (RC-2 / RC-1), local only
ollama serve &
cd apps/api && source .venv/bin/activate
python - <<'PY'
import asyncio
from pathlib import Path
from app.rag.verification.verifier import batch_verify_claims_nli, verify_claim_nli
C = Path("tests/eval/fixtures/corpus")
names = ["service-api.md","limits-2026.txt","retention-policy.md","scratch-notes.txt","leave-policy.md"]
chunks = [{"text": (C/n).read_text(), "filename": n, "page": 1, "rrf_score": 0.033-0.001*i} for i,n in enumerate(names)]
claims = ["Effective from:", "Maximum payload size:", "Default request rate limit:"]
async def go():
    try:  await batch_verify_claims_nli(claims, chunks, provider="ollama", model="gemma3:1b")
    except Exception as e: print("BATCH RAISED:", type(e).__name__, str(e)[:120])
    for c in claims: print(c, "->", (await verify_claim_nli(c, chunks, provider="ollama", model="gemma3:1b"))["verdict"])
asyncio.run(go())
PY
```

---

## 13. Approval requested

Approve (a) the Phase-1 slice **F-1 + F-2 + F-3 + F-10**, (b) the acceptance gate and regression tests in §10, and (c) defer F-4/F-5/F-6/F-7/F-8/F-9 until after the re-baseline. **No implementation has begun.**
