"""
TRUSTRAG — Local LLM Client implementations for Ollama and llama.cpp.

Provides first-class LangChain BaseChatModel interfaces with zero native
compilation dependencies by communicating directly with Ollama's local REST API
and llama.cpp's OpenAI-compatible server API via async httpx.
"""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress
from pathlib import Path
from typing import Any, TypeVar

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel, Field

from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


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
    return converted


def _extract_json_substring(text: str) -> str:
    """Safely extract valid JSON payload from an LLM output string."""
    cleaned = text.strip()
    # Strip markdown code blocks if wrapped
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()

    # If starts with '{' or '[', find matching closing bracket
    start_brace = cleaned.find("{")
    start_bracket = cleaned.find("[")

    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        end_brace = cleaned.rfind("}")
        if end_brace != -1 and end_brace > start_brace:
            return cleaned[start_brace : end_brace + 1]
    elif start_bracket != -1:
        end_bracket = cleaned.rfind("]")
        if end_bracket != -1 and end_bracket > start_bracket:
            return cleaned[start_bracket : end_bracket + 1]

    return cleaned


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
        import asyncio

        return asyncio.run(self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs))

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
            # PERF 2026-09-06 (lean 8GB hosts): 2k context halves the Ollama
            # KV-cache on unified memory; 1k token cap stops runaway
            # generations (up to 9 LLM calls per analysis with recovery).
            "num_ctx": kwargs.get("num_ctx", 2048),
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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
        """
        Return a Runnable that prompts for structured JSON and parses into the Pydantic schema.
        """
        schema_dict = schema.model_json_schema()
        schema_json = json.dumps(schema_dict, indent=2)
        props = schema_dict.get("properties", {})
        template = {k: f"<{v.get('type', 'value')}>" for k, v in props.items()}
        template_str = json.dumps(template)

        async def _invoke_structured(input_messages: Any) -> T:
            # Ensure input messages list
            if isinstance(input_messages, (str, BaseMessage, tuple)):
                msgs = [input_messages]
            else:
                msgs = list(input_messages)

            # Append instruction for JSON conforming to schema
            instruction = (
                f"\n\nYou MUST respond ONLY with valid JSON using the keys {list(props.keys())}.\n"
                f"Required JSON structure:\n{template_str}\n"
                f"Full schema reference:\n{schema_json}\n"
                "Return raw JSON only, without markdown fences, explanation, "
                "or meta-schema wrapper."
            )

            # Append to last message or add new human message
            augmented_messages = list(msgs)
            if augmented_messages:
                last = augmented_messages[-1]
                if isinstance(last, tuple) and len(last) == 2:
                    augmented_messages[-1] = (last[0], f"{last[1]}{instruction}")
                elif isinstance(last, HumanMessage):
                    augmented_messages[-1] = HumanMessage(content=f"{last.content}{instruction}")
                else:
                    augmented_messages.append(HumanMessage(content=instruction))
            else:
                augmented_messages.append(HumanMessage(content=instruction))

            # Invoke model with format="json"
            result = await self._agenerate(augmented_messages, format="json", **kwargs)
            raw_text = result.generations[0].message.content
            cleaned_json = _extract_json_substring(raw_text)

            try:
                return schema.model_validate_json(cleaned_json)
            except Exception as parse_err:
                logger.warning(
                    "JSON schema parsing failed, attempting repair",
                    raw=raw_text[:200],
                    error=str(parse_err),
                )
                try:
                    data = json.loads(cleaned_json)
                    if isinstance(data, dict):
                        # 1. Check if model wrapped inside "properties" (common with small LLMs)
                        if "properties" in data and isinstance(data["properties"], dict):
                            with suppress(Exception):
                                return schema.model_validate(data["properties"])
                        # 2. Check if model wrapped inside another sub-dict
                        for v in data.values():
                            if isinstance(v, dict):
                                with suppress(Exception):
                                    return schema.model_validate(v)
                    return schema.model_validate(data)
                except Exception:
                    raise parse_err from None

        return RunnableLambda(_invoke_structured)  # type: ignore[return-value]


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
        import asyncio

        return asyncio.run(self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs))

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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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
        """
        Return a Runnable prompting llama.cpp for structured JSON, parsed into Pydantic.
        """
        schema_dict = schema.model_json_schema()
        schema_json = json.dumps(schema_dict, indent=2)
        props = schema_dict.get("properties", {})
        template = {k: f"<{v.get('type', 'value')}>" for k, v in props.items()}
        template_str = json.dumps(template)

        async def _invoke_structured(input_messages: Any) -> T:
            if isinstance(input_messages, (str, BaseMessage, tuple)):
                msgs = [input_messages]
            else:
                msgs = list(input_messages)

            instruction = (
                f"\n\nYou MUST respond ONLY with valid JSON using the keys {list(props.keys())}.\n"
                f"Required JSON structure:\n{template_str}\n"
                f"Full schema reference:\n{schema_json}\n"
                "Return raw JSON only, without markdown fences, explanation, "
                "or meta-schema wrapper."
            )

            augmented_messages = list(msgs)
            if augmented_messages:
                last = augmented_messages[-1]
                if isinstance(last, tuple) and len(last) == 2:
                    augmented_messages[-1] = (last[0], f"{last[1]}{instruction}")
                elif isinstance(last, HumanMessage):
                    augmented_messages[-1] = HumanMessage(content=f"{last.content}{instruction}")
                else:
                    augmented_messages.append(HumanMessage(content=instruction))
            else:
                augmented_messages.append(HumanMessage(content=instruction))

            result = await self._agenerate(
                augmented_messages, response_format={"type": "json_object"}, **kwargs
            )
            raw_text = result.generations[0].message.content
            cleaned_json = _extract_json_substring(raw_text)

            try:
                return schema.model_validate_json(cleaned_json)
            except Exception as parse_err:
                logger.warning(
                    "llama.cpp JSON schema validation failed, attempting parse",
                    raw=raw_text[:200],
                    error=str(parse_err),
                )
                try:
                    data = json.loads(cleaned_json)
                    if isinstance(data, dict):
                        if "properties" in data and isinstance(data["properties"], dict):
                            with suppress(Exception):
                                return schema.model_validate(data["properties"])
                        for v in data.values():
                            if isinstance(v, dict):
                                with suppress(Exception):
                                    return schema.model_validate(v)
                    return schema.model_validate(data)
                except Exception:
                    raise parse_err from None

        return RunnableLambda(_invoke_structured)  # type: ignore[return-value]


