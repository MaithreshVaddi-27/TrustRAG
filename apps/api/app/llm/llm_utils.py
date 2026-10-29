"""Shared LLM utilities — content normalization and structured output helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any, TypeVar

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable, RunnableLambda

from app.core.observability.logging import get_logger

T = TypeVar("T")  # bound resolved at runtime by caller's schema


# ─── Content Normalization ──────────────────────────────────────────────────


def normalize_llm_content(raw: Any) -> str:
    """
    Normalize LLM response.content to a plain string.

    Handles provider-specific shapes:
      - str: returned as-is
      - bytes: decoded to UTF-8
      - list[dict|str|object]: joined (dicts with 'text' key, objects with .text attr)
      - other: cast to str
    """
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text"):
                parts.append(item.text)
        return "".join(parts)
    return str(raw)


# ─── JSON Extraction ─────────────────────────────────────────────────────────


def extract_json_substring(text: str) -> str:
    """Safely extract valid JSON payload from an LLM output string."""
    cleaned = text.strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()

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


# ─── Structured Output Builder ───────────────────────────────────────────────


def _rescue_schema_from_text(raw_text: str, schema: Any) -> Any | None:
    """Rescue structured objects when an LLM outputs free-form or malformed text."""
    if not raw_text or not hasattr(schema, "model_fields"):
        return None

    fields = schema.model_fields

    # Case 1: Verdict schemas (e.g. NLIVerdict)
    if "verdict" in fields:
        verdict_match = re.search(
            r"(?:verdict|status|claim\s*is)?[:\s\*\-]*\b(SUPPORTED|CONTRADICTED|NEUTRAL|VERIFIED|PROVEN|TRUE|CORRECT|REFUTED|FALSE|DISPROVEN|ENTAILMENT|UNVERIFIED|UNCERTAIN|VALID|INVALID)\b",
            raw_text,
            re.IGNORECASE,
        )
        if verdict_match:
            raw_verdict = verdict_match.group(1).upper()
            segments: list[int] = []
            for seg_match in re.finditer(
                r"(?:segment|segments|\[segment\]?)\s*#?(\d+)", raw_text, re.IGNORECASE
            ):
                with suppress(ValueError):
                    segments.append(int(seg_match.group(1)))
            if not segments:
                for bracket_match in re.finditer(r"\[(\d+)\]", raw_text):
                    with suppress(ValueError):
                        segments.append(int(bracket_match.group(1)))
            deduped_segments = sorted(set(segments))

            exp_match = re.search(
                r"(?:explanation|reason|because)[:\s]*(.+)", raw_text, re.IGNORECASE | re.DOTALL
            )
            explanation = exp_match.group(1).strip() if exp_match else raw_text.strip()
            if len(explanation) > 300:
                explanation = explanation[:297] + "..."

            with suppress(Exception):
                return schema.model_validate(
                    {
                        "verdict": raw_verdict,
                        "supporting_segments": deduped_segments,
                        "explanation": explanation,
                    }
                )

    # Case 2: Batch verdict schemas (e.g. BatchNLIVerdict)
    if "verdicts" in fields:
        verdicts_list: list[dict[str, Any]] = []
        pattern = re.compile(
            r"(?:claim\s*)?(\d+)[:\.\)]\s*(?:verdict[:\s]*)?\b(SUPPORTED|CONTRADICTED|NEUTRAL|VERIFIED|PROVEN|TRUE|CORRECT|REFUTED|FALSE|DISPROVEN)\b(?:[^\n]*?(?:segment|segments)\s*#?(\d+))?",
            re.IGNORECASE,
        )
        for line in raw_text.splitlines():
            line_strip = line.strip()
            if not line_strip:
                continue
            m = pattern.search(line_strip)
            if m:
                cid = int(m.group(1))
                v = m.group(2).upper()
                seg = int(m.group(3)) if m.group(3) else None
                verdicts_list.append(
                    {
                        "claim_id": cid,
                        "verdict": v,
                        "supporting_segments": [seg] if seg else [],
                        "explanation": line_strip,
                    }
                )
        if verdicts_list:
            with suppress(Exception):
                return schema.model_validate({"verdicts": verdicts_list})

    # Case 3: Claim decomposition (e.g. ClaimDecomposition)
    if "claims" in fields:
        claims: list[str] = []
        for line in raw_text.splitlines():
            line_strip = line.strip()
            if not line_strip:
                continue
            m = re.match(r"^(?:\d+[\.\)]|[-*•])\s*(.+)$", line_strip)
            if m:
                c = m.group(1).strip()
                if len(c) > 10:
                    claims.append(c)
        if claims:
            with suppress(Exception):
                return schema.model_validate({"claims": claims})

    return None


def build_structured_output_runnable(
    generate_fn: Callable[..., Awaitable[ChatResult]],
    schema: Any,
    json_format_kwargs: dict[str, Any],
    extra_kwargs: dict[str, Any],
) -> Runnable[Any, Any]:
    """Build a Runnable that prompts for structured JSON and parses into Pydantic.

    Shared by ChatOllamaClient and ChatLlamaCppClient which differ only in
    how they signal JSON output mode to the model (``format="json"`` vs
    ``response_format={"type": "json_object"}``).

    Args:
        generate_fn: The model's async ``_agenerate`` method (bound to instance).
        schema: Pydantic model class with ``model_json_schema()`` support.
        json_format_kwargs: Provider-specific JSON mode flags, e.g.
            ``{"format": "json"}`` for Ollama or
            ``{"response_format": {"type": "json_object"}}`` for llama.cpp.
        extra_kwargs: Additional kwargs forwarded to ``_agenerate``
            (temperature, max_tokens, etc.).
    """
    schema_dict = schema.model_json_schema()
    props = schema_dict.get("properties", {})
    template = {k: f"<{v.get('type', 'value')}>" for k, v in props.items()}
    template_str = json.dumps(template)

    merged_kwargs = {**json_format_kwargs, **extra_kwargs}

    async def _invoke_structured(input_messages: Any) -> Any:
        if isinstance(input_messages, (str, BaseMessage, tuple)):
            msgs = [input_messages]
        else:
            msgs = list(input_messages)

        # NOTE: only the key list + shape template are sent — never the full
        # JSON-schema dump ($defs, titles, descriptions). The dump added KBs
        # of schema jargon that sub-2B local models echoed back as prose or
        # truncated mid-output, failing validation on every NLI call while
        # simple schemas (decomposition) happened to survive. Keys + shape
        # is sufficient for both local and cloud models.
        instruction = (
            f"\n\nYou MUST respond ONLY with valid JSON using the keys"
            f" {list(props.keys())}.\n"
            f"Required JSON structure:\n{template_str}\n"
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

        result = await generate_fn(augmented_messages, **merged_kwargs)
        raw_text = result.generations[0].message.content
        cleaned_json = extract_json_substring(raw_text)

        try:
            return schema.model_validate_json(cleaned_json)
        except Exception as parse_err:
            logger = get_logger(__name__)
            logger.warning(
                "JSON schema validation failed, attempting repair",
                raw=raw_text[:200],
                error=str(parse_err),
            )
            try:
                data = json.loads(cleaned_json)
                fields = getattr(schema, "model_fields", {})
                if isinstance(data, list):
                    for target in ("verdicts", "claims", "results", "items"):
                        if target in fields:
                            with suppress(Exception):
                                return schema.model_validate({target: data})
                    for target in fields:
                        with suppress(Exception):
                            return schema.model_validate({target: data})
                elif isinstance(data, dict):
                    if "properties" in data and isinstance(data["properties"], dict):
                        with suppress(Exception):
                            return schema.model_validate(data["properties"])
                    for target_key in ("verdicts", "claims"):
                        if target_key in fields and target_key not in data:
                            for alt in (
                                "results",
                                "claims",
                                "items",
                                "data",
                                "verdicts",
                                "statements",
                            ):
                                if alt in data and alt != target_key:
                                    with suppress(Exception):
                                        return schema.model_validate(
                                            {**data, target_key: data[alt]}
                                        )
                    for v in data.values():
                        if isinstance(v, dict):
                            with suppress(Exception):
                                return schema.model_validate(v)
                return schema.model_validate(data)
            except Exception:
                rescued = _rescue_schema_from_text(raw_text, schema)
                if rescued is not None:
                    return rescued
                raise parse_err from None

    return RunnableLambda(_invoke_structured)  # type: ignore[return-value]
