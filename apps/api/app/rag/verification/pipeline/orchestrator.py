"""
TRUSTRAG — Claim verification pipeline: orchestration.

Main orchestrator for decompose → batch-verify → individual-fallback flow,
plus claim retrieval and persistence. Coordinates the pipeline sub-modules:

- ``decomposition`` — answer claim decomposition
- ``nli`` — single + batch + fused NLI verification
- ``retrieval`` — targeted claim evidence retrieval & persistence
- ``metrics`` — NLI batch-failure counters
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.config import get_model_config
from app.observability.logging import get_logger
from app.persistence.mongodb import Collections
from app.persistence.mongodb import get_collection as _mongodb_get_collection


def _shim_or(name, default):
    """Resolve `name` from the `app.rag.verification.verifier` shim if present,
    otherwise fall back to `default`. This lets tests patch
    `app.rag.verification.verifier.<name>` and have the orchestrator honor it."""
    import sys

    shim = sys.modules.get("app.rag.verification.verifier")
    if shim is not None and hasattr(shim, name):
        return getattr(shim, name)
    return default


# Module-level `get_collection` so tests can patch
# `app.rag.verification.pipeline.orchestrator.get_collection` and have the
# orchestrator honor the mock (it reads the name at call time).
get_collection = _mongodb_get_collection


def _get_collection(name):
    return _shim_or("get_collection", get_collection)(name)


def fused_decompose_verify(*args, **kwargs):
    from app.rag.verification.pipeline.decomposition import decompose_answer_to_claims as _real
    return _shim_or("fused_decompose_verify", _real)(*args, **kwargs)


def verify_claim_nli(*args, **kwargs):
    from app.rag.verification.pipeline.nli import verify_claim_nli as _real
    return _shim_or("verify_claim_nli", _real)(*args, **kwargs)


def batch_verify_claims_nli(*args, **kwargs):
    from app.rag.verification.pipeline.nli import batch_verify_claims_nli as _real
    return _shim_or("batch_verify_claims_nli", _real)(*args, **kwargs)


def decompose_answer_to_claims(*args, **kwargs):
    from app.rag.verification.pipeline.decomposition import decompose_answer_to_claims as _real
    return _shim_or("decompose_answer_to_claims", _real)(*args, **kwargs)
from app.llm.local_llm import is_reasoning_model, is_small_model


def _is_small(provider: str | None, model: str | None) -> bool:
    """Wrapper for is_small_model to keep the verifier module's re-export stable."""
    return is_small_model(model, provider)
from app.rag.generation.context import extract_citations
from app.rag.generation.generator import format_context_with_chunk_indices, neutralize_prompt_fences
from app.rag.verification.meta import _fused_claims_cover_answer, _filter_degenerate_claims
from app.rag.verification.pipeline.metrics import get_nli_metrics
from app.rag.verification.pipeline.infra import _chunk_identity
from app.rag.verification.pipeline.retrieval import _persist_claim_evidence, retrieve_evidence_for_claim
from app.rag.verification.schemas import ClaimVerdict
from app.rag.verification.verdict import is_refusal_answer
from app.rag.verification.triple import extract_claim_triple_heuristic

logger = get_logger(__name__)

__all__ = [
    "UNCHECKED_CLAIM_STATE",
    "_await_nli_call",
    "_nli_timeout_seconds",
    "_structured_verifier",
    "batch_verify_claims_nli",
    "decompose_answer_to_claims",
    "execute_claim_verification",
    "fused_decompose_verify",
    "get_nli_metrics",
    "is_refusal_answer",
    "verify_claim_nli",
    "_is_small",
]

# ─── Sentinel ─────────────────────────────────────────────────────────────────
UNCHECKED_CLAIM_STATE = "UNCHECKED"

# ─── Per-call NLI timeout ────────────────────────────────────────────────────
NLI_PER_CALL_TIMEOUT_SECONDS = 90

_CLOUD_PROVIDERS = frozenset({"gemini"})