# ─── Health & CLI Model Discovery Helpers ─────────────────────────────────────


# ─── CLI model discovery (LLM-only) ────────────────────────────────────────────
# NOTE: embedding models are intentionally EXCLUDED everywhere here.
# `ollama list` feeds the Ollama LLM selector, `llama-server --cache-list` feeds
# the llama.cpp LLM selector. Embeddings are fixed via EMBEDDING_* env / models.yaml
# and pinned per-KB at ingest — never user-selected per request.

# ─── Canonical installed-model sets ──────────────────────────────────────────
# The ONLY hardcoded local model ids in the backend. These seed offline
# display and merge with live `ollama list` / `llama-server --cache-list` /
# /v1/models output at runtime — prune here when a model is deleted locally.
# Cloud (gemini/nvidia) ids are API-side and live in models.py, not here.
INSTALLED_OLLAMA_LLMS = [
    "granite4.2:3b-q4_K_M",
    "gemma3:1b",
]

INSTALLED_LLAMACPP_LLMS = [
    "occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M",
    "occ-ai/OCC-RAG-0.6B-GGUF:Q4_K_M",
    "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M",
    "ibm-granite/granite-4.0-h-1b-GGUF:Q4_K_M",
]

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
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
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
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
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

    # Canonical installed set seeds the list; live CLI/API results merge below.
    primary_ollama_llms = list(INSTALLED_OLLAMA_LLMS)

    # Merge models preserving order with primary models at the top
    all_llms = list(
        dict.fromkeys(
            primary_ollama_llms
            + cli_llms
            + [m for m in api_models if not _is_embedding_model_name(m)]
        )
    )

    # If CLI succeeded, Ollama daemon is installed and active
    if cli_llms:
        connected = True

    default_model = "granite4.2:3b-q4_K_M" if "granite4.2:3b-q4_K_M" in all_llms else all_llms[0]

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

    primary_llamacpp_llms = list(INSTALLED_LLAMACPP_LLMS)

    # The HF-hub scan returns bare repo ids (`org/model-GGUF`) while the server
    # and cache-list return quantified ids (`org/model-GGUF:Q4_K_M`) for the
    # same weights — drop the bare form when a quantified sibling is listed so
    # the selector never shows one model twice.
    quantified_bases = {m.split(":")[0] for m in (*primary_llamacpp_llms, *api_models) if ":" in m}
    hf_llms = [
        m
        for m in hf_models
        if not _is_embedding_model_name(m) and (":" in m or m not in quantified_bases)
    ]

    combined = list(
        dict.fromkeys(
            primary_llamacpp_llms
            + [m for m in api_models if not _is_embedding_model_name(m)]
            + cache_models
            + hf_llms
        )
    )
    default_model = (
        "occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M"
        if "occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M" in combined
        else (
            "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M"
            if "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M" in combined
            else combined[0]
        )
    )

    return {
        "connected": connected,
        "provider": "llama_cpp",
        "base_url": base_url,
        "models": combined,
        "cache_models": cache_models,
        "default_model": default_model,
    }
