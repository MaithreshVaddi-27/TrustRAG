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

import httpx
import pytest

from app.core.exceptions import LLMUnavailableError
from app.core.llm_ledger import (
    begin_analysis,
    calls_remaining,
    current_ledger,
    end_analysis,
    invoke_counted,
    llm_budget_exhausted,
    max_calls_per_analysis,
    record_call,
)
from app.core.llm_outage import classify_llm_exception
from app.core.logging import _scrub_sensitive, scrub_secret_values

CONFIG_PATH = "app.core.config.get_model_config"


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


@pytest.mark.parametrize("provider", ["gemini", "google_genai", "nvidia", "nim"])
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


def _exc(cls, **attrs):
    e = cls("boom")
    for k, v in attrs.items():
        setattr(e, k, v)
    return e


class _Cred(Exception):
    status_code = 401


class _Quota(Exception):
    status_code = 429


class _Server(Exception):
    status_code = 503


@pytest.mark.parametrize(
    "exc",
    [
        _Cred(),
        _Quota(),
        _Server(),
        _exc(Exception, code=429),  # google.api_core style
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        TimeoutError("timed out"),
        Exception("RESOURCE_EXHAUSTED: quota exceeded"),
        Exception("401 PermissionDenied"),
    ],
)
def test_provider_failures_classify_as_outage(exc):
    assert isinstance(classify_llm_exception(exc, context="generation"), LLMUnavailableError)


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("could not parse json"),
        KeyError("verdict"),
        RuntimeError("some unrelated bug"),
    ],
)
def test_ordinary_errors_pass_through_unchanged(exc):
    """A misclassification would be worse than the status quo: it would turn a
    recoverable model error into a hard terminal abort."""
    assert classify_llm_exception(exc) is None


def test_already_classified_exception_is_returned_unchanged():
    original = LLMUnavailableError("probe said 401")
    assert classify_llm_exception(original) is original


def test_outage_message_distinguishes_credential_from_quota():
    cred = str(classify_llm_exception(_Cred(), context="generation"))
    quota = str(classify_llm_exception(_Quota(), context="generation"))
    assert "API key" in cred
    assert "rate-limited" in quota or "quota" in quota
    assert "generation" in cred  # context is surfaced for diagnosis


# ─── B-16: cloud is never evicted ──────────────────────────────────────────────


@pytest.fixture
def _clean_registry():
    from app.core import model_registry as mr

    mr._LLM_REGISTRY.clear()
    mr._PENDING_CLOSE.clear()
    yield mr
    mr._LLM_REGISTRY.clear()
    mr._PENDING_CLOSE.clear()


def test_local_lru_eviction_still_works(_clean_registry):
    mr = _clean_registry
    with patch.object(mr, "get_max_llm_instances", return_value=1):
        mr.put_llm_instance("ollama", "a", MagicMock())
        mr.put_llm_instance("ollama", "b", MagicMock())
    assert list(mr._LLM_REGISTRY.keys()) == ["ollama:b"]


def test_cloud_clients_are_never_evicted(_clean_registry):
    """A cloud client may have an in-flight billed request; closing it wastes
    the call and can abort the response."""
    mr = _clean_registry
    with patch.object(mr, "get_max_llm_instances", return_value=1):
        mr.put_llm_instance("gemini", "g", MagicMock())
        mr.put_llm_instance("nvidia", "n", MagicMock())
        mr.put_llm_instance("ollama", "x", MagicMock())
        mr.put_llm_instance("ollama", "y", MagicMock())
    keys = list(mr._LLM_REGISTRY.keys())
    assert "gemini:g" in keys
    assert "nvidia:n" in keys
    assert "ollama:y" in keys
    assert "ollama:x" not in keys  # the local one rotated instead


# ─── B-17: credential redaction by value ───────────────────────────────────────


