"""
TRUSTRAG — Local LLM provider: Ollama client.

LangChain BaseChatModel interface for local Ollama instances.
Calls POST {base_url}/api/chat via async httpx with connection pooling.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any, TypeVar

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.config import get_model_config
from app.core.system.concurrency import get_global_semaphore
from app.llm.providers.base import _convert_messages_to_dict
from app.observability.logging import get_logger
from app.security.exceptions import ConfigurationError

logger = get_logger(__name__)

__all__ = ["ChatOllamaClient"]

T = TypeVar("T", bound=BaseModel)

# NOTE: defaults below mirror models.yaml (llm.model_ollama,
# llm.temperature, llm.top_p) for standalone construction in tests.
# Production code must pass base_url/model explicitly from
# get_model_config().llm_model_for("ollama") / settings.ollama_base_url.


def _get_shared_http_client():
    """Lazy getter for _shared_http_client so tests can patch
    app.llm.local_llm._shared_http_client."""
    import app.llm.local_llm as _m

    return _m._shared_http_client


class ChatOllamaClient(BaseChatModel):
    """Lightweight, ultra-fast client for local Ollama instances."""

    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="gemma3:1b")
    temperature: float = Field(default=0.2)
    top_p: float = Field(default=0.9)
    timeout: float = Field(default=120.0)
    format: str | None = Field(default=None)
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
            import asyncio

            asyncio.get_running_loop()
        except RuntimeError:
            import asyncio

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
        default_num_ctx = cfg.local_llm_num_ctx
        default_num_batch = cfg.local_llm_num_batch
        default_keep_alive = cfg.local_llm_keep_alive

        use_prompt_cache = cfg.prompt_caching

        min_p = cfg.local_llm_min_p
        top_k = cfg.local_llm_top_k
        early_exit_eos = cfg.local_llm_early_exit_eos

        options: dict[str, Any] = {
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "num_ctx": kwargs.get("num_ctx", default_num_ctx),
            "num_predict": kwargs.get("max_tokens", 1024),
            "repeat_penalty": kwargs.get("repeat_penalty", self.repeat_penalty),
            "num_batch": kwargs.get("num_batch", kwargs.get("n_batch", default_num_batch)),
            "min_p": min_p if min_p > 0.0 else None,
            "top_k": top_k if top_k > 0 else None,
        }
        options = {k: v for k, v in options.items() if v is not None}

        if use_prompt_cache:
            options["num_keep"] = kwargs.get("num_keep", -1)

        _ollama_stops: list[str] = []
        if early_exit_eos:
            _ollama_stops.extend(["<|endoftext|>", "<|eot_id|>"])
        if stop:
            _ollama_stops.extend(stop)
        if _ollama_stops:
            options["stop"] = list(dict.fromkeys(_ollama_stops))

        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": dict_messages,
            "stream": False,
            "options": options,
            "keep_alive": kwargs.get("keep_alive", default_keep_alive),
        }

        requested_format = kwargs.get("format", self.format)
        if requested_format:
            payload["format"] = requested_format

        try:
            async with get_global_semaphore():
                client = _get_shared_http_client()(self.base_url, self.timeout)
                res = await client.post(endpoint, json=payload)
                if res.status_code == 404:
                    with suppress(Exception):
                        tags_res = await client.get(f"{self.base_url.rstrip('/')}/api/tags")
                        if tags_res.is_success:
                            avail = [m.get("name", "") for m in tags_res.json().get("models", [])]
                            prefix = kwargs.get("model", self.model).split(":")[0]
                            match = next((m for m in avail if m.startswith(prefix)), None)
                            if match:
                                payload["model"] = match
                                res = await client.post(endpoint, json=payload)

            if res.status_code == 404:
                raise ConfigurationError(
                    f"Ollama model '{self.model}' not found. "
                    f"Please run 'ollama pull {self.model}' in your terminal."
                )
            res.raise_for_status()
            data = res.json()
            content = data.get("message", {}).get("content", "")
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
        except httpx.ConnectError as exc:
            raise ConfigurationError(
                f"Cannot connect to Ollama at '{self.base_url}'. "
                f"Is Ollama running? Run 'ollama serve' in your terminal.",
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
        from app.llm.llm_utils import build_structured_output_runnable

        return build_structured_output_runnable(
            generate_fn=self._agenerate,
            schema=schema,
            json_format_kwargs={"format": "json"},
            extra_kwargs=kwargs,
        )


# Re-export constants expected by consumers importing from app.llm.local_llm