def _nli_timeout_seconds() -> int:
    """Per-call NLI budget, scaled by provider."""
    try:
        cfg = get_model_config()
        from app.config import normalize_provider

        if normalize_provider(cfg.verification_provider) in _CLOUD_PROVIDERS:
            configured = int(getattr(cfg, "llm_timeout_seconds", 0) or 0)
            if configured > NLI_PER_CALL_TIMEOUT_SECONDS:
                return configured
    except Exception:
        logger.debug("NLI timeout: falling back to default", exc_info=True)
    return NLI_PER_CALL_TIMEOUT_SECONDS


async def _await_nli_call(coro, *, what: str):
    """Await one NLI LLM call with a per-call timeout."""
    import asyncio

    timeout_s = _nli_timeout_seconds()
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except TimeoutError:
        logger.warning("NLI call timed out", what=what, timeout_s=timeout_s)
        raise


def _structured_verifier(
    model_obj: Any,
    provider: str | None,
    schema: type,
    cap: dict[str, Any],
):
    """Build the structured-output verifier for the active provider."""
    from app.config import get_model_config, normalize_provider

    norm = (provider or get_model_config().verification_provider or "").strip().lower()

    if norm in ("gemini", "google_genai"):
        return _apply_cap_via_model_copy(model_obj, cap).with_structured_output(schema)

    return model_obj.with_structured_output(schema, **cap)


def _apply_cap_via_model_copy(model_obj: Any, cap: dict[str, Any]) -> Any:
    """Return a copy of `model_obj` with output-cap fields applied."""
    if not cap:
        return model_obj
    fields = getattr(type(model_obj), "model_fields", None)
    if not fields:
        return model_obj
    applicable = {k: v for k, v in cap.items() if k in fields}
    if not applicable:
        return model_obj
    try:
        return model_obj.model_copy(update=applicable)
    except Exception:
        logger.debug("model_copy cap application failed", exc_info=True)
        return model_obj


# ─── Main orchestrator ──────────────────────────────────────────────────────


