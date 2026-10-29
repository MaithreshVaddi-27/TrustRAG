# RAG and Agent Audit — 2026-10-29

## Scope and outcome

Audited the backend RAG/agent path from retrieval and generation through claim decomposition, NLI verification, recovery, verdict persistence, and response presentation, with emphasis on the report that related claims were marked `NEUTRAL`. Preserved the pre-existing working-tree changes. No live provider, database, or manual README setup was needed; the backend test suite exercises the relevant paths with mocks and local test doubles.

## Confirmed finding fixed

### High — verification failure could be reported as `PASS`

`apps/api/app/rag/agent/graph.py`, `verification_node`: when NLI verification timed out or raised an exception at the recovery-attempt limit, the error branch set an empty claim list and `reliability_score=None`, but then set `verdict_status="PASS"`. `should_recover()` treats `PASS` as successful termination, while the analysis service’s presentation gate allows the verified/trusted answer through. This allowed a run with no completed verification to look successful.

**Fix:** both timeout and exception paths now remain `FAIL`, independent of retry count. The workflow can end when its bounded retry budget is exhausted, but it cannot claim verification succeeded. Added regression coverage for an exception at the recovery limit in `apps/api/tests/test_agent.py`.

## Additional confirmed finding fixed

### High — missing Qdrant collection bypassed Mongo-backed self-heal

A KB whose Qdrant collection had not been created failed before the existing self-heal path: dense retrieval queried collection metadata and propagated the Qdrant 404, while sparse retrieval converted the same missing-index response into a generic retrieval outage. The agent only checks Mongo chunks after a successful empty retrieval, so it never rebuilt vectors from stored chunks. This matched the observed IRS KB state (Mongo chunks present, no Qdrant collection/points) and caused retries to repeat against the absent index.

**Fix:** dense and sparse retrieval now treat only Qdrant's typed HTTP 404 (`UnexpectedResponse`, status 404) as an empty/missing-index result. Other Qdrant errors remain outages. The existing agent self-heal can then inspect Mongo, initialize the missing collection, and rebuild it. Added focused regressions for both retrieval branches and the missing-collection agent path.

## Reported neutral-claim symptom

The configured fused decompose-and-verify path is disabled in the current uncommitted `apps/api/config/models.yaml` change (`fused_decompose_verify: false`), and small local models already bypass it in code. Those paths use classic decomposition followed by batch/per-claim NLI. NLI/model-output failures are intentionally normalized to `NEUTRAL` rather than mislabeled `SUPPORTED`; that is safer than inventing support, but it can make supported claims appear neutral if the selected model fails to produce a valid structured response. The verifier includes alias normalization for common local-model labels and per-claim fallbacks. The focused verification tests pass, but without a live provider and representative corpus it is not possible to quantify the remaining real-model false-neutral rate or tune a threshold responsibly.

Recommended next diagnostic for a reported case: inspect its persisted trace and claim explanation alongside the exact evidence chunks, effective provider/model, and whether batch/per-claim fallback occurred. Use a small, labeled evaluation set of supported, contradicted, and absent claims before changing NLI prompts or acceptance policy.

## Review and validation

- ECC review workflow completed on the current diff: no verified CRITICAL/HIGH findings; one low-value style observation was not actionable.
- Additional read-only frontend review found no verified correctness/security regression in the diff; that agent’s frontend-specific pass was incomplete due to an authentication error.
- Focused backend tests: `90 passed` (`test_agent.py` and `test_verification.py`).
- Full backend suite from `apps/api`: `703 passed`; total coverage `79.24%` (configured minimum `78%`).
- `ruff check app/rag/agent/graph.py tests/test_agent.py`: passed.
- `ruff format --check app/rag/agent/graph.py tests/test_agent.py`: passed.
- `git diff --check`: passed.
- No live LLM/manual README environment run was performed. The attempted repo-root test invocation was invalid because tests require `apps/api` as the working directory; rerunning from the API project root passed.

## Remaining notes

- Neutral is an uncertainty label, not a claim that the statement is false. Do not change neutral to supported merely because a claim appears query-related; support must be grounded in evidence.
- Retrieval/verification quality against a real corpus still needs a labeled evaluation run. Existing unit tests validate deterministic behavior, not provider-specific NLI accuracy.
