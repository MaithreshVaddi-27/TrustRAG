"""
Regression tests for audit Wave 2 — cloud failure-story correctness.

Covers:
  B-4  per-analysis LLM call/token ledger and its cap
  B-5  vendor SDK / transport failures classified as a terminal LLM_OUTAGE
  B-16 cloud clients are never evicted or closed by the RAM-based LRU
  B-17 credentials are redacted by value, not only by key name
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.observability.logging import _scrub_sensitive, scrub_secret_values
from app.llm.llm_ledger import (
    begin_analysis,
    calls_remaining,
    current_ledger,
    end_analysis,
    invoke_counted,
    llm_budget_exhausted,
    max_calls_per_analysis,
    record_call,
)

CONFIG_PATH = "app.llm.llm_ledger.get_model_config"


def _cfg(provider: str, cap: int = 4) -> MagicMock:
    m = MagicMock()
    m.llm_provider = provider
    m.max_llm_calls_per_analysis = cap
    return m


# ─── B-4: the ledger ───────────────────────────────────────────────────────────


def _response(inp: int = 10, out: int = 5) -> MagicMock:
    r = MagicMock()
    r.usage_metadata = {"input_tokens": inp, "output_tokens": out}
    return r


def test_invoke_counted_records_calls_and_tokens():
    llm = MagicMock()
    llm.model_name = "gemini-3.8-flash"
    llm.ainvoke = AsyncMock(return_value=_response(120, 45))

    async def run():
        tok = begin_analysis()
        try:
            for _ in range(3):
                await invoke_counted(llm, "hi")
            return current_ledger().as_dict()
        finally:
            end_analysis(tok)

    import asyncio

    snap = asyncio.run(run())
    assert snap["calls"] == 3
    assert snap["input_tokens"] == 360
    assert snap["output_tokens"] == 135
    assert snap["by_model"] == {"gemini-3.8-flash": 3}


def test_invoke_counted_falls_back_to_length_estimate():
    """An unusual response shape must degrade token precision, not break the call."""
    llm = MagicMock()
    r = MagicMock()
    r.usage_metadata = None
    r.response_metadata = {}
    r.content = "x" * 40  # -> 10 tokens by the //4 heuristic
    llm.ainvoke = AsyncMock(return_value=r)

    import asyncio

    async def run():
        tok = begin_analysis()
        try:
            await invoke_counted(llm, "hi")
            return current_ledger()
        finally:
            end_analysis(tok)

    led = asyncio.run(run())
    assert led.calls == 1
    assert led.output_tokens == 10


def test_no_ledger_outside_an_analysis_is_safe():
    """Counting must be a no-op when no analysis is in flight (e.g. MCP tool)."""
    assert current_ledger() is None
    assert record_call() is None
    assert llm_budget_exhausted() is False
    assert calls_remaining() is None


@pytest.mark.parametrize("provider", ["ollama", "llama_cpp", "mlx"])
def test_local_tiers_are_never_capped(provider):
    """A local model costs no money; an on-prem 70B operator must not be
    throttled by a spend guard."""
    with patch(CONFIG_PATH, return_value=_cfg(provider)):
        assert max_calls_per_analysis() is None
        assert llm_budget_exhausted() is False


@pytest.mark.parametrize("provider", ["gemini", "google_genai"])
def test_cloud_tiers_are_capped(provider):
    with patch(CONFIG_PATH, return_value=_cfg(provider, cap=4)):
        assert max_calls_per_analysis() == 4


def test_budget_guard_does_not_fire_for_local_however_many_calls():
    with patch(CONFIG_PATH, return_value=_cfg("ollama")):
        tok = begin_analysis()
        try:
            for _ in range(500):
                record_call()
            assert llm_budget_exhausted() is False
        finally:
            end_analysis(tok)


def test_budget_guard_fires_once_cloud_cap_is_spent():
    with patch(CONFIG_PATH, return_value=_cfg("gemini", cap=3)):
        tok = begin_analysis()
        try:
            for _ in range(3):
                record_call()
            assert llm_budget_exhausted() is True
            assert calls_remaining() == 0
        finally:
            end_analysis(tok)


def test_ledgers_are_isolated_per_context():
    """Two concurrent analyses must not share a budget (ContextVar scoping)."""
    import asyncio

    async def analysis_spend(n: int) -> int:
        tok = begin_analysis()
        try:
            for _ in range(n):
                record_call()
            return current_ledger().calls
        finally:
            end_analysis(tok)

    async def both():
        return await asyncio.gather(analysis_spend(2), analysis_spend(7))

    first, second = asyncio.run(both())
    assert sorted([first, second]) == [2, 7]


# ─── B-5: provider-outage classification ───────────────────────────────────────
# NOTE: the first-generation classify_llm_exception() unit tests were removed
# with the helper itself (centralize-exceptions refactor deleted
# app/core/llm_outage.py). Outage behavior is covered at the graph level below
# (dead credential → terminal LLM_OUTAGE; ordinary errors still recoverable).


# ─── B-16: no client registry (fresh client per call) ─────────────────────────
# The bounded LLM registry was removed: every get_llm() constructs a fresh
# HTTP-backed client, so there is nothing to evict and no client can be
# closed mid-request. These pin the replacement contract.


def test_llm_clients_are_constructed_fresh_per_call():
    """No registry: two identical get_llm() calls return distinct objects."""
    from app.llm.model_registry import get_llm

    with patch("app.llm.model_registry._create_llm") as fake_create:
        fake_create.side_effect = lambda **kwargs: MagicMock(name="llm")
        first = get_llm("ollama", "gemma3:1b")
        second = get_llm("ollama", "gemma3:1b")
    assert first is not second
    assert fake_create.call_count == 2


def test_cloud_clients_are_never_shared_across_calls():
    """Same guarantee for cloud providers (previously: never evicted)."""
    from app.llm.model_registry import get_llm

    with patch("app.llm.model_registry._create_llm") as fake_create:
        fake_create.side_effect = lambda **kwargs: MagicMock(name="llm")
        first = get_llm("gemini", "gemini-3.5-flash-lite")
        second = get_llm("gemini", "gemini-3.5-flash-lite")
    assert first is not second
    assert fake_create.call_count == 2


# ─── B-17: credential redaction by value ───────────────────────────────────────
# NOTE: every string below is SYNTHETIC (format-valid, value-fake) — redaction
# test vectors only. No real credential is ever committed; runtime secrets load
# from env (.env → Settings) and tests use os.environ.setdefault dummies.


@pytest.mark.parametrize(
    "secret",
    [
        "AIzaSyD-1234567890abcdefghijklmnopqrstu",  # SYNTHETIC
        "sk-abcdefghijklmnopqrstuvwxyz012345",  # SYNTHETIC
        "hf_abcdefghijklmnopqrstuvwxyz01",  # SYNTHETIC
    ],
)
def test_secret_values_are_scrubbed(secret):
    assert secret not in scrub_secret_values(f"validation failed for input_value={secret}")
    assert secret not in scrub_secret_values(f"Authorization: Bearer {secret}")


def test_scrubber_leaves_harmless_text_alone():
    assert scrub_secret_values("connection refused") == "connection refused"


def test_structlog_processor_scrubs_value_not_just_key():
    """Regression (audit B-17): key-name scrubbing alone missed credentials
    embedded in an exception message by a vendor SDK."""
    key = "AIzaSyD-1234567890abcdefghijklmnopqrstu"
    out = _scrub_sensitive(None, "error", {"error": f"invalid key: {key}"})
    assert key not in out["error"]


def test_structlog_processor_still_redacts_sensitive_keys():
    out = _scrub_sensitive(None, "info", {"api_key": "whatever-value"})
    assert out["api_key"] == "[REDACTED]"


# ─── B-5: the graph short-circuits instead of entering recovery ────────────────


class _DeadCredential(Exception):
    status_code = 401


@pytest.mark.asyncio
async def test_dead_credential_yields_terminal_llm_outage_not_abstain():
    """Regression (audit B-5): a revoked key used to be swallowed by the node's
    generic `except Exception`, converted to verdict FAIL, and driven through up
    to three more recovery rounds against the live API before terminating as
    `abstained` — telling the user the knowledge base lacked evidence."""
    from app.rag.agent.graph import _execute_with_fallback

    async def boom():
        raise _DeadCredential("API key not valid")

    with patch("app.rag.agent.graph.add_trace_event", AsyncMock()):
        out = await _execute_with_fallback(
            {"analysis_id": "a1", "attempts": 0}, "generation", boom, timeout_seconds=5
        )

    assert out["diagnosis_type"] == "LLM_UNAVAILABLE"
    # Recovery budget exhausted => the graph terminates instead of retrying.
    assert out["attempts"] >= 1
    assert out["reliability_score"] == 0.0
    assert "unavailable" in out["answer"].lower()
    assert [e["error_type"] for e in out["node_errors"]] == ["LLM_UNAVAILABLE"]


@pytest.mark.asyncio
async def test_ordinary_node_error_still_allows_recovery():
    """The outage path must not swallow ordinary bugs — those should keep
    producing node_errors and leaving the recovery budget untouched."""
    from app.rag.agent.graph import _execute_with_fallback

    async def bug():
        raise ValueError("unparseable verdict json")

    with patch("app.rag.agent.graph.add_trace_event", AsyncMock()):
        out = await _execute_with_fallback(
            {"analysis_id": "a1", "attempts": 0}, "generation", bug, timeout_seconds=5
        )

    assert out.get("diagnosis_type") is None
    assert out["attempts"] == 0
    assert [e["error_type"] for e in out["node_errors"]] == ["ValueError"]


@pytest.mark.asyncio
async def test_budget_guard_stops_node_before_spending():
    """Once the cloud cap is spent, a node must not start another paid call."""
    from app.rag.agent.graph import _execute_with_fallback

    called = {"n": 0}

    async def would_cost_money():
        called["n"] += 1
        return {}

    with (
        patch("app.rag.agent.graph.add_trace_event", AsyncMock()),
        patch(CONFIG_PATH, return_value=_cfg("gemini", cap=2)),
    ):
        tok = begin_analysis()
        try:
            for _ in range(2):
                record_call()
            assert llm_budget_exhausted() is True
            out = await _execute_with_fallback(
                {"analysis_id": "a1", "attempts": 0},
                "generation",
                would_cost_money,
                timeout_seconds=5,
            )
        finally:
            end_analysis(tok)

    assert called["n"] == 0, "node ran despite an exhausted budget"
    assert out["diagnosis_type"] == "RECOVERY_BUDGET_EXHAUSTED"
    assert [e["error_type"] for e in out["node_errors"]] == ["RECOVERY_BUDGET_EXHAUSTED"]


# ─── B-7: context compression must not be a hidden cost multiplier ─────────────


def test_compression_is_off_by_default():
    """Compression issues a SECOND full LLM call on the same model. Cloud tiers
    have 128K-1M windows, so firing by default doubled cloud generation cost
    (audit B-7)."""
    from app.core.config.model_config import get_model_config

    cfg = get_model_config()
    assert cfg.context_compression_provider == "off", (
        "compression provider must default to 'off'; a cloud tier pays a second "
        "full LLM call for a benefit it rarely needs"
    )
    assert cfg.context_compression_enabled is False


def test_compression_threshold_is_configurable():
    from app.core.config.model_config import get_model_config

    assert get_model_config().context_compression_min_tokens > 0


# ─── B-14: provider aliases must resolve to the right context window ───────────


def test_cloud_aliases_are_not_clamped_to_the_local_window():
    """'google_genai' is an accepted provider spelling but was missing
    from the limits table, so it fell through to the 4096 local default and
    logged a false 'evidence will be truncated' warning (audit B-14)."""
    from app.rag.generation.generator import calculate_dynamic_num_ctx

    big = "word " * 4000  # ~20k tokens: far over local, well under cloud
    gemini = calculate_dynamic_num_ctx(big, "", "q", 512, "gemini")
    assert calculate_dynamic_num_ctx(big, "", "q", 512, "google_genai") == gemini
    # Cloud must not be pinned to the local 4096 cap.
    assert gemini > 4096


def test_local_aliases_also_resolve():
    from app.rag.generation.generator import calculate_dynamic_num_ctx

    big = "word " * 4000
    assert calculate_dynamic_num_ctx(big, "", "q", 512, "llamacpp") == calculate_dynamic_num_ctx(
        big, "", "q", 512, "llama_cpp"
    )


def test_num_ctx_is_never_sent_to_cloud_clients():
    """The cloud context number is advisory only — sending num_ctx to a cloud
    client is a ValidationError on Gemini."""
    from app.rag.generation.generator import _invoke_kwargs_for_provider

    for provider in ("gemini", "google_genai"):
        kwargs = _invoke_kwargs_for_provider(provider, 512, num_ctx=8192)
        assert "num_ctx" not in kwargs, f"{provider} got num_ctx: {kwargs}"
    for provider in ("ollama", "llama_cpp", "mlx"):
        kwargs = _invoke_kwargs_for_provider(provider, 512, num_ctx=8192)
        assert kwargs.get("num_ctx") == 8192


# ─── B-15: the effective model must always be allowlist-checked ───────────────


def test_provider_normalization_is_canonical():
    """Aliases must resolve identically wherever they are handled, so the
    allowlist check, the resolved model, the persisted document, and downstream
    provider switches cannot disagree (audit B-15/B-18)."""
    from app.core.config.model_config import normalize_provider

    assert normalize_provider("google_genai") == "google_genai"
    assert normalize_provider("llamacpp") == "llama_cpp"
    assert normalize_provider("llama-cpp") == "llama_cpp"
    assert normalize_provider("  GEMINI ") == "gemini"
    assert normalize_provider(None) == ""
    assert normalize_provider("mystery") == "mystery"


def test_effective_cloud_model_is_validated_even_when_request_omits_it():
    """Regression (audit B-15): with `llm_model` omitted, the old check resolved
    to None and skipped the allowlist entirely, so the config default went
    through unvalidated. The EFFECTIVE model must always be checked."""
    from pydantic import ValidationError

    from app.api.v1.schemas.analysis import AnalysisCreate
    from app.core.config.model_config import get_model_config

    real = get_model_config()
    base = {"knowledge_base_id": "64ee39d09c6292376e191982", "query": "hello"}

    class _CfgStub:
        """Minimal stand-in: the validator builds allowlists for every provider."""

        llm_provider = "gemini"
        supported_gemini_models: ClassVar[list[str]] = ["gemini-allowed-only"]
        embedding_dimensionality = real.embedding_dimensionality
        embedding_model = real.embedding_model

        def __init__(self, resolved: str):
            self._resolved = resolved

        def llm_model_for(self, _provider):
            return self._resolved

        # The validator also allowlists the resolved verification model
        # (B-15); keep it inside the allowlist so this test isolates the
        # generation-model check rather than tripping the verifier one.
        @property
        def verification_provider(self) -> str:
            return "llama_cpp"

        def verification_model_for(self, _provider):
            return "some/local-verifier"

    # 1. Config default outside the allowlist is rejected even with no
    #    llm_model supplied by the caller.
    with patch(
        "app.api.v1.schemas.analysis.get_model_config", return_value=_CfgStub("gemini-not-allowed")
    ):
        with pytest.raises(ValidationError, match="not enabled"):
            AnalysisCreate(llm_provider="gemini", **base)

    # 2. The same request passes when the resolved default IS allowed.
    with patch(
        "app.api.v1.schemas.analysis.get_model_config", return_value=_CfgStub("gemini-allowed-only")
    ):
        with patch("app.llm.local_llm.get_discovered_llms", return_value=frozenset()):
            ok = AnalysisCreate(llm_provider="gemini", **base)
    assert ok.llm_model is None  # the caller did not ask for a specific model


def test_cross_provider_mismatch_is_still_rejected():
    from pydantic import ValidationError

    from app.api.v1.schemas.analysis import AnalysisCreate
    from app.core.config.model_config import get_model_config

    gemini = get_model_config().supported_gemini_models
    if not gemini:
        pytest.skip("no Gemini models configured")
    with patch("app.llm.local_llm.get_discovered_llms", return_value=frozenset()):
        with pytest.raises(ValidationError):
            AnalysisCreate(
                knowledge_base_id="64ee39d09c6292376e191982",
                query="hi",
                llm_provider="ollama",
                llm_model=gemini[0],
            )


# ─── B-18: provider asymmetries ──────────────────────────────────────────────


def test_gemini_and_local_keep_their_own_token_parameters():
    from app.rag.generation.generator import _invoke_kwargs_for_provider

    assert "max_output_tokens" in _invoke_kwargs_for_provider("gemini", 512)
    assert "max_output_tokens" in _invoke_kwargs_for_provider("google_genai", 512)
    # Local OpenAI-compatible servers do still take max_tokens.
    assert "max_tokens" in _invoke_kwargs_for_provider("ollama", 512)
    assert "max_tokens" in _invoke_kwargs_for_provider("llama_cpp", 512)


def test_verification_model_allowlist_rejects_unbudgeted_cloud_model(monkeypatch):
    """The verifier runs its own billed calls. Nothing used to constrain WHICH
    cloud model those calls targeted, so a drifted verification model could
    bill a model the generation allowlist already forbids (audit B-15)."""
    from app.api.v1.schemas.analysis import AnalysisCreate
    from app.core import config as cfgmod

    real = cfgmod.get_model_config()

    class _CfgStub:
        """Cloud generation allowlist stays valid; the verifier is the offender."""

        llm_provider = "gemini"
        supported_gemini_models: ClassVar[list[str]] = ["gemini-allowed-only"]
        embedding_dimensionality = real.embedding_dimensionality
        embedding_model = real.embedding_model

        def __init__(self, resolved: str):
            self._resolved = resolved

        def llm_model_for(self, provider: str) -> str:
            return self._resolved

        @property
        def verification_provider(self) -> str:
            return "gemini"

        def verification_model_for(self, provider: str) -> str:
            return "some-unbudgeted-expensive-model"

    from app.api.v1.schemas import analysis as analysis_mod

    monkeypatch.setattr(analysis_mod, "get_model_config", lambda: _CfgStub("gemini-allowed-only"))
    monkeypatch.delenv("GEMINI_VERIFICATION_MODEL", raising=False)
    monkeypatch.delenv("VERIFICATION_MODEL", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    with pytest.raises(ValueError, match="Verification model"):
        AnalysisCreate(knowledge_base_id="kb1", query="q", llm_provider="gemini")


def test_verification_model_allowlist_allows_env_operator_override(monkeypatch):
    """An explicit env override is an operator decision, same trust level as
    settings.<provider>_model — honour it rather than rejecting the request."""
    from app.api.v1.schemas.analysis import AnalysisCreate
    from app.core import config as cfgmod

    real = cfgmod.get_model_config()

    class _CfgStub:
        llm_provider = "gemini"
        supported_gemini_models: ClassVar[list[str]] = ["gemini-allowed-only"]
        embedding_dimensionality = real.embedding_dimensionality
        embedding_model = real.embedding_model

        def llm_model_for(self, provider: str) -> str:
            return "gemini-allowed-only"

        @property
        def verification_provider(self) -> str:
            return "gemini"

        def verification_model_for(self, provider: str) -> str:
            return "operator-chosen-verifier"

    monkeypatch.setattr(cfgmod, "get_model_config", lambda: _CfgStub())
    monkeypatch.setenv("GEMINI_VERIFICATION_MODEL", "operator-chosen-verifier")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    created = AnalysisCreate(knowledge_base_id="kb1", query="q", llm_provider="gemini")
    assert created.llm_provider == "gemini"


def test_nli_timeout_is_longer_for_billed_cloud_calls(monkeypatch):
    """A fixed 90s cap cancelled cloud NLI generation mid-flight. Cancelled
    Gemini requests are still billed, so cloud must use the configured
    provider budget (audit B-18)."""
    from app.rag.verification import verifier

    class _CloudCfg:
        verification_provider = "gemini"
        llm_timeout_seconds = 180

    class _LocalCfg:
        verification_provider = "llama_cpp"
        llm_timeout_seconds = 180

    monkeypatch.setattr(verifier, "NLI_PER_CALL_TIMEOUT_SECONDS", 90)

    with patch("app.core.config.get_model_config", return_value=_CloudCfg()):
        assert verifier._nli_timeout_seconds() == 180

    with patch("app.core.config.get_model_config", return_value=_LocalCfg()):
        assert verifier._nli_timeout_seconds() == 90


def test_nli_timeout_never_goes_below_the_local_floor(monkeypatch):
    """A misconfigured short cloud timeout must not shorten the local guard."""
    from app.rag.verification import verifier

    class _ShortCfg:
        verification_provider = "gemini"
        llm_timeout_seconds = 10

    monkeypatch.setattr(verifier, "NLI_PER_CALL_TIMEOUT_SECONDS", 90)
    with patch("app.core.config.get_model_config", return_value=_ShortCfg()):
        assert verifier._nli_timeout_seconds() == 90
