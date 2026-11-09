"""
TRUSTRAG — Local LLM provider: llama.cpp client.

LangChain BaseChatModel interface for llama.cpp HTTP server (llama-server)
via its OpenAI-compatible /v1/chat/completions API. Also serves Apple MLX
(mlx_lm.server), which speaks the same protocol.
"""

from __future__ import annotations

from typing import Any, TypeVar

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.config import get_model_config
from app.config.settings import _DEFAULT_LLAMACPP_BASE_URL
from app.core.system.concurrency import get_global_semaphore
from app.llm.providers.base import _convert_messages_to_dict, _shared_http_client
from app.observability.logging import get_logger
from app.security.exceptions import ConfigurationError

logger = get_logger(__name__)

__all__ = ["ChatLlamaCppClient"]

T = TypeVar("T", bound=BaseModel)


class ChatLlamaCppClient(BaseChatModel):
    """
    Client for llama.cpp HTTP server (llama-server) via its OpenAI-compatible
    /v1/chat/completions API. Also serves Apple MLX (mlx_lm.server), which
    speaks the same protocol.
    """

    base_url: str = Field(default=_DEFAULT_LLAMACPP_BASE_URL)
    model: str = Field(default="LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M")
    temperature: float = Field(default=0.2)
    top_p: float = Field(default=0.9)
    max_tokens: int = Field(default=1024)
    max_completion_tokens: int | None = Field(default=None)
    timeout: float = Field(default=120.0)
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
            import asyncio

            asyncio.get_running_loop()
        except RuntimeError:
            import asyncio

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
        default_num_batch = cfg.local_llm_num_batch

        kv_cache_quant = cfg.kv_cache_quantization
        use_flash_attn = cfg.flash_attention
        use_prompt_cache = cfg.prompt_caching

        min_p = cfg.local_llm_min_p
        top_k = cfg.local_llm_top_k
        early_exit_eos = cfg.local_llm_early_exit_eos

        requested_num_ctx = kwargs.get("num_ctx", kwargs.get("n_ctx"))
        if requested_num_ctx is not None and int(requested_num_ctx) > cfg.local_llm_num_ctx:
            logger.warning(
                "Requested num_ctx exceeds configured server context",
                requested=requested_num_ctx,
                server_ctx=cfg.local_llm_num_ctx,
            )

        _llama_stops: list[str] = []
        if early_exit_eos:
            _llama_stops.extend(["<|endoftext|>", "<|eot_id|>", "<|eot|>"])
        if stop:
            _llama_stops.extend(stop)
        _llama_stops = list(dict.fromkeys(_llama_stops)) or None

        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": dict_messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": False,
            "cache_prompt": use_prompt_cache,
            "repeat_penalty": kwargs.get("repeat_penalty", self.repeat_penalty),
            "n_batch": kwargs.get("num_batch", kwargs.get("n_batch", default_num_batch)),
            "cache_type_k": kv_cache_quant,
            "cache_type_v": kv_cache_quant,
            "flash_attention": use_flash_attn,
            "min_p": min_p if min_p > 0.0 else None,
            "top_k": top_k if top_k > 0 else None,
            "stop": _llama_stops,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        if kwargs.get("format") == "json" or kwargs.get("response_format"):
            payload["response_format"] = {"type": "json_object"}

        try:
            async with get_global_semaphore():
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
                f"Ensure 'llama-server' is running on port 9931 or your configured URL.",
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
        from app.llm.llm_utils import build_structured_output_runnable

        return build_structured_output_runnable(
            generate_fn=self._agenerate,
            schema=schema,
            json_format_kwargs={"response_format": {"type": "json_object"}},
            extra_kwargs=kwargs,
        )
