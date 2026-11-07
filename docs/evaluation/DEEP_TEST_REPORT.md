# TrustRAG — Deep Test Report

**Date:** 2026-11-07

## Test summary
- Backend: 757 passed, 4 skipped, coverage 78.73%
- ruff: clean, mypy: clean (75 files)
- Frontend: lint clean, build clean

## Lowest-coverage modules (prioritized for test additions)
| Module | Coverage | Priority |
|---|---|---|
| app/llm/llm_utils.py | 18% | P2 |
| app/core/observability/logging.py | 49% | P3 |
| app/llm/model_registry.py | 51% | P2 |
| app/api/deps.py | 52% | P1 |
| app/db/mongodb.py | 54% | P2 |
| app/llm/onnx_embeddings.py | 55% | P2 |
| app/services/search_service.py | 58% | P2 |
| app/llm/onnx_reranker.py | 63% | P2 |
| app/core/system/memory.py | 64% | P3 |
| app/mcp/server.py | 66% | P2 |
| app/services/auth_service.py | 69% | P1 |
| app/services/kb_service.py | 70% | P1 |
| app/services/analysis_service.py | 77% | P1 |

## Recommended changes
1. **P1 (correctness/auth):** Add unit tests for `deps.py`, `auth_service.py`, `kb_service.py`, `analysis_service.py` (ownership/IDOR paths, token revocation, KB CRUD).
2. **P2 (reliability):** Add tests for `onnx_embeddings.py`, `onnx_reranker.py`, `model_registry.py`, `search_service.py`.
3. **P2 (observability):** Add tests for `logging.py`, `tracing.py`.
4. **P3 (infra):** `memory.py`, `hardware.py`, `concurrency.py`.

## Where to make changes (file paths)
- `apps/api/app/api/deps.py` — token revocation, user lookup
- `apps/api/app/services/auth_service.py` — register/auth/revoke
- `apps/api/app/services/kb_service.py` — KB CRUD, ownership
- `apps/api/app/services/analysis_service.py` — analysis lifecycle
- `apps/api/app/llm/onnx_embeddings.py` — embedding cache, micro-batch
- `apps/api/app/llm/onnx_reranker.py` — rerank scoring
- `apps/api/app/llm/model_registry.py` — provider detection
- `apps/api/app/services/search_service.py` — web search, sanitization
- `apps/api/app/mcp/server.py` — MCP tool dispatch, tenant guards

## Browser QA
- Landing, login, dashboard: no console errors, all network 200.
- Full E2E (upload→index→analysis): TRUSTED, 1.0 reliability, validated via API.

## Deferred
- See FUTURE_IMPROVEMENTS.md.