@pytest.mark.parametrize(
    "secret",
    [
        "AIzaSyD-1234567890abcdefghijklmnopqrstu",
        "nvapi-AbCdEf0123456789XyZ",
        "sk-abcdefghijklmnopqrstuvwxyz012345",
        "hf_abcdefghijklmnopqrstuvwxyz01",
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
    from app.agent.graph import _execute_with_fallback

    async def boom():
        raise _DeadCredential("API key not valid")

    with patch("app.agent.graph.add_trace_event", AsyncMock()):
        out = await _execute_with_fallback(
            {"analysis_id": "a1", "attempts": 0}, "generation", boom, timeout_seconds=5
        )

    assert out["diagnosis_type"] == "LLM_OUTAGE"
    # Recovery budget exhausted => the graph terminates instead of retrying.
    assert out["attempts"] >= 1
    assert out["reliability_score"] == 0.0
    assert "insufficient evidence" in out["answer"].lower()
    assert "not a finding" in out["answer"].lower()
    assert [e["error_type"] for e in out["node_errors"]] == ["LLM_OUTAGE"]


@pytest.mark.asyncio
async def test_ordinary_node_error_still_allows_recovery():
    """The outage path must not swallow ordinary bugs — those should keep
    producing node_errors and leaving the recovery budget untouched."""
    from app.agent.graph import _execute_with_fallback

    async def bug():
        raise ValueError("unparseable verdict json")

    with patch("app.agent.graph.add_trace_event", AsyncMock()):
        out = await _execute_with_fallback(
            {"analysis_id": "a1", "attempts": 0}, "generation", bug, timeout_seconds=5
        )

    assert out.get("diagnosis_type") is None
    assert out["attempts"] == 0
    assert [e["error_type"] for e in out["node_errors"]] == ["ValueError"]


@pytest.mark.asyncio
async def test_budget_guard_stops_node_before_spending():
    """Once the cloud cap is spent, a node must not start another paid call."""
    from app.agent.graph import _execute_with_fallback

    called = {"n": 0}

    async def would_cost_money():
        called["n"] += 1
        return {}

    with (
        patch("app.agent.graph.add_trace_event", AsyncMock()),
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
    from app.core.config import get_model_config

    cfg = get_model_config()
    assert cfg.context_compression_provider == "off", (
        "compression provider must default to 'off'; a cloud tier pays a second "
        "full LLM call for a benefit it rarely needs"
    )
    assert cfg.context_compression_enabled is False


def test_compression_budget_exceeds_target_so_summaries_finish():
    """The cap is the budget to WRITE the summary, not the size we want. Capping
    at exactly the target truncated summaries mid-sentence."""
    from app.generation.generator import _compression_budget

    for target in (128, 300, 500, 1024):
        budget = _compression_budget(target)
        assert budget > target, f"target {target} got budget {budget} — truncates"
        assert budget >= 256, f"target {target} floor too low"


def test_compression_threshold_is_configurable():
    from app.core.config import get_model_config

    assert get_model_config().context_compression_min_tokens > 0


# ─── B-13: nvidia_base_url must actually reach the client ─────────────────────


def test_nvidia_base_url_is_read_from_config():
    """Previously dead config: the endpoint only took effect when load_dotenv
    happened to export NVIDIA_BASE_URL, so a mounted secret, a programmatic
    override, or a self-hosted gateway was silently ignored."""
    from app.core.config import get_model_config

    assert hasattr(get_model_config(), "nvidia_base_url")


def test_nvidia_client_receives_configured_base_url():
    """The wiring, end to end: a configured endpoint must land on the client."""
    import os

    from app.core import model_registry as mr
    from app.core.config import get_model_config, get_settings

    marker = "http://self-hosted-nim.internal:8000/v1"
    previous = os.environ.get("NVIDIA_BASE_URL")
    os.environ["NVIDIA_BASE_URL"] = marker
    try:
        importlib_cfg = get_model_config()
        assert importlib_cfg.nvidia_base_url == marker

        settings = get_settings()
        captured = {}

        def _fake_chat_nvidia(**kwargs):
            captured.update(kwargs)
            return MagicMock(name="chatnvidia")

        with (
            patch.dict(
                "sys.modules",
                {"langchain_nvidia_ai_endpoints": MagicMock(ChatNVIDIA=_fake_chat_nvidia)},
            ),
            patch.object(settings, "nvidia_api_key", "dummy-key", create=True),
            patch.object(mr, "get_settings", return_value=settings),
        ):
            mr._create_llm(
                provider="nvidia",
                model="some/model",
                temperature=0.0,
                max_tokens=512,
                timeout=30,
            )
        assert captured.get("base_url") == marker, (
            f"base_url did not reach ChatNVIDIA: {captured.get('base_url')!r}"
        )
    finally:
        if previous is None:
            os.environ.pop("NVIDIA_BASE_URL", None)
        else:
            os.environ["NVIDIA_BASE_URL"] = previous


# ─── B-14: provider aliases must resolve to the right context window ───────────


def test_cloud_aliases_are_not_clamped_to_the_local_window():
    """'google_genai' and 'nim' are accepted provider spellings but were missing
    from the limits table, so they fell through to the 4096 local default and
    logged a false 'evidence will be truncated' warning (audit B-14)."""
    from app.generation.generator import calculate_dynamic_num_ctx

    big = "word " * 4000  # ~20k tokens: far over local, well under cloud
    gemini = calculate_dynamic_num_ctx(big, "", "q", 512, "gemini")
    assert calculate_dynamic_num_ctx(big, "", "q", 512, "google_genai") == gemini
    nvidia = calculate_dynamic_num_ctx(big, "", "q", 512, "nvidia")
    assert calculate_dynamic_num_ctx(big, "", "q", 512, "nim") == nvidia
    # Cloud must not be pinned to the local 4096 cap.
    assert gemini > 4096
    assert nvidia > 4096


def test_local_aliases_also_resolve():
    from app.generation.generator import calculate_dynamic_num_ctx

    big = "word " * 4000
    assert calculate_dynamic_num_ctx(big, "", "q", 512, "llamacpp") == calculate_dynamic_num_ctx(
        big, "", "q", 512, "llama_cpp"
    )


def test_num_ctx_is_never_sent_to_cloud_clients():
    """The cloud context number is advisory only — sending num_ctx to a cloud
    client is a ValidationError on Gemini and ignored by NVIDIA."""
    from app.generation.generator import _invoke_kwargs_for_provider

    for provider in ("gemini", "google_genai", "nvidia", "nim"):
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
    from app.core.config import normalize_provider

    assert normalize_provider("google_genai") == "gemini"
    assert normalize_provider("nim") == "nvidia"
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
    from app.core.config import get_model_config

    real = get_model_config()
    base = {"knowledge_base_id": "64ee39d09c6292376e191982", "query": "hello"}

    class _CfgStub:
        """Minimal stand-in: the validator builds allowlists for every provider."""

        llm_provider = "gemini"
        supported_gemini_models: ClassVar[list[str]] = ["gemini-allowed-only"]
        supported_nvidia_models: ClassVar[list[str]] = ["nvidia-allowed-only"]
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
    with patch("app.core.config.get_model_config", return_value=_CfgStub("gemini-not-allowed")):
        with pytest.raises(ValidationError, match="not enabled"):
            AnalysisCreate(llm_provider="gemini", **base)

    # 2. The same request passes when the resolved default IS allowed.
    with patch("app.core.config.get_model_config", return_value=_CfgStub("gemini-allowed-only")):
        with patch("app.core.local_llm.get_discovered_llms", return_value=frozenset()):
            ok = AnalysisCreate(llm_provider="gemini", **base)
    assert ok.llm_model is None  # the caller did not ask for a specific model


def test_cross_provider_mismatch_is_still_rejected():
    from pydantic import ValidationError

    from app.api.v1.schemas.analysis import AnalysisCreate
    from app.core.config import get_model_config

    gemini = get_model_config().supported_gemini_models
    if not gemini:
        pytest.skip("no Gemini models configured")
    with patch("app.core.local_llm.get_discovered_llms", return_value=frozenset()):
        with pytest.raises(ValidationError):
            AnalysisCreate(
                knowledge_base_id="64ee39d09c6292376e191982",
                query="hi",
                llm_provider="nvidia",
                llm_model=gemini[0],
            )


# ─── B-18: provider asymmetries ──────────────────────────────────────────────


def test_nvidia_uses_the_non_deprecated_token_parameter():
    """`max_tokens` emits a DeprecationWarning on every call from
    langchain-nvidia-ai-endpoints; the OpenAI-compatible spelling is
    `max_completion_tokens`."""
    from app.core.local_llm import verification_cap_kwargs
    from app.generation.generator import _invoke_kwargs_for_provider

    for kwargs in (
        _invoke_kwargs_for_provider("nvidia", 512),
        _invoke_kwargs_for_provider("nim", 512),
        verification_cap_kwargs("nvidia", "meta/llama-3.3-70b-instruct", 512),
        verification_cap_kwargs("nim", "meta/llama-3.3-70b-instruct", 512),
    ):
        assert "max_completion_tokens" in kwargs, kwargs
        assert "max_tokens" not in kwargs, f"deprecated parameter still used: {kwargs}"


def test_gemini_and_local_keep_their_own_token_parameters():
    from app.generation.generator import _invoke_kwargs_for_provider

    assert "max_output_tokens" in _invoke_kwargs_for_provider("gemini", 512)
    assert "max_output_tokens" in _invoke_kwargs_for_provider("google_genai", 512)
    # Local OpenAI-compatible servers do still take max_tokens.
    assert "max_tokens" in _invoke_kwargs_for_provider("ollama", 512)
    assert "max_tokens" in _invoke_kwargs_for_provider("llama_cpp", 512)


def test_nvidia_client_receives_top_p():
    """Omitting top_p made cloud sampling silently diverge from the configured
    value that local clients receive."""
    from app.core import model_registry as mr
    from app.core.config import get_settings

    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    settings = get_settings()
    with (
        patch.dict("sys.modules", {"langchain_nvidia_ai_endpoints": MagicMock(ChatNVIDIA=_fake)}),
        patch.object(settings, "nvidia_api_key", "dummy-key", create=True),
        patch.object(mr, "get_settings", return_value=settings),
    ):
        mr._create_llm(provider="nvidia", model="m/x", temperature=0.0, max_tokens=512, timeout=30)
    assert "top_p" in captured, f"NVIDIA client got no top_p: {sorted(captured)}"


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
        supported_nvidia_models: ClassVar[list[str]] = ["nvidia-allowed-only"]
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

    monkeypatch.setattr(cfgmod, "get_model_config", lambda: _CfgStub("gemini-allowed-only"))
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
        supported_nvidia_models: ClassVar[list[str]] = ["nvidia-allowed-only"]
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
    Gemini/NVIDIA requests are still billed, so cloud must use the configured
    provider budget (audit B-18)."""
    from app.verification import verifier

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
    from app.verification import verifier

    class _ShortCfg:
        verification_provider = "nvidia"
        llm_timeout_seconds = 10

    monkeypatch.setattr(verifier, "NLI_PER_CALL_TIMEOUT_SECONDS", 90)
    with patch("app.core.config.get_model_config", return_value=_ShortCfg()):
        assert verifier._nli_timeout_seconds() == 90
