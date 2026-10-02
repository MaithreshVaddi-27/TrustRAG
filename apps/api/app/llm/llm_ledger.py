"""
TRUSTRAG — Per-analysis LLM call/token ledger.

The existing spend guards were both vacuous (audit B-4):

* `cost_controls.max_input_tokens: 100000` was compared against the *query
  string only*, which pydantic already caps at 2000 characters (~500 tokens).
  The ceiling could never be reached, so the check never fired.
* `recovery.max_recovery_tokens: 2000` was compared against
  `len(query)//4 + 100` per round (~110), so a whole run used ~220 of 2000.

Nothing therefore bounded how much a single analysis could spend. On a cloud
tier that is real money: probe + compression + generation + verification, times
up to three recovery rounds, with the verifier's per-claim NLI fallback
multiplying each round by up to `max_individual_nli_fallback` (8).

This module provides the real counter. A `ContextVar` holds one ledger per
in-flight analysis, so concurrent requests cannot pollute each other, and
`invoke_counted` wraps every provider call the app makes.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_model_config
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMCallLedger:
    """Cumulative LLM usage for a single analysis."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    # Per-model breakdown, for diagnosing which stage is expensive.
    by_model: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "by_model": dict(self.by_model),
        }


_LEDGER: ContextVar[LLMCallLedger | None] = ContextVar("trustrag_llm_ledger", default=None)


def begin_analysis() -> Token:
    """Start a fresh ledger for the current analysis. Returns a reset token."""
    return _LEDGER.set(LLMCallLedger())


def end_analysis(token: Token | None = None) -> None:
    """Detach the ledger, restoring the previous context value."""
    if token is not None:
        _LEDGER.reset(token)
    else:
        _LEDGER.set(None)


def current_ledger() -> LLMCallLedger | None:
    """The ledger for the in-flight analysis, or None outside one."""
    return _LEDGER.get()


def max_calls_per_analysis() -> int | None:
    """Per-analysis LLM call cap, or None when the tier is unlimited.

    Only cloud tiers are capped: a local model costs no money, and an on-prem
    operator with a 70B model should not be throttled by a spend guard.
    """
    cfg = get_model_config()
    if (cfg.llm_provider or "").strip().lower() in ("gemini", "google_genai"):
        return int(cfg.max_llm_calls_per_analysis)
    return None


def calls_remaining() -> int | None:
    """Calls left before the cap, or None when uncapped / no active analysis."""
    ledger = _LEDGER.get()
    if ledger is None:
        return None
    cap = max_calls_per_analysis()
    if cap is None:
        return None
    return max(0, cap - ledger.calls)


def llm_budget_exhausted() -> bool:
    """True only when a ledger is active AND its cap has been spent.

    Both conditions matter: outside an analysis there is no ledger, and a local
    tier has an uncapped budget. The guard must never fire in either case, or a
    free local model would report itself as spent.
    """
    ledger = _LEDGER.get()
    if ledger is None:
        return False
    cap = max_calls_per_analysis()
    if cap is None:
        return False
    return ledger.calls >= cap


def _extract_usage(response: Any) -> tuple[int, int]:
    """Best-effort (input, output) token counts from a LangChain response.

    Prefers the provider's own accounting and falls back to a character
    estimate, so an unusual response shape degrades the precision of the
    counter rather than breaking the call.
    """
    input_tokens = 0
    output_tokens = 0

    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)

    if not output_tokens:
        meta = getattr(response, "response_metadata", None)
        if isinstance(meta, dict):
            tu = meta.get("token_usage") or meta.get("usage") or {}
            if isinstance(tu, dict):
                input_tokens = input_tokens or int(
                    tu.get("prompt_tokens") or tu.get("input_tokens") or 0
                )
                output_tokens = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)

    if not output_tokens:
        content = getattr(response, "content", None)
        if isinstance(content, str) and content:
            output_tokens = max(1, len(content) // 4)

    return input_tokens, output_tokens


def record_call(
    *, model: str | None = None, input_tokens: int = 0, output_tokens: int = 0
) -> LLMCallLedger | None:
    """Record one completed LLM call against the active ledger."""
    ledger = _LEDGER.get()
    if ledger is None:
        return None
    ledger.calls += 1
    ledger.input_tokens += int(input_tokens or 0)
    ledger.output_tokens += int(output_tokens or 0)
    if model:
        ledger.by_model[model] = ledger.by_model.get(model, 0) + 1
    remaining = calls_remaining()
    if remaining is not None and remaining <= 0:
        logger.warning(
            "LLM call budget exhausted for this analysis",
            calls=ledger.calls,
            cap=max_calls_per_analysis(),
        )
    return ledger


async def invoke_counted(llm: Any, payload: Any, **kwargs: Any) -> Any:
    """`await llm.ainvoke(payload, **kwargs)` with ledger accounting.

    Used at every LLM call site instead of calling `ainvoke` directly, so the
    ledger sees the fused/batch/per-claim verification paths too — which is
    exactly where the cost multiplication happens.
    """
    response = await llm.ainvoke(payload, **kwargs)
    in_tok, out_tok = _extract_usage(response)
    record_call(model=_model_name(llm), input_tokens=in_tok, output_tokens=out_tok)
    return response


def _model_name(llm: Any) -> str | None:
    for attr in ("model_name", "model", "model_id"):
        value = getattr(llm, attr, None)
        if isinstance(value, str) and value:
            return value
    return None
