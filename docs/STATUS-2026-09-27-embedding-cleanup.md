# Status — Dead-code cleanup + single embedding engine (2026-09-27)

## Scope
- Deleted verified dead/unused backend code and config keys.
- Locked embeddings to one engine: ONNX BGE, `embedding.model` in
  `apps/api/config/models.yaml` (`BAAI/bge-small-en-v1.5`) as sole source of truth.
- `models.yaml` config_version bumped 1.21 → 1.22.

## Deleted dead code
- `app/core/exceptions.py`: `RetrievalError`, `EmbeddingError`,
  `VerificationError`, `RecoveryError`. Kept `GenerationError` as parent of live
  `LLMUnavailableError`.
- `app/core/experimentation.py`: `is_enabled`, `get_flag` (+ orphaned
  `_matches_rule`/`_in_rollout` on `FeatureFlagManager`), `conversion_rate`,
  `avg_latency_ms`, `record_conversion`, `record_custom_metric`, `get_metrics`,
  `get_all_metrics`, `create_agent_config_from_experiment`.
- `app/core/semantic_cache.py`: `clear_all_cache` (tests use `reset_module_state`).
- `models.yaml` keys: `llm.framework`, `embedding.framework/provider/
  quantized_model_path/quantization`, `verification.framework`,
  `ingestion.max_total_tokens_per_doc`, `ocr.engine`,
  `observability.metrics_enabled`, `cost_controls.enable_response_caching`,
  `optimization.max_context_tokens`, `local_llm.max_loaded_models`.

## Embedding lock (full provider-choice removal)
- Removed: `EMBEDDING_PROVIDER`/`EMBEDDING_BACKEND`/`EMBEDDING_MODEL` envs,
  `Settings.embedding_provider` + `gemini_embedding_model`,
  `ModelConfig.embedding_provider`, request-level overrides (upload Form,
  `AnalysisCreate`, `AgentState`, pipeline/retriever/graph signatures),
  HuggingFace torch branch (`BGEAwareHuggingFaceEmbeddings`,
  `CachedEmbeddingsWrapper`), KB `embedding_provider` pinning, retired-provider guards.
- `get_embedding_model(model=None)` is now ONNX-only; fixed `"onnx"` labels kept
  in status/snapshot payloads for API-shape stability.
- Frontend: Playground no longer sends embedding fields; `/models/providers`
  lists one engine; `PlaygroundPage.test.jsx` mock updated to `onnx`.

## Verification
- `ruff check` + `ruff format`: clean.
- Backend `pytest`: **427 passed**.
- Frontend `vitest`: **25 passed**.
- Diff: 27 files, +170 / −873.

## Follow-ups (not done)
- Refresh `README`/`docs/` references to `EMBEDDING_PROVIDER=onnx|huggingface`
  and the Playground embedding selector.
- `docker-compose.yml` comment mentioning the huggingface provider.
- Consider consolidating `scripts/export_bge_onnx.py` into `ensure_onnx_models.py`.
