"""
TRUSTRAG — Local LLM Client implementations for Ollama and llama.cpp.

Provides first-class LangChain BaseChatModel interfaces with zero native
compilation dependencies by communicating directly with Ollama's local REST API
and llama.cpp's OpenAI-compatible server API via async httpx.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
from collections.abc import Iterator
from typing import Any, Callable, TypeVar

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
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
            role_norm = "assistant" if role in ("ai", "assistant") else ("system" if role == "system" else "user")
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
            converted.append({
                "role": str(m.get("role", "user")),
                "content": str(m.get("content", "")),
            })
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
    model: str = Field(default="gemma4:e2b")
    temperature: float = Field(default=0.2)
    top_p: float = Field(default=0.9)
    timeout: float = Field(default=120.0)
    format: str | None = Field(default=None)

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
            "num_ctx": kwargs.get("num_ctx", 4096),  # Limit KV-cache to 4k tokens to prevent memory bloat
            "num_predict": kwargs.get("max_tokens", 2048),
        }
        if stop:
            options["stop"] = stop

        requested_model = kwargs.get("model", self.model)
        target_model = "gemma4:e2b-it-qat" if requested_model in ("gemma4:e2b", "gemma4") else requested_model

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
                    try:
                        tags_res = await client.get(f"{self.base_url.rstrip('/')}/api/tags")
                        if tags_res.is_success:
                            avail = [m.get("name", "") for m in tags_res.json().get("models", [])]
                            prefix = requested_model.split(":")[0]
                            match = next((m for m in avail if m.startswith(prefix)), None)
                            if match:
                                payload["model"] = match
                                res = await client.post(endpoint, json=payload)
                    except Exception:
                        pass

                if res.status_code == 404:
                    raise ConfigurationError(
                        f"Ollama model '{self.model}' not found. Please run 'ollama pull {self.model}' in your terminal."
                    )
                res.raise_for_status()
                data = res.json()
                content = data.get("message", {}).get("content", "")
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=content))]
                )
        except httpx.ConnectError as exc:
            raise ConfigurationError(
                f"Cannot connect to Ollama at '{self.base_url}'. Is Ollama running? Run 'ollama serve' in your terminal.",
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
        Return a Runnable that prompts for structured JSON and parses into the given Pydantic schema.
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
                "Return raw JSON only, without markdown fences, explanation, or meta-schema wrapper."
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
                            try:
                                return schema.model_validate(data["properties"])
                            except Exception:
                                pass
                        # 2. Check if model wrapped inside another sub-dict
                        for v in data.values():
                            if isinstance(v, dict):
                                try:
                                    return schema.model_validate(v)
                                except Exception:
                                    pass
                    return schema.model_validate(data)
                except Exception:
                    raise parse_err

        return RunnableLambda(_invoke_structured)  # type: ignore[return-value]


# ─── llama.cpp Chat Model ──────────────────────────────────────────────────────


class ChatLlamaCppClient(BaseChatModel):
    """
    Client for llama.cpp HTTP server (llama-server) using its OpenAI-compatible /v1/chat/completions API.
    """

    base_url: str = Field(default="http://localhost:8081/v1")
    model: str = Field(default="gemma-4-E2B-it-qat-q4_0-gguf:Q4_0")
    temperature: float = Field(default=0.2)
    top_p: float = Field(default=0.9)
    max_tokens: int = Field(default=2048)
    timeout: float = Field(default=120.0)

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
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=content))]
                )
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
        Return a Runnable that prompts llama.cpp for structured JSON and parses into Pydantic schema.
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
                "Return raw JSON only, without markdown fences, explanation, or meta-schema wrapper."
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
                            try:
                                return schema.model_validate(data["properties"])
                            except Exception:
                                pass
                        for v in data.values():
                            if isinstance(v, dict):
                                try:
                                    return schema.model_validate(v)
                                except Exception:
                                    pass
                    return schema.model_validate(data)
                except Exception:
                    raise parse_err

        return RunnableLambda(_invoke_structured)  # type: ignore[return-value]


# ─── Ollama Embeddings ─────────────────────────────────────────────────────────


class OllamaEmbeddings(Embeddings):
    """
    Ultra-fast local Ollama embeddings client calling POST /api/embed.
    Zero cloud dependencies, sub-millisecond local vector generation.
    """

    def __init__(
        self,
        model: str = "embeddinggemma:300m-qat-q8_0",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        endpoint = f"{self.base_url}/api/embed"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(endpoint, json={"model": self.model, "input": texts})
                res.raise_for_status()
                data = res.json()
                return data.get("embeddings", [])
        except Exception as exc:
            logger.error("Ollama embed_documents failed", model=self.model, error=str(exc))
            raise ConfigurationError(
                f"Failed to generate Ollama embeddings with model '{self.model}'",
                detail=str(exc),
            ) from exc

    def embed_query(self, text: str) -> list[float]:
        embs = self.embed_documents([text])
        return embs[0] if embs else []

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        endpoint = f"{self.base_url}/api/embed"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(endpoint, json={"model": self.model, "input": texts})
                res.raise_for_status()
                data = res.json()
                return data.get("embeddings", [])
        except Exception as exc:
            logger.error("Ollama aembed_documents failed", model=self.model, error=str(exc))
            raise ConfigurationError(
                f"Failed to generate Ollama embeddings with model '{self.model}'",
                detail=str(exc),
            ) from exc

    async def aembed_query(self, text: str) -> list[float]:
        res = await self.aembed_documents([text])
        return res[0] if res else []


class LlamaCppEmbeddings(Embeddings):
    """
    Client for local llama.cpp embeddings (e.g. ggml-org/embeddinggemma-300M-GGUF:Q8_0).
    Targets standard OpenAI-compatible /v1/embeddings endpoint (with fallback to /embedding).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081/v1",
        model: str = "ggml-org/embeddinggemma-300M-GGUF:Q8_0",
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(
                    f"{self.base_url}/embeddings",
                    json={"model": self.model, "input": texts},
                )
                if res.status_code == 200:
                    data = res.json()
                    return [item["embedding"] for item in data.get("data", [])]
                # Fallback to single text /embedding
                results: list[list[float]] = []
                for t in texts:
                    res_single = client.post(
                        f"{self.base_url.replace('/v1', '')}/embedding",
                        json={"content": t},
                    )
                    res_single.raise_for_status()
                    results.append(res_single.json().get("embedding", []))
                return results
        except Exception as exc:
            logger.error("llama.cpp embed_documents failed", model=self.model, error=str(exc))
            raise ConfigurationError(
                f"Failed to generate llama.cpp embeddings with model '{self.model}'",
                detail=str(exc),
            ) from exc

    def embed_query(self, text: str) -> list[float]:
        embs = self.embed_documents([text])
        return embs[0] if embs else []

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/embeddings",
                    json={"model": self.model, "input": texts},
                )
                if res.status_code == 200:
                    data = res.json()
                    return [item["embedding"] for item in data.get("data", [])]
                # Fallback
                results: list[list[float]] = []
                for t in texts:
                    res_single = await client.post(
                        f"{self.base_url.replace('/v1', '')}/embedding",
                        json={"content": t},
                    )
                    res_single.raise_for_status()
                    results.append(res_single.json().get("embedding", []))
                return results
        except Exception as exc:
            logger.error("llama.cpp aembed_documents failed", model=self.model, error=str(exc))
            raise ConfigurationError(
                f"Failed to generate llama.cpp embeddings with model '{self.model}'",
                detail=str(exc),
            ) from exc

    async def aembed_query(self, text: str) -> list[float]:
        res = await self.aembed_documents([text])
        return res[0] if res else []


