"""
TRUSTRAG — Local LLM Client implementations for Ollama and llama.cpp.

Provides first-class LangChain BaseChatModel interfaces with zero native
compilation dependencies by communicating directly with Ollama's local REST API
and llama.cpp's OpenAI-compatible server API via async httpx.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
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

from app.core.exceptions import ConfigurationError, LLMUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Reuse HTTP connections for the Ollama/llama.cpp request fan-out. One analysis
# can perform generation, decomposition, batch NLI, fallback NLI, and recovery;
# per-call clients previously discarded keep-alive connections every time.
_HTTP_CLIENTS: dict[tuple[str, float, int], httpx.AsyncClient] = {}
_HTTP_CLIENTS_LOCK = threading.Lock()

# OPT (local-LLM load): local inference servers are serial (llama-server -np 2,
# Ollama default queue). Without an LLM-level semaphore, 2 concurrent analyses
# x ~9 sequential calls pile up into timeout cascades. Serialize local
# generations here; the analysis-level semaphore in analysis_service.py is
# per-process and too coarse to protect the single inference server.
_LOCAL_LLM_SEMAPHORE = asyncio.Semaphore(int(os.getenv("LOCAL_LLM_MAX_CONCURRENCY", "1")))


def _shared_http_client(base_url: str, timeout: float) -> httpx.AsyncClient:
    """Return a per-event-loop, per-endpoint pooled AsyncClient."""
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = 0
    key = (base_url.rstrip("/"), float(timeout), loop_id)
    with _HTTP_CLIENTS_LOCK:
        client = _HTTP_CLIENTS.get(key)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(timeout=timeout)
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


T = TypeVar("T", bound=BaseModel)

# Providers served by a local inference process (single-tenant, serial).
# Output caps and concurrency guards apply ONLY here — cloud chat models use
# different parameter names (e.g. max_output_tokens) and must not receive ours.
LOCAL_LLM_PROVIDERS = frozenset({"ollama", "llama_cpp", "llamacpp"})


def local_cap_kwargs(provider: str | None, max_tokens: int) -> dict[str, int]:
    """Task-sized output caps for local inference servers only.

    A rewrite needs ~20 words, a single NLI verdict ~100 tokens — letting them
    inherit the 1024-token default grows per-call KV cache and wall time for
    nothing. Returns {} for cloud providers (foreign parameter names).
    """
    if (provider or "").strip().lower() in LOCAL_LLM_PROVIDERS:
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

        options: dict[str, Any] = {
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            # OPT (local-LLM load): 2048 overflowed with 3000-char contexts +
            # system prompt and produced truncated stubs. 4096 matches
            # llama-server -c 4096 and fits the reduced context budget.
            "num_ctx": kwargs.get("num_ctx", 4096),
            "num_predict": kwargs.get("max_tokens", 1024),
            "repeat_penalty": kwargs.get("repeat_penalty", self.repeat_penalty),
        }
        if stop:
            options["stop"] = stop

        requested_model = kwargs.get("model", self.model)
        target_model = requested_model

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": dict_messages,
            "stream": False,
            "options": options,
            "keep_alive": kwargs.get("keep_alive", "5m"),  # Release GPU memory after 5 min idle
        }

        requested_format = kwargs.get("format", self.format)
        if requested_format:
            payload["format"] = requested_format

        try:
            async with _LOCAL_LLM_SEMAPHORE:
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
    /v1/chat/completions API.
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

        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": dict_messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": False,
            "cache_prompt": True,
            "repeat_penalty": kwargs.get("repeat_penalty", self.repeat_penalty),
        }
        if stop:
            payload["stop"] = stop

        if kwargs.get("format") == "json" or kwargs.get("response_format"):
            payload["response_format"] = {"type": "json_object"}

        try:
            async with _LOCAL_LLM_SEMAPHORE:
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


async def probe_local_llm_server(provider: str, base_url: str, timeout: float = 3.0) -> None:
    """Fail fast when a local inference server is not running.

    Raises LLMUnavailableError with copy-paste start instructions instead of
    letting an analysis burn minutes of timeouts before abstaining. Only the
    configured base URL is echoed (no secrets); transport details stay in logs.
    """
    norm = (provider or "").strip().lower()
    base = (base_url or "").rstrip("/")
    if norm == "ollama":
        probe_url = f"{base}/api/tags"
        start_hint = "Start it with 'ollama serve' (then 'ollama pull <model>' if needed)."
    else:
        probe_url = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
        start_hint = "Start it with './scripts/start_local_llm.sh' (llama-server on :8080)."
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.get(probe_url)
        if res.status_code >= 500:
            raise LLMUnavailableError(
                f"Local LLM server '{norm}' at {base} returned HTTP {res.status_code}. {start_hint}"
            )
    except LLMUnavailableError:
        raise
    except Exception as exc:
        logger.warning("Local LLM server probe failed", provider=norm, base_url=base)
        raise LLMUnavailableError(
            f"Local LLM server '{norm}' is not reachable at {base}. {start_hint}"
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
        _DISCOVERY_SNAPSHOT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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


async def seed_local_model_discovery() -> dict[str, list[str]]:
    """
    Discover locally-installed GENERATIVE models and warm the shared cache.

    Sources (CLI-only, no server dependency):
      - ollama    -> `ollama list`
      - llama_cpp -> `llama-server --cache-list`

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

    merge_discovered_llms("ollama", ollama_models)
    merge_discovered_llms("llama_cpp", llamacpp_models)
    save_discovery_snapshot()

    return {"ollama": ollama_models, "llama_cpp": llamacpp_models}


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
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(endpoint)
            if res.status_code == 200:
                connected = True
                data = res.json()
                api_models = [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception as exc:
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
    default_model = (
        "gemma3:1b"
        if "gemma3:1b" in all_llms
        else (all_llms[0] if all_llms else "")
    )
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
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(endpoint)
            if res.status_code == 200:
                connected = True
                data = res.json()
                api_models = [m.get("id") for m in data.get("data", []) if m.get("id")]
    except Exception as exc:
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
