"""
TRUSTRAG — Local LLM Client implementations for Ollama, llama.cpp, and MLX.

Provides first-class LangChain BaseChatModel interfaces with zero native
compilation dependencies by communicating directly with Ollama's local REST API
and the OpenAI-compatible server APIs of llama.cpp (llama-server) and Apple
MLX (mlx_lm.server) via async httpx.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, TypeVar

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.core.concurrency import get_global_semaphore
from app.core.config import get_model_config
from app.core.exceptions import ConfigurationError, LLMUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Reuse HTTP connections for the Ollama/llama.cpp request fan-out. One analysis
# can perform generation, decomposition, batch NLI, fallback NLI, and recovery;
# per-call clients previously discarded keep-alive connections every time.
_HTTP_CLIENTS: dict[tuple[str, float, int], httpx.AsyncClient] = {}
_HTTP_CLIENTS_LOCK = threading.Lock()


# Shared global semaphore for local LLM inference.
# Managed by app.core.concurrency.get_global_semaphore() - hardware-aware
# (2/4/8 based on RAM) with LOCAL_LLM_MAX_CONCURRENCY env override.
def _get_local_llm_semaphore() -> asyncio.Semaphore:
    """Get the global concurrency semaphore for local LLM inference."""
    return get_global_semaphore()


def _shared_http_client(base_url: str, timeout: float) -> httpx.AsyncClient:
    """Return a per-event-loop, per-endpoint pooled AsyncClient with connection limits."""
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = 0
    key = (base_url.rstrip("/"), float(timeout), loop_id)
    with _HTTP_CLIENTS_LOCK:
        client = _HTTP_CLIENTS.get(key)
        if client is None or client.is_closed:
            # Connection pooling: keep-alive for local inference servers
            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0,
            )
            client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
            )
            _HTTP_CLIENTS[key] = client
        return client


async def close_local_llm_clients() -> None:
    """Close all pooled local-LLM HTTP clients during application shutdown."""
    with _HTTP_CLIENTS_LOCK:
        clients = list(_HTTP_CLIENTS.values())
        _HTTP_CLIENTS.clear()
    if clients:
        results = await asyncio.gather(
            *(client.aclose() for client in clients), return_exceptions=True
        )
        errors = [str(result) for result in results if isinstance(result, Exception)]
        if errors:
            logger.debug("One or more local LLM clients failed to close", errors=errors)


# ─── Model Offloading (Phase 4.1) ────────────────────────────────────────────────
# Auto-unload inactive models from memory to save RAM.
# Ollama: call /api/ps to check loaded models, then /api/delete to unload unused
# llama.cpp: auto-unload on idle (keep_alive) or restart server with new model


async def unload_ollama_inactive_models(
    base_url: str, keep_model: str | None = None
) -> dict[str, Any]:
    """
    Unload inactive models from Ollama to free memory.

    Args:
        base_url: Ollama base URL
        keep_model: Model name to keep loaded (won't be unloaded)

    Returns:
        Dict with unloaded models info
    """
    cfg = get_model_config()
    if not cfg.local_llm_model_unload_enabled:
        return {"status": "disabled", "unloaded": []}

    endpoint = f"{base_url.rstrip('/')}/api/ps"
    try:
        client = _shared_http_client(base_url, 10.0)
        res = await client.get(endpoint)
        if not res.is_success:
            return {"status": "error", "message": f"HTTP {res.status_code}", "unloaded": []}

        data = res.json()
        loaded_models = data.get("models", [])

        # Find models to unload (not the keep_model)
        to_unload = []
        for model_info in loaded_models:
            model_name = model_info.get("name", "")
            if model_name and model_name != keep_model:
                to_unload.append(model_name)

        if not to_unload:
            loaded_names = [m.get("name") for m in loaded_models]
            return {"status": "no_action_needed", "loaded": loaded_names, "unloaded": []}

        # Unload each model from VRAM via keep_alive=0.
        # NOTE: Ollama's /api/delete PERMANENTLY DELETES the model blob from
        # disk — never use it for memory offloading. POST /api/generate with
        # keep_alive=0 unloads the model from memory while keeping it on disk.
        unloaded = []
        for model_name in to_unload:
            try:
                unload_payload = {"model": model_name, "keep_alive": 0}
                unload_res = await client.post(
                    f"{base_url.rstrip('/')}/api/generate", json=unload_payload
                )
                if unload_res.is_success:
                    unloaded.append(model_name)
                    logger.info("Unloaded inactive Ollama model", model=model_name)
                else:
                    logger.warning(
                        "Failed to unload Ollama model",
                        model=model_name,
                        status=unload_res.status_code,
                    )
            except Exception as exc:
                logger.warning("Error unloading Ollama model", model=model_name, error=str(exc))

        return {"status": "success", "unloaded": unloaded, "kept": keep_model}

    except Exception as exc:
        logger.error("Failed to unload Ollama inactive models", error=str(exc))
        return {"status": "error", "message": str(exc), "unloaded": []}


async def unload_llamacpp_inactive_models(
    base_url: str, keep_model: str | None = None
) -> dict[str, Any]:
    """
    Unload inactive models from llama.cpp server.

    For llama.cpp, the model is loaded via --model flag at startup.
    To "unload", we rely on the server's keep_alive mechanism or restart.
    This function checks if a different model is loaded and returns info.

    Args:
        base_url: llama.cpp base URL
        keep_model: Model name to keep loaded (for info purposes)

    Returns:
        Dict with current model info
    """
    cfg = get_model_config()
    if not cfg.local_llm_model_unload_enabled:
        return {"status": "disabled", "current_model": None}

    # For llama.cpp, model management is done at server startup.
    # The server serves one model at a time (the one passed via --model).
    # We can check which model is currently loaded via /v1/models
    endpoint = f"{base_url.rstrip('/')}/models"
    try:
        client = _shared_http_client(base_url, 10.0)
        res = await client.get(endpoint)
        if not res.is_success:
            return {"status": "error", "message": f"HTTP {res.status_code}", "current_model": None}

        data = res.json()
        models = data.get("data", [])
        current_model = models[0].get("id") if models else None

        # llama.cpp doesn't support dynamic unload via API.
        # User needs to restart llama-server with the desired model.
        # We just report the current state.
        return {
            "status": "info_only",
            "current_model": current_model,
            "note": "llama.cpp serves one model at a time. Restart server to change model.",
            "keep_model": keep_model,
        }

    except Exception as exc:
        logger.error("Failed to check llama.cpp model status", error=str(exc))
        return {"status": "error", "message": str(exc), "current_model": None}


async def unload_inactive_models_for_provider(
    provider: str, base_url: str, keep_model: str | None = None
) -> dict[str, Any]:
    """
    Unified function to unload inactive models for a provider.

    Args:
        provider: Provider name ("ollama", "llama_cpp", "llamacpp", "mlx")
        base_url: Base URL for the provider
        keep_model: Model to keep loaded

    Returns:
        Dict with unload results
    """
    norm = (provider or "").strip().lower()
    if norm == "ollama":
        return await unload_ollama_inactive_models(base_url, keep_model)
    elif norm in ("llama_cpp", "llamacpp", "mlx"):
        return await unload_llamacpp_inactive_models(base_url, keep_model)
    else:
        return {"status": "unsupported", "provider": provider, "unloaded": []}


# Periodic cleanup task (can be called from a background task)
_LAST_UNLOAD_CHECK: dict[str, float] = {}
_UNLOAD_CHECK_LOCK = threading.Lock()


async def maybe_unload_inactive_models(
    provider: str, base_url: str, current_model: str | None = None
) -> dict[str, Any] | None:
    """
    Check if it's time to unload inactive models and do so if needed.
    Rate-limited to once per model_unload_timeout period.

    Args:
        provider: Provider name
        base_url: Base URL
        current_model: Currently active model (won't be unloaded)

    Returns:
        Result dict if unload was attempted, None if skipped
    """
    cfg = get_model_config()
    if not cfg.local_llm_model_unload_enabled:
        return None

    # Parse timeout (e.g., "5m" -> 300 seconds)
    timeout_str = cfg.local_llm_model_unload_timeout
    try:
        if timeout_str.endswith("s"):
            timeout_sec = int(timeout_str[:-1])
        elif timeout_str.endswith("m"):
            timeout_sec = int(timeout_str[:-1]) * 60
        elif timeout_str.endswith("h"):
            timeout_sec = int(timeout_str[:-1]) * 3600
        else:
            timeout_sec = 300  # Default 5 minutes
    except ValueError:
        timeout_sec = 300

    now = time.time()
    key = f"{provider}:{base_url}"

    with _UNLOAD_CHECK_LOCK:
        last_check = _LAST_UNLOAD_CHECK.get(key, 0)
        if now - last_check < timeout_sec:
            return None  # Not time yet
        _LAST_UNLOAD_CHECK[key] = now

    # Time to check - perform unload
    logger.info("Periodic model unload check", provider=provider, timeout=f"{timeout_sec}s")
    return await unload_inactive_models_for_provider(provider, base_url, current_model)


T = TypeVar("T", bound=BaseModel)

# Providers served by a local inference process (single-tenant, serial).
# Output caps and concurrency guards apply ONLY here — cloud chat models use
# different parameter names (e.g. max_output_tokens) and must not receive ours.
# "mlx" (mlx_lm.server, Apple Silicon) speaks the same OpenAI-compatible
# protocol as llama.cpp, so it shares the client, caps, and semaphore.
LOCAL_LLM_PROVIDERS = frozenset({"ollama", "llama_cpp", "llamacpp", "mlx"})


def local_cap_kwargs(provider: str | None, max_tokens: int) -> dict[str, int]:
    """Task-sized output caps for local inference servers only.

    A rewrite needs ~20 words, a single NLI verdict ~100 tokens — letting them
    inherit the 1024-token default grows per-call KV cache and wall time for
    nothing. Returns {} for cloud providers (foreign parameter names).
    """
    if (provider or "").strip().lower() in LOCAL_LLM_PROVIDERS:
        return {"max_tokens": int(max_tokens)}
    return {}


# Model ids whose thinking trace shares the completion budget with the
# answer (observed live: muse-glimmer-30b spends ~475 tokens reasoning about
# trivia; qwen3:1.7b on Ollama burns small num_predict budgets entirely in
# the thinking trace → empty content → ABSTAIN). Verification caps sized
# for direct-answer models truncate their verdict JSON → false NEUTRALs →
# failed reliability checks.
REASONING_MODEL_KEYWORDS = (
    "glimmer",
    "gpt-oss",
    "reasoning",
    "deepseek-r1",
    "r1-",
    "qwen3",
    "qwq",
    "think",
)


def is_reasoning_model(model: str | None) -> bool:
    """True when the model id looks like a thinking/reasoning model."""
    name = (model or "").lower()
    return any(kw in name for kw in REASONING_MODEL_KEYWORDS)


def verification_cap_kwargs(
    provider: str | None, model: str | None, max_tokens: int
) -> dict[str, int]:
    """Task-sized output caps for verification calls on any provider.

    Direct-answer local models keep the lean KV-saving caps. Thinking
    models (local or cloud) get headroom with a 1024-token floor: live
    probes show muse-glimmer-30b spending ~475 tokens reasoning about
    trivia and starving a 256-token rewrite to empty, while 512+ succeeds
    — a starved call costs a full retry spiral, dwarfing the extra tokens.
    Non-reasoning cloud models keep instance defaults ({} — the registry
    already sets tight max_output_tokens). Reasoning cloud models get the
    headroom with the provider-correct param name.
    """
    norm = (provider or "").strip().lower()
    if is_reasoning_model(model):
        roomy = max(int(max_tokens) * 2, 1024)
        if norm in LOCAL_LLM_PROVIDERS:
            return {"max_tokens": roomy}
        if norm in ("gemini", "google_genai"):
            return {"max_output_tokens": roomy}
        return {"max_tokens": roomy}
    if norm in LOCAL_LLM_PROVIDERS:
        return {"max_tokens": int(max_tokens)}
    return {}


def _convert_messages_to_dict(messages: list[Any]) -> list[dict[str, str]]:
    """Normalize LangChain message objects or tuples into OpenAI/Ollama role dicts."""
    converted: list[dict[str, str]] = []
    for m in messages:
        if isinstance(m, tuple) and len(m) == 2:
            role, content = m
            role_norm = (
                "assistant"
                if role in ("ai", "assistant")
                else ("system" if role == "system" else "user")
            )
            converted.append({"role": role_norm, "content": str(content)})
        elif isinstance(m, SystemMessage):
            converted.append({"role": "system", "content": str(m.content)})
        elif isinstance(m, AIMessage):
            converted.append({"role": "assistant", "content": str(m.content)})
        elif isinstance(m, HumanMessage):
            converted.append({"role": "user", "content": str(m.content)})
        elif isinstance(m, BaseMessage):
            role_norm = getattr(m, "role", "user")
            converted.append({"role": str(role_norm), "content": str(m.content)})
        elif isinstance(m, dict):
            converted.append(
                {
                    "role": str(m.get("role", "user")),
                    "content": str(m.get("content", "")),
                }
            )
        elif isinstance(m, str):
            converted.append({"role": "user", "content": m})
        else:
            logger.warning("Dropping unsupported message type", msg_type=type(m).__name__)
    if not converted:
        raise ConfigurationError("No valid messages to send to local LLM (empty prompt)")
    return converted


# ─── Ollama Chat Model ─────────────────────────────────────────────────────────


class ChatOllamaClient(BaseChatModel):
    """
    Lightweight, ultra-fast client for local Ollama instances.
    Calls POST {base_url}/api/chat via httpx.
    """

    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="granite4.2:3b-q4_K_M")
    temperature: float = Field(default=0.2)
    top_p: float = Field(default=0.9)
    timeout: float = Field(default=120.0)
    format: str | None = Field(default=None)
    # Penalize token repetition: small local models loop scaffolding
    # (e.g. repeating a FINAL_SECTION block until max tokens). 1.1 = mild.
    repeat_penalty: float = Field(default=1.1)

    @property
    def _llm_type(self) -> str:
        return "ollama-client"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
            )
        raise ConfigurationError(
            "Synchronous Ollama generation cannot run inside an active event loop; "
            "use ainvoke() instead."
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        dict_messages = _convert_messages_to_dict(messages)
        endpoint = f"{self.base_url.rstrip('/')}/api/chat"

        cfg = get_model_config()
        # Use config values with env override, fallback to hardcoded defaults
        default_num_ctx = cfg.local_llm_num_ctx
        default_num_batch = cfg.local_llm_num_batch  # Not used by Ollama, but kept for consistency
        default_keep_alive = cfg.local_llm_keep_alive

        # Optimization flags from models.yaml
        use_prompt_cache = cfg.prompt_caching

        # Speculative Decoding / Early Exit (Phase 2.5)
        min_p = cfg.local_llm_min_p
        top_k = cfg.local_llm_top_k
        early_exit_eos = cfg.local_llm_early_exit_eos

        options: dict[str, Any] = {
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            # OPT (local-LLM load): 2048 overflowed with 3000-char contexts +
            # system prompt and produced truncated stubs. 4096 matches
            # llama-server -c 4096 and fits the reduced context budget.
            "num_ctx": kwargs.get("num_ctx", default_num_ctx),
            "num_predict": kwargs.get("max_tokens", 1024),
            "repeat_penalty": kwargs.get("repeat_penalty", self.repeat_penalty),
            # Batch size for prompt processing (Ollama uses num_batch;
            # accept n_batch alias since callers may use llama.cpp naming).
            "num_batch": kwargs.get("num_batch", kwargs.get("n_batch", default_num_batch)),
            # Min-p sampling: only tokens with p >= min_p * p_max are considered
            "min_p": min_p if min_p > 0.0 else None,
            # Top-k sampling: restrict to top K tokens
            "top_k": top_k if top_k > 0 else None,
        }
        # Clean up None values
        options = {k: v for k, v in options.items() if v is not None}
        # Ollama prompt caching: num_keep specifies how many prompt tokens to keep in KV cache
        # -1 = keep all (full prompt caching), 0 = disable, N = keep first N tokens
        if use_prompt_cache:
            options["num_keep"] = kwargs.get("num_keep", -1)
        # Early exit on EOS for Ollama (speculative decoding / early exit - Phase 2.5)
        # Union with caller-provided stops instead of overwriting (P1-1 fix).
        # NOTE: never add "\n\n" here — thinking models (qwen3, deepseek-r1)
        # open with "<think>\n\n", so a blank-line stop decapitates every
        # answer to a stub (observed live: qwen3:1.7b → empty content →
        # deterministic ABSTAIN across all recovery retries). It also
        # truncates ordinary multi-paragraph answers mid-way.
        _ollama_stops: list[str] = []
        if early_exit_eos:
            # Real end-of-sequence tokens only.
            _ollama_stops.extend(["<|endoftext|>", "<|eot_id|>"])
        if stop:
            _ollama_stops.extend(stop)
        if _ollama_stops:
            seen = set()
            options["stop"] = [s for s in _ollama_stops if not (s in seen or seen.add(s))]

        requested_model = kwargs.get("model", self.model)
        target_model = requested_model

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": dict_messages,
            "stream": False,
            "options": options,
            # Release GPU memory after idle period
            "keep_alive": kwargs.get("keep_alive", default_keep_alive),
        }

        requested_format = kwargs.get("format", self.format)
        if requested_format:
            payload["format"] = requested_format

        try:
            async with _get_local_llm_semaphore():
                client = _shared_http_client(self.base_url, self.timeout)
                res = await client.post(endpoint, json=payload)
                if res.status_code == 404:
                    with suppress(Exception):
                        tags_res = await client.get(f"{self.base_url.rstrip('/')}/api/tags")
                        if tags_res.is_success:
                            avail = [m.get("name", "") for m in tags_res.json().get("models", [])]
                            prefix = requested_model.split(":")[0]
                            match = next((m for m in avail if m.startswith(prefix)), None)
                            if match:
                                payload["model"] = match
                                res = await client.post(endpoint, json=payload)

            if res.status_code == 404:
                raise ConfigurationError(
                    "Ollama model "
                    f"'{self.model}' not found. Please run 'ollama pull {self.model}' "
                    "in your terminal."
                )
            res.raise_for_status()
            data = res.json()
            content = data.get("message", {}).get("content", "")
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
        except httpx.ConnectError as exc:
            raise ConfigurationError(
                "Cannot connect to Ollama at "
                f"'{self.base_url}'. Is Ollama running? Run 'ollama serve' in your terminal.",
                detail=str(exc),
            ) from exc
        except Exception as exc:
            if isinstance(exc, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Ollama generation failed for model '{self.model}'", detail=str(exc)
            ) from exc

    def with_structured_output(self, schema: type[T], **kwargs: Any) -> Runnable[Any, T]:
        """Prompt for structured JSON and parse into the Pydantic schema."""
        from app.core.llm_utils import build_structured_output_runnable

        return build_structured_output_runnable(
            generate_fn=self._agenerate,
            schema=schema,
            json_format_kwargs={"format": "json"},
            extra_kwargs=kwargs,
        )


# ─── llama.cpp Chat Model ──────────────────────────────────────────────────────


class ChatLlamaCppClient(BaseChatModel):
    """
    Client for llama.cpp HTTP server (llama-server) via its OpenAI-compatible
    /v1/chat/completions API. Also serves Apple MLX (mlx_lm.server), which
    speaks the same protocol — the registry constructs this client for the
    `mlx` provider with the MLX base URL and model id.
    """

    base_url: str = Field(default="http://127.0.0.1:8080/v1")
    model: str = Field(default="occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M")
    temperature: float = Field(default=0.2)
    top_p: float = Field(default=0.9)
    max_tokens: int = Field(default=1024)  # PERF 2026-09-06: lean cap (was 2048)
    timeout: float = Field(default=120.0)
    # Stronger than Ollama's: sub-2B reasoning models readily fall into
    # repeat-until-cap loops on scaffolded prompts.
    repeat_penalty: float = Field(default=1.15)

    @property
    def _llm_type(self) -> str:
        return "llama-cpp-client"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
            )
        raise ConfigurationError(
            "Synchronous llama.cpp generation cannot run inside an active event loop; "
            "use ainvoke() instead."
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        dict_messages = _convert_messages_to_dict(messages)
        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"

        cfg = get_model_config()
        # Use config values with env override, fallback to hardcoded defaults
        default_num_batch = cfg.local_llm_num_batch

        # Optimization flags from models.yaml (Phase 1: wire existing flags)
        kv_cache_quant = cfg.kv_cache_quantization
        use_flash_attn = cfg.flash_attention
        use_prompt_cache = cfg.prompt_caching

        # Speculative Decoding / Early Exit (Phase 2.5)
        min_p = cfg.local_llm_min_p
        top_k = cfg.local_llm_top_k
        early_exit_eos = cfg.local_llm_early_exit_eos

        # num_ctx is advisory for llama.cpp/MLX: the server context is fixed at
        # startup (-c). Log when the request needs more than the server offers.
        requested_num_ctx = kwargs.get("num_ctx", kwargs.get("n_ctx"))
        if requested_num_ctx is not None and int(requested_num_ctx) > cfg.local_llm_num_ctx:
            logger.warning(
                "Requested num_ctx exceeds configured server context",
                requested=requested_num_ctx,
                server_ctx=cfg.local_llm_num_ctx,
            )

        # n_batch / num_batch alias: callers may use either naming.
        requested_batch = kwargs.get("n_batch", kwargs.get("num_batch", default_num_batch))

        # Union early-exit EOS stops with caller-provided stops (P1-1 fix).
        _llama_stops: list[str] = []
        if early_exit_eos:
            _llama_stops.extend(["<|endoftext|>", "<|im_end|>", "</s>"])
        if stop:
            _llama_stops.extend(stop)
        _llama_stops = list(dict.fromkeys(_llama_stops)) or None  # type: ignore[assignment]

        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": dict_messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": False,
            "cache_prompt": use_prompt_cache,
            "repeat_penalty": kwargs.get("repeat_penalty", self.repeat_penalty),
            # llama.cpp-specific: prompt processing batch size (controls KV cache build parallelism)
            "n_batch": requested_batch,
            # KV cache quantization: q4_0, q8_0, fp16 (saves 50-75% context VRAM)
            "cache_type_k": kv_cache_quant,
            "cache_type_v": kv_cache_quant,
            # Flash attention: computes attention in SRAM tiles (O(N) memory)
            "flash_attention": use_flash_attn,
            # Min-p sampling: only tokens with p >= min_p * p_max are considered
            "min_p": min_p if min_p > 0.0 else None,
            # Top-k sampling: restrict to top K tokens
            "top_k": top_k if top_k > 0 else None,
            # Early exit on EOS for n_predict streaming
            "stop": _llama_stops,
        }
        # Clean up None values
        payload = {k: v for k, v in payload.items() if v is not None}

        if kwargs.get("format") == "json" or kwargs.get("response_format"):
            payload["response_format"] = {"type": "json_object"}

        try:
            async with _get_local_llm_semaphore():
                client = _shared_http_client(self.base_url, self.timeout)
                res = await client.post(endpoint, json=payload)
            res.raise_for_status()
            data = res.json()
            choices = data.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
        except httpx.ConnectError as exc:
            raise ConfigurationError(
                f"Cannot connect to llama.cpp server at '{self.base_url}'. "
                f"Ensure 'llama-server' is running on port 8080 or your configured URL.",
                detail=str(exc),
            ) from exc
        except Exception as exc:
            if isinstance(exc, ConfigurationError):
                raise
            raise ConfigurationError(
                f"llama.cpp generation failed for model '{self.model}'", detail=str(exc)
            ) from exc

    def with_structured_output(self, schema: type[T], **kwargs: Any) -> Runnable[Any, T]:
        """Return a Runnable prompting llama.cpp for structured JSON, parsed into Pydantic."""
        from app.core.llm_utils import build_structured_output_runnable

        return build_structured_output_runnable(
            generate_fn=self._agenerate,
            schema=schema,
            json_format_kwargs={"response_format": {"type": "json_object"}},
            extra_kwargs=kwargs,
        )


# ─── Health & CLI Model Discovery Helpers ─────────────────────────────────────


# ─── CLI model discovery (LLM-only) ────────────────────────────────────────────
# NOTE: embedding models are intentionally EXCLUDED everywhere here.
# `ollama list` feeds the Ollama LLM selector, `llama-server --cache-list` feeds
# the llama.cpp LLM selector. Embeddings are fixed via EMBEDDING_* env / models.yaml
# and pinned per-KB at ingest — never user-selected per request.

# ─── Runtime model discovery cache ────────────────────────────────────────────
# Only models actually discovered via `ollama list` and `llama-server --cache-list`
# are cached here. No hardcoded fallbacks — the UI should only show models
# actually installed on the user's system.
_DISCOVERED_LLMS: dict[str, set[str]] = {}
_DISCOVERED_LLMS_LOCK = threading.Lock()


def merge_discovered_llms(provider: str, models: list[str], replace: bool = False) -> None:
    """Cache live-discovered GENERATIVE model ids for a local provider.

    With ``replace=True`` the bucket is replaced by the fresh authoritative
    list (used when live CLI/API discovery succeeded) so uninstalled models
    stop being offered. An empty fresh list never wipes the cache — a
    transient discovery failure must not break in-flight request validation.
    """
    clean = [m for m in models if m and not _is_embedding_model_name(m)]
    if not clean:
        return
    with _DISCOVERED_LLMS_LOCK:
        if replace:
            _DISCOVERED_LLMS[provider] = set(clean)
        else:
            bucket = _DISCOVERED_LLMS.setdefault(provider, set())
            bucket.update(clean)


# ─── Resilient local-server HTTP ──────────────────────────────────────────────
# A single 3 s sample on a busy 8 GB host is a coin flip: the server can be
# alive yet miss one probe (cold model, full accept backlog), which used to
# 503 the whole analysis and flap the UI's connected pill on every 8 s poll.
# Every probe/status GET below retries once, and connection-refused (server
# down) stays distinct from timeout (server slow) so each gets the right
# message and the right recovery.
PROBE_TIMEOUT_SECONDS = 3.0
PROBE_ATTEMPTS = 2


async def _fetch_json_with_retry(
    url: str, timeout: float = PROBE_TIMEOUT_SECONDS, attempts: int = PROBE_ATTEMPTS
) -> httpx.Response:
    """GET with one retry. Only connection/timeout errors retry — HTTP errors
    (e.g. 500s) return normally for the caller to interpret."""
    last_exc: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                return await client.get(url)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            logger.debug("Local-server HTTP attempt failed, retrying", url=url)
    assert last_exc is not None
    raise last_exc


async def probe_local_llm_server(provider: str, base_url: str, timeout: float = 3.0) -> None:
    """Fail fast when a local inference server is not running.

    Raises LLMUnavailableError with copy-paste start instructions instead of
    letting an analysis burn minutes of timeouts before abstaining. Only the
    configured base URL is echoed (no secrets); transport details stay in logs.
    Connection-refused means down (start it); timeout means slow/overloaded
    (wait and retry) — conflating them sent users restarting a live server.
    """
    norm = (provider or "").strip().lower()
    base = (base_url or "").rstrip("/")
    if norm == "ollama":
        probe_url = f"{base}/api/tags"
        start_hint = "Start it with 'ollama serve' (then 'ollama pull <model>' if needed)."
    elif norm == "mlx":
        probe_url = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
        start_hint = (
            "Start it with 'mlx_lm.server --model <mlx-community/...-4bit>' "
            "(Apple Silicon only; pip install mlx-lm)."
        )
    else:
        probe_url = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
        start_hint = "Start it with './scripts/start_local_llm.sh' (llama-server on :8080)."
    try:
        res = await _fetch_json_with_retry(probe_url, timeout=timeout)
        if res.status_code >= 500:
            raise LLMUnavailableError(
                f"Local LLM server '{norm}' at {base} returned HTTP {res.status_code}. {start_hint}"
            )
    except LLMUnavailableError:
        raise
    except httpx.ConnectError as exc:
        logger.warning("Local LLM server probe failed", provider=norm, base_url=base)
        raise LLMUnavailableError(
            f"Local LLM server '{norm}' is not reachable at {base}. {start_hint}"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.warning("Local LLM server probe timed out", provider=norm, base_url=base)
        raise LLMUnavailableError(
            f"Local LLM server '{norm}' at {base} is not answering "
            f"(timed out after {PROBE_ATTEMPTS} attempts). It may be starting "
            f"up or overloaded — wait a few seconds and retry. {start_hint}"
        ) from exc
    except Exception as exc:
        logger.warning("Local LLM server probe failed", provider=norm, base_url=base)
        raise LLMUnavailableError(
            f"Local LLM server '{norm}' is not reachable at {base}. {start_hint}"
        ) from exc


# ─── Cloud-model preflight ──────────────────────────────────────────────────
# A stalled cloud model (observed: nvidia/nemotron-3.5-lightning-30b-a3b
# returning zero bytes indefinitely) otherwise burns the full per-call
# timeout across every sequential pipeline call before abstaining. One tiny
# completion up front converts that into a fast 503 with an actionable
# message. Gemini answers the same probe in seconds.
CLOUD_PROBE_TIMEOUT_SECONDS = 60.0


async def probe_cloud_llm(
    provider: str, model: str | None, timeout: float = CLOUD_PROBE_TIMEOUT_SECONDS
) -> None:
    """Fail fast when a cloud chat model (nvidia, gemini) is not responding.

    Sends a minimal 8-token completion bounded by ``timeout``. Raises
    LLMUnavailableError (→ 503) on stall/unreachable; lets ConfigurationError
    (missing API key) propagate unchanged — it already names the fix.

    Args:
        provider: 'nvidia'/'nim' or 'gemini'/'google_genai'.
        model: Explicit model id (already resolved by the caller).
        timeout: Probe budget in seconds. 60s distinguishes a dead endpoint
            (no first byte) from a merely slow one.
    """
    from app.core.model_registry import get_llm  # lazy: avoids import cycle

    norm = (provider or "").strip().lower()
    hint = (
        "The model endpoint may be capacity-limited — retry in a few minutes, "
        "or switch provider (gemini, ollama, llama_cpp)."
    )
    try:
        llm = get_llm(provider=norm, model=model)
    except ConfigurationError:
        raise
    except Exception as exc:
        logger.warning("Cloud LLM probe: model init failed", provider=norm, model=model)
        raise LLMUnavailableError(
            f"Cloud LLM '{norm}' model '{model}' could not be initialized. {hint}"
        ) from exc

    # Provider-correct output cap (mirrors generator._invoke_kwargs_for_provider).
    cap = {"max_output_tokens": 8} if norm in ("gemini", "google_genai") else {"max_tokens": 8}
    try:
        await asyncio.wait_for(llm.ainvoke("Reply with the word OK.", **cap), timeout=timeout)
    except TimeoutError as exc:  # asyncio.wait_for raises builtin TimeoutError (3.11+)
        logger.warning("Cloud LLM probe timed out", provider=norm, model=model, timeout=timeout)
        raise LLMUnavailableError(
            f"Cloud LLM '{norm}' model '{model}' is not responding "
            f"(no output after {timeout:g}s). {hint}"
        ) from exc
    except LLMUnavailableError:
        raise
    except ConfigurationError:
        raise
    except Exception as exc:
        logger.warning("Cloud LLM probe failed", provider=norm, model=model)
        raise LLMUnavailableError(
            f"Cloud LLM '{norm}' model '{model}' is not reachable. {hint}"
        ) from exc


def get_discovered_llms(provider: str) -> frozenset[str]:
    """Return cached live-discovered model ids for a provider (empty if unknown)."""
    with _DISCOVERED_LLMS_LOCK:
        return frozenset(_DISCOVERED_LLMS.get(provider, set()))


# ─── Discovery snapshot (cross-process seeding) ──────────────────────────────
# The discovery cache above is in-memory per process. A process started later
# (e.g. the backend after scripts/discover_local_models.py) re-seeds from this
# JSON snapshot so a pre-run discovery script actually warms the server.
_DISCOVERY_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "discovered_models.json"

_EMBEDDING_NAME_KEYWORDS = (
    "embed",
    "bge",
    "nomic",
    "minilm",
    "gte",
    "mxbai",
    "snowflake",
    "arctic-embed",
    "e5-",
    "e5_",
    "/e5",
)


def _is_embedding_model_name(name: str) -> bool:
    return any(kw in name.lower() for kw in _EMBEDDING_NAME_KEYWORDS)


def save_discovery_snapshot() -> None:
    """Persist the current discovered-model cache for later processes."""
    with _DISCOVERED_LLMS_LOCK:
        payload = {
            "providers": {
                provider: sorted(models) for provider, models in _DISCOVERED_LLMS.items()
            },
        }
    try:
        _DISCOVERY_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write (tmp + rename) so concurrent seeders never interleave.
        tmp_path = _DISCOVERY_SNAPSHOT_PATH.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(_DISCOVERY_SNAPSHOT_PATH)
        logger.debug("Persisted model discovery snapshot", path=str(_DISCOVERY_SNAPSHOT_PATH))
    except Exception as exc:
        logger.debug("Failed to persist model discovery snapshot", error=str(exc))


def load_discovery_snapshot() -> None:
    """Seed the in-process discovery cache from a previously-persisted snapshot."""
    try:
        data = json.loads(_DISCOVERY_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except Exception as exc:
        logger.debug("Failed to load model discovery snapshot", error=str(exc))
        return
    providers = data.get("providers", {}) if isinstance(data, dict) else {}
    for provider, models in providers.items():
        if isinstance(models, list):
            merge_discovered_llms(str(provider), [str(m) for m in models])


# Load snapshot at module import so any process gets cached models
load_discovery_snapshot()


async def seed_local_model_discovery() -> dict[str, list[str]]:
    """
    Discover locally-installed GENERATIVE models and warm the shared cache.

    Sources (CLI-only, no server dependency):
      - ollama    -> `ollama list`
      - llama_cpp -> `llama-server --cache-list`
      - mlx       -> HuggingFace hub scan for `mlx-community` / `*mlx*` weights

    Loads any previously-persisted snapshot, refreshes the in-process cache from
    the live CLIs, then persists the result so a backend started later seeds
    identically. Runs at API startup and standalone via scripts/discover_local_models.py.
    """
    load_discovery_snapshot()

    ollama_models = [
        m for m in await discover_ollama_cli_models() if not _is_embedding_model_name(m)
    ]
    llamacpp_models = [
        m for m in await discover_llamacpp_cache_models() if not _is_embedding_model_name(m)
    ]
    mlx_models = [m for m in discover_mlx_cache_models() if not _is_embedding_model_name(m)]

    merge_discovered_llms("ollama", ollama_models)
    merge_discovered_llms("llama_cpp", llamacpp_models)
    merge_discovered_llms("mlx", mlx_models)
    save_discovery_snapshot()

    return {"ollama": ollama_models, "llama_cpp": llamacpp_models, "mlx": mlx_models}


async def discover_ollama_cli_models() -> list[str]:
    """
    Run 'ollama list' CLI and return installed GENERATIVE model names only.
    Embedding models are filtered out — they are not selectable LLMs.
    """
    llm_models: list[str] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama",
            "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
        except TimeoutError:
            with suppress(Exception):
                proc.kill()
                await proc.wait()
            raise
        if proc.returncode == 0:
            lines = stdout.decode().strip().split("\n")
            for line in lines[1:]:  # skip header
                parts = line.split()
                if parts and not _is_embedding_model_name(parts[0]):
                    llm_models.append(parts[0])
    except Exception as exc:
        logger.debug("Failed to run 'ollama list' CLI", error=str(exc))

    return llm_models


async def discover_llamacpp_cache_models() -> list[str]:
    """
    Run 'llama-server --cache-list' CLI and return cached GENERATIVE model IDs only.
    Embedding GGUFs are filtered out — they are not selectable LLMs.
    """
    cache_models: list[str] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "llama-server",
            "--cache-list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
        except TimeoutError:
            with suppress(Exception):
                proc.kill()
                await proc.wait()
            raise
        if proc.returncode == 0:
            lines = stdout.decode().strip().split("\n")
            for line in lines:
                match = re.search(r"^\s*\d+\.\s*(.+)$", line)
                if match:
                    name = match.group(1).strip()
                    if not _is_embedding_model_name(name):
                        cache_models.append(name)
    except Exception as exc:
        logger.debug("Failed to run 'llama-server --cache-list' CLI", error=str(exc))

    return cache_models


def discover_hf_hub_gguf_models() -> list[str]:
    """Scan local HuggingFace cache for any downloaded GGUF blobs or models."""
    gguf_models: list[str] = []
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        for model_dir in hf_cache.glob("models--*"):
            dir_name = model_dir.name.replace("models--", "").replace("--", "/")
            if "gguf" in dir_name.lower():
                gguf_models.append(dir_name)
    return gguf_models


def discover_mlx_cache_models() -> list[str]:
    """Scan the local HuggingFace cache for downloaded MLX weights.

    MLX models ship as `.safetensors` (not GGUF), so the GGUF scan misses
    them. Matches `mlx-community` builds and any repo id containing `mlx`
    (case-insensitive); embedding models are filtered out by callers.
    Apple Silicon only — elsewhere the cache simply won't contain any.
    """
    mlx_models: list[str] = []
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        for model_dir in hf_cache.glob("models--*"):
            dir_name = model_dir.name.replace("models--", "").replace("--", "/")
            if "mlx" in dir_name.lower() and "gguf" not in dir_name.lower():
                mlx_models.append(dir_name)
    return sorted(set(mlx_models))


async def check_ollama_status(base_url: str = "http://localhost:11434") -> dict[str, Any]:
    """
    Discover Ollama status and GENERATIVE models via 'ollama list' CLI + HTTP API.
    Embedding models are excluded — embeddings are not selected per request.
    Only models actually installed on the system are returned.
    """
    endpoint = f"{base_url.rstrip('/')}/api/tags"
    cli_llms = [m for m in await discover_ollama_cli_models() if not _is_embedding_model_name(m)]

    api_models: list[str] = []
    connected = False
    try:
        res = await _fetch_json_with_retry(endpoint)
        if res.status_code == 200:
            connected = True
            data = res.json()
            api_models = [m.get("name") for m in data.get("models", []) if m.get("name")]
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.debug("Ollama HTTP check failed", error=str(exc))

    # Only use models actually discovered via CLI or API.
    # Ollama serves every pulled model on demand, so the CLI+API union is
    # exactly the servable set (unlike llama-server, which serves one model).
    all_llms = list(
        dict.fromkeys(cli_llms + [m for m in api_models if not _is_embedding_model_name(m)])
    )

    # If CLI succeeded, Ollama daemon is installed and active
    if cli_llms:
        connected = True

    # Default to gemma3:1b if discovered, else first discovered
    default_model = "gemma3:1b" if "gemma3:1b" in all_llms else (all_llms[0] if all_llms else "")
    merge_discovered_llms("ollama", all_llms, replace=True)

    return {
        "connected": connected,
        "provider": "ollama",
        "base_url": base_url,
        "models": all_llms,
        "default_model": default_model,
    }


async def check_llamacpp_status(base_url: str = "http://127.0.0.1:8080/v1") -> dict[str, Any]:
    """
    Discover llama.cpp status and GENERATIVE models via 'llama-server --cache-list',
    HTTP /v1/models endpoint, and local HuggingFace cache. Embedding GGUFs excluded.
    Only models actually installed on the system are returned.
    """
    endpoint = f"{base_url.rstrip('/')}/models"
    cache_models = await discover_llamacpp_cache_models()
    hf_models = discover_hf_hub_gguf_models()

    api_models: list[str] = []
    connected = False
    try:
        res = await _fetch_json_with_retry(endpoint)
        if res.status_code == 200:
            connected = True
            data = res.json()
            api_models = [m.get("id") for m in data.get("data", []) if m.get("id")]
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.debug("llama.cpp HTTP check failed", error=str(exc))

    # llama-server serves ONLY the model(s) passed via --model (reported by
    # /v1/models). Cached/HF blobs are NOT servable until loaded, so when the
    # server is connected the selector lists exactly the API set — otherwise
    # users pick phantom models that fail at generation time. Offline, fall
    # back to the cache/HF union so the UI still shows what can be started.
    api_llms = [m for m in api_models if not _is_embedding_model_name(m)]
    if connected and api_llms:
        combined = list(dict.fromkeys(api_llms))
    else:
        # The HF-hub scan returns bare repo ids (`org/model-GGUF`) while the
        # server and cache-list return quantified ids (`org/model-GGUF:Q4_K_M`)
        # for the same weights — drop the bare form when a quantified sibling
        # is listed so the selector never shows one model twice. Also dedup
        # across cache vs HF when the same GGUF id appears in both sources.
        quantified_bases = {m.split(":")[0] for m in api_models + cache_models if ":" in m}
        hf_llms = [
            m
            for m in hf_models
            if not _is_embedding_model_name(m) and (":" in m or m not in quantified_bases)
        ]
        combined = list(dict.fromkeys(api_llms + cache_models + hf_llms))

    # Default to LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M if discovered, else first discovered
    default_model = (
        "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M"
        if "LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M" in combined
        else (combined[0] if combined else "")
    )

    merge_discovered_llms("llama_cpp", combined, replace=True)

    return {
        "connected": connected,
        "provider": "llama_cpp",
        "base_url": base_url,
        "models": combined,
        "cache_models": cache_models,
        "default_model": default_model,
    }


async def check_mlx_status(
    base_url: str = "http://127.0.0.1:8090/v1", max_ports: int = 5
) -> dict[str, Any]:
    """
    Discover MLX status and GENERATIVE models by checking multiple MLX server ports.
    MLX only supports 1 model per server, so we check ports 8090, 8091, 8092...
    and aggregate all discovered models for UI selection.
    """
    cache_models = discover_mlx_cache_models()

    all_api_models: list[str] = []
    any_connected = False

    # Check consecutive ports starting from base_url port
    import re

    base_port_match = re.search(r":(\d+)", base_url)
    start_port = int(base_port_match.group(1)) if base_port_match else 8090

    for port_offset in range(max_ports):
        port = start_port + port_offset
        endpoint = f"http://127.0.0.1:{port}/v1/models"

        try:
            res = await _fetch_json_with_retry(endpoint)
            if res.status_code == 200:
                any_connected = True
                data = res.json()
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                all_api_models.extend(models)
        except (httpx.ConnectError, httpx.TimeoutException):
            continue

    api_llms = [m for m in all_api_models if not _is_embedding_model_name(m)]

    # MLX server serves ONLY the model(s) passed via --model (reported by
    # /v1/models). Cached/HF blobs are NOT servable until loaded, so when the
    # server is connected the selector lists exactly the API set — otherwise
    # users pick phantom models that fail at generation time.
    if any_connected and api_llms:
        combined = list(dict.fromkeys(api_llms))
    else:
        # Combine API-discovered + cached (deduplicated) when server is not connected
        combined = list(dict.fromkeys(api_llms + cache_models))

    default_model = (
        "mlx-community/Llama-3.2-1B-Instruct-4bit"
        if "mlx-community/Llama-3.2-1B-Instruct-4bit" in combined
        else (combined[0] if combined else "")
    )

    merge_discovered_llms("mlx", combined, replace=True)

    return {
        "connected": any_connected,
        "provider": "mlx",
        "base_url": base_url,
        "models": combined,
        "cache_models": cache_models,
        "default_model": default_model,
    }