# ─── Health & CLI Model Discovery Helpers ─────────────────────────────────────


async def discover_ollama_cli_models() -> dict[str, list[str]]:
    """
    Run 'ollama list' CLI command and parse installed models.
    Distinguishes between generative LLMs and embedding models.
    """
    llm_models: list[str] = []
    embedding_models: list[str] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
        if proc.returncode == 0:
            lines = stdout.decode().strip().split("\n")
            for line in lines[1:]:  # skip header
                parts = line.split()
                if parts:
                    name = parts[0]
                    lower_name = name.lower()
                    if any(kw in lower_name for kw in ("embed", "bge", "nomic", "minilm")):
                        embedding_models.append(name)
                    else:
                        llm_models.append(name)
    except Exception as exc:
        logger.debug("Failed to run 'ollama list' CLI", error=str(exc))

    return {"llm_models": llm_models, "embedding_models": embedding_models}


async def discover_llamacpp_cache_models() -> list[str]:
    """
    Run 'llama-server --cache-list' CLI command and parse models currently in the local cache.
    """
    cache_models: list[str] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "llama-server", "--cache-list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
        if proc.returncode == 0:
            lines = stdout.decode().strip().split("\n")
            for line in lines:
                match = re.search(r"^\s*\d+\.\s*(.+)$", line)
                if match:
                    cache_models.append(match.group(1).strip())
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
    Discover Ollama status and models using both 'ollama list' CLI and HTTP REST API.
    Returns connected state, text generation models, and detected embedding models.
    """
    endpoint = f"{base_url.rstrip('/')}/api/tags"
    cli_result = await discover_ollama_cli_models()
    cli_llms = cli_result["llm_models"]
    cli_embeddings = cli_result["embedding_models"]

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

    # User-specified primary models for Ollama
    primary_ollama_llms = ["granite4.2:3b-q4_K_M", "qwen3.5:4b", "gemma4:e2b-it-qat", "gemma4:e2b"]
    primary_ollama_embs = ["embeddinggemma:300m-qat-q8_0"]

    # Merge models preserving order with primary models at the top
    all_llms = list(dict.fromkeys(primary_ollama_llms + cli_llms + [m for m in api_models if not any(k in m.lower() for k in ("embed", "bge", "nomic"))]))
    all_embeddings = list(dict.fromkeys(primary_ollama_embs + cli_embeddings + [m for m in api_models if any(k in m.lower() for k in ("embed", "bge", "nomic"))]))

    # If CLI succeeded, Ollama daemon is installed and active
    if cli_llms or cli_embeddings:
        connected = True

    default_model = "gemma4:e2b-it-qat" if "gemma4:e2b-it-qat" in all_llms else all_llms[0]

    return {
        "connected": connected,
        "provider": "ollama",
        "base_url": base_url,
        "models": all_llms,
        "embedding_models": all_embeddings,
        "default_model": default_model,
    }


async def check_llamacpp_status(base_url: str = "http://localhost:8081/v1") -> dict[str, Any]:
    """
    Discover llama.cpp status and models using 'llama-server --cache-list',
    HTTP /v1/models endpoint, and local HuggingFace cache.
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

    primary_llamacpp_llms = [
        "google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0",
        "psychopenguin/Qwen3.5-4B-Q4_K_M-GGUF:Q4_K_M",
        "ibm-granite/granite-4.2-3b-GGUF:Q4_K_M",
    ]
    primary_llamacpp_embs = [
        "ggml-org/embeddinggemma-300M-GGUF:Q8_0",
    ]

    combined = list(dict.fromkeys(primary_llamacpp_llms + api_models + cache_models + hf_models))
    default_model = "google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0" if "google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0" in combined else combined[0]

    return {
        "connected": connected,
        "provider": "llama_cpp",
        "base_url": base_url,
        "models": combined,
        "cache_models": list(dict.fromkeys(primary_llamacpp_embs + cache_models)),
        "default_model": default_model,
    }