async def execute_claim_verification(
    analysis_id_str: str,
    answer: str,
    chunks: list[dict[str, Any]],
    evidence_ids: list[ObjectId],
    user_id_str: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    attempt: int = 0,
    kb_id_str: str | None = None,
) -> list[dict[str, Any]]:
    """
    Decompose answer, execute NLI verifications, and save claims to MongoDB.

    Uses batch verification to minimize API calls and prevent rate limiting (429).
    """
    analysis_id = ObjectId(analysis_id_str)
    claims_coll = _get_collection(Collections.CLAIMS)

    cfg = get_model_config()
    caps = cfg.tier_caps(provider)
    max_claims = caps["max_verification_claims"]
    context_str, context_chunk_indices = format_context_with_chunk_indices(chunks)

    claims_texts: list[str] = []
    results_map: dict[int, dict[str, Any]] = {}

    # 0. Fused fast path
    fused_enabled = bool(getattr(cfg, "fused_decompose_verify", True))
    if (
        fused_enabled
        and answer
        and not is_refusal_answer(answer)
        and not is_reasoning_model(model)
        and not is_small_model(model, provider)
    ):
        try:
            fused_items = await _await_nli_call(
                fused_decompose_verify(
                    answer, chunks, provider=provider, model=model, context_str=context_str
                ),
                what="fused_decompose_verify",
            )
        except TimeoutError:
            fused_items = None
        if fused_items is not None:
            fused_items = [
                it
                for it in fused_items
                if it.get("claim") and not _is_meta_claim(it["claim"])
            ]
            if len(fused_items) > max_claims:
                fused_items = fused_items[:max_claims]
            if fused_items:
                fused_claims = [it["claim"] for it in fused_items]
                if not _fused_claims_cover_answer(answer, fused_claims):
                    logger.warning(
                        "Fused verification omitted answer content; using two-step verification"
                    )
                else:
                    claims_texts = fused_claims
                    results_map = {
                        i + 1: {
                            "verdict": it["verdict"],
                            "supporting_segments": it["supporting_segments"],
                            "explanation": it["explanation"],
                        }
                        for i, it in enumerate(fused_items)
                    }

    if not results_map:
        # 1. Classic two-step path
        try:
            claims_texts = await _await_nli_call(
                decompose_answer_to_claims(answer, provider=provider, model=model),
                what="decompose_answer_to_claims",
            )
        except TimeoutError:
            claims_texts = [answer] if answer and answer.strip() else []
        if not claims_texts and answer and not is_refusal_answer(answer):
            parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if len(s.strip()) > 40]
            if parts:
                logger.info(
                    "Empty structured decomposition; split answer into sentences",
                    sentences=len(parts),
                )
                claims_texts = parts
        if len(claims_texts) == 1 and len(claims_texts[0]) > 400:
            parts = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", claims_texts[0])
                if len(s.strip()) > 40
            ]
            if parts:
                logger.info("Split fallback answer blob into sentences", sentences=len(parts))
                claims_texts = parts

        claims_texts = [c for c in claims_texts if not _is_meta_claim(c)]
        claims_texts = _filter_degenerate_claims(claims_texts)
        if not claims_texts:
            parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if len(s.strip()) > 40]
            if parts:
                logger.info(
                    "All claims filtered as degenerate; sentence-split answer fallback",
                    sentences=len(parts),
                )
                claims_texts = _filter_degenerate_claims(parts)
            else:
                return []

        if len(claims_texts) > max_claims:
            claims_texts = claims_texts[:max_claims]

        # 2. Execute verification (batch first)
        batch_kwargs = {"provider": provider, "model": model, "context_str": context_str}
        try:
            results_map = await _await_nli_call(
                batch_verify_claims_nli(claims_texts, chunks, **batch_kwargs),
                what="batch_verify_claims_nli",
            )
        except Exception:
            logger.warning("Batch verification failed, retrying once before individual fallback")
            try:
                results_map = await _await_nli_call(
                    batch_verify_claims_nli(claims_texts, chunks, **batch_kwargs),
                    what="batch_verify_claims_nli(retry)",
                )
            except Exception:
                logger.warning("Batch verification retry failed, falling back to individual checks")

    # 2b. Targeted retrieval for NEUTRAL claims
    claim_evidence_ids: dict[int, list[ObjectId]] = {}
    if kb_id_str:
        neutral_positions = [
            i
            for i in range(1, len(claims_texts) + 1)
            if str(results_map.get(i, {}).get("verdict", "")).upper() == "NEUTRAL"
        ]
        retrieval_budget = min(max(0, caps["max_claim_retrievals"]), len(neutral_positions))
        if retrieval_budget:
            seen_keys = {_chunk_identity(c) for c in chunks}
            claim_top_k = int(cfg.claim_retrieval_top_k or 5)
            for position in neutral_positions[:retrieval_budget]:
                claim_text = claims_texts[position - 1]
                try:
                    fresh = await _await_nli_call(
                        retrieve_evidence_for_claim(
                            claim_text, kb_id_str, seen_keys, top_k=claim_top_k
                        ),
                        what="retrieve_evidence_for_claim",
                    )
                except TimeoutError:
                    continue
                if not fresh:
                    continue
                seen_keys.update(_chunk_identity(c) for c in fresh)
                pairs = await _persist_claim_evidence(analysis_id, user_id_str, fresh)
                if not pairs:
                    continue
                mini_chunks = [chunk for chunk, _ in pairs]
                mini_str, mini_indices = format_context_with_chunk_indices(mini_chunks)
                try:
                    re_res = await _await_nli_call(
                        verify_claim_nli(
                            claim_text,
                            mini_chunks,
                            provider=provider,
                            model=model,
                            context_str=mini_str,
                        ),
                        what="verify_claim_nli(targeted)",
                    )
                except TimeoutError:
                    continue
                re_verdict = str(re_res.get("verdict", "")).upper()
                if re_verdict in ("SUPPORTED", "CONTRADICTED"):
                    mapped: list[ObjectId] = []
                    for idx in re_res.get("supporting_segments", []):
                        if isinstance(idx, int) and 0 < idx <= len(mini_indices):
                            mini_pos = mini_indices[idx - 1]
                            if 0 <= mini_pos < len(pairs):
                                mapped.append(pairs[mini_pos][1])
                    results_map[position] = {
                        "verdict": re_res.get("verdict", "NEUTRAL"),
                        "supporting_segments": [],
                        "explanation": f"{re_res.get('explanation', '')} [targeted retrieval]",
                    }
                    claim_evidence_ids[position] = mapped

    # 3. Process each claim and persist
    fallback_budget = max(0, int(cfg.max_individual_nli_fallback or 0))
    try:
        _threshold = float(getattr(cfg, "maximum_contradiction_rate", 0.2) or 0.2)
        _contra = sum(
            1 for _r in results_map.values() if str(_r.get("verdict", "")).upper() == "CONTRADICTED"
        )
        if _contra and len(claims_texts) and (_contra / max(1, len(claims_texts))) > _threshold:
            fallback_budget = 0
    except Exception:
        logger.debug("Contradiction early-exit check skipped", exc_info=True)

    claim_docs = []
    for i, text in enumerate(claims_texts, start=1):
        if i in results_map:
            nli_res = results_map[i]
        elif fallback_budget > 0:
            fallback_budget -= 1
            try:
                nli_res = await _await_nli_call(
                    verify_claim_nli(
                        text,
                        chunks,
                        provider=provider,
                        model=model,
                        context_str=context_str,
                    ),
                    what="verify_claim_nli(fallback)",
                )
            except TimeoutError:
                nli_res = {
                    "verdict": UNCHECKED_CLAIM_STATE,
                    "supporting_segments": [],
                    "explanation": f"Verification skipped: per-call NLI timeout ({NLI_PER_CALL_TIMEOUT_SECONDS}s).",
                }
        else:
            nli_res = {
                "verdict": UNCHECKED_CLAIM_STATE,
                "supporting_segments": [],
                "explanation": (
                    "Verification skipped: batch NLI unavailable and the "
                    "per-claim fallback budget is exhausted."
                ),
            }

        raw_segments = nli_res.get("supporting_segments", [])
        supporting_evidence_ids = []
        for idx in raw_segments:
            if not isinstance(idx, int) or not 0 < idx <= len(context_chunk_indices):
                continue
            chunk_idx = context_chunk_indices[idx - 1]
            if 0 <= chunk_idx < len(evidence_ids):
                supporting_evidence_ids.append(evidence_ids[chunk_idx])

        if nli_res.get("verdict") in ("SUPPORTED", "CONTRADICTED", "NEUTRAL"):
            for cited_num in extract_citations(text):
                if 1 <= cited_num <= len(context_chunk_indices):
                    chunk_idx = context_chunk_indices[cited_num - 1]
                    if 0 <= chunk_idx < len(evidence_ids):
                        cited_id = evidence_ids[chunk_idx]
                        if cited_id not in supporting_evidence_ids:
                            supporting_evidence_ids.append(cited_id)

        for extra_id in claim_evidence_ids.get(i, []):
            if extra_id not in supporting_evidence_ids:
                supporting_evidence_ids.append(extra_id)

        if (
            not supporting_evidence_ids
            and evidence_ids
            and nli_res.get("verdict") in ("SUPPORTED", "CONTRADICTED")
            and i not in claim_evidence_ids
        ):
            supporting_evidence_ids = list(evidence_ids)

        subj, pred, obj = extract_claim_triple_heuristic(text)
        claim_doc = {
            "analysis_id": analysis_id,
            "user_id": ObjectId(user_id_str) if user_id_str else None,
            "text": text,
            "subject": subj,
            "predicate": pred,
            "object": obj,
            "state": nli_res.get("verdict", "NEUTRAL"),
            "explanation": nli_res.get("explanation", ""),
            "evidence_ids": supporting_evidence_ids,
            "attempt": attempt,
            "created_at": datetime.now(UTC),
        }
        claim_docs.append(claim_doc)

    if claim_docs:
        try:
            insert_res = await claims_coll.insert_many(claim_docs)
            for doc, inserted_id in zip(claim_docs, insert_res.inserted_ids, strict=False):
                doc["_id"] = inserted_id
        except TypeError:
            for doc in claim_docs:
                res = await claims_coll.insert_one(doc)
                doc["_id"] = res.inserted_id

    return claim_docs


def _is_meta_claim(text: str) -> bool:
    """True when a claim is about the QA process, not the subject matter."""
    lowered = text.lower().strip()
    if lowered.startswith("#"):
        return True
    if "<context>" in lowered or "answering_criteria" in lowered or "final_section" in lowered:
        return True
    return any(p in lowered for p in ("the user asks", "the user query", "the question asks"))
