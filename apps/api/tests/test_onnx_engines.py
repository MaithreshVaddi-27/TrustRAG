"""
Tests for the ONNX embedding and reranking engines (audit T-8).

`onnx_embeddings.py` and `onnx_reranker.py` had no fake-session fixture, so the
engines were almost entirely untested — which left the *batching* logic
unverified. That batching is not an optimisation detail: both files chunk
their inputs specifically to bound peak RAM (audit B-1 removed 177 MB of Torch
import from this path, and the chunk size is what keeps it there). A regression
that dropped the chunking would silently restore the memory blow-up with no test
failing.

These inject a fake `ort.InferenceSession` and assert the batching, the
ordering, the empty-input handling, and the BGE query-instruction behaviour.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

EMBED_DIM = 384


# ─── Fakes ───────────────────────────────────────────────────────────────────


class _Named:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeSession:
    """Stands in for ort.InferenceSession.

    Records every `run()` call so the chunking can be asserted, and returns a
    deterministic row per input so ordering is verifiable end to end.
    """

    def __init__(
        self, dim: int = EMBED_DIM, input_names: tuple[str, ...] = ("input_ids", "attention_mask")
    ):
        self.dim = dim
        self._input_names = input_names
        self.run_calls: list[dict] = []

    def get_inputs(self):
        return [_Named(n) for n in self._input_names]

    def get_outputs(self):
        out = _Named("last_hidden_state")
        out.shape = [None, self.dim]
        return [out]

    def run(self, output_names, inputs):
        self.run_calls.append(inputs)
        n = int(np.asarray(inputs["input_ids"]).shape[0])
        # Deterministic, distinguishable rows so mis-ordering is detectable.
        base = len(self.run_calls) * 1000
        out = np.zeros((n, self.dim), dtype=np.float32)
        for i in range(n):
            out[i, 0] = float(base + i)
        return [out]


class _FakeRerankSession(_FakeSession):
    """Returns one logit per pair so scores are order-traceable."""

    def __init__(
        self,
        dim: int = 8,
        input_names: tuple[str, ...] = ("input_ids", "attention_mask", "token_type_ids"),
    ):
        super().__init__(dim=dim, input_names=input_names)
        self.logits = None

    def run(self, output_names, inputs):
        self.run_calls.append(inputs)
        n = int(np.asarray(inputs["input_ids"]).shape[0])
        base = len(self.run_calls) * 1000
        self.logits = np.array(
            [[float(base + i)] for i in range(n)],
            dtype=np.float32,
        )
        return [self.logits]


def _fake_tokenizer():
    tok = MagicMock()

    def _call(texts, *args, **kwargs):
        single = isinstance(texts, str)
        seq = [texts] if single else list(texts)
        n = len(seq)
        return {
            "input_ids": np.ones((n, 8), dtype=np.int64),
            "attention_mask": np.ones((n, 8), dtype=np.int64),
            "token_type_ids": np.zeros((n, 8), dtype=np.int64),
        }

    tok.side_effect = _call
    return tok


def _make_embedder(session, **kwargs):
    """Construct ONNXBGEEmbeddings without touching onnxruntime or transformers."""
    from app.core import onnx_embeddings as mod

    tok = _fake_tokenizer()
    with (
        patch.object(mod, "_ORT_AVAILABLE", True),
        patch("transformers.AutoTokenizer.from_pretrained", return_value=tok),
    ):
        # Patch InferenceSession *after* import so the module global is replaced.
        with patch.object(mod.ort, "InferenceSession", return_value=session):
            emb = mod.ONNXBGEEmbeddings(
                model_path="/fake/model.onnx",
                tokenizer_name=kwargs.pop("tokenizer_name", "BAAI/bge-small-en-v1.5"),
                **kwargs,
            )
    emb.tokenizer = tok  # our instrumented tokenizer
    return emb


def _make_reranker(session, **kwargs):
    """ONNXReranker imports onnxruntime lazily inside _initialize and also
    configures SessionOptions, so the real (installed) module is patched."""
    import onnxruntime as ort

    from app.core import onnx_reranker as mod

    tok = _fake_tokenizer()
    with (
        patch("transformers.AutoTokenizer.from_pretrained", return_value=tok),
        patch.object(ort, "InferenceSession", return_value=session),
        patch.object(ort, "SessionOptions", MagicMock()),
        patch.object(ort, "GraphOptimizationLevel", MagicMock()),
    ):
        rr = mod.ONNXCrossEncoder(model_path="/fake/rerank.onnx", **kwargs)
    rr._tokenizer = tok
    return rr


# ─── Embeddings ──────────────────────────────────────────────────────────────


def test_embeddings_are_chunked_to_bound_ram():
    """75 documents must be inferred in batches of ≤32. One giant call is
    exactly the RAM spike the chunking exists to prevent."""
    session = _FakeSession()
    emb = _make_embedder(session)

    docs = [f"doc {i}" for i in range(75)]
    out = emb.embed_documents(docs)

    assert len(out) == 75, "lost or duplicated documents"
    # 75 / 32 -> 3 batches
    assert len(session.run_calls) == 3, f"expected 3 chunks, got {len(session.run_calls)}"
    for call in session.run_calls:
        assert np.asarray(call["input_ids"]).shape[0] <= 32, "a chunk exceeded 32 inputs"


def test_embedding_chunk_sizes_are_exact():
    session = _FakeSession()
    emb = _make_embedder(session)
    emb.embed_documents([f"d{i}" for i in range(64)])
    sizes = [int(np.asarray(c["input_ids"]).shape[0]) for c in session.run_calls]
    assert sizes == [32, 32], f"expected [32, 32], got {sizes}"


def test_embedding_output_preserves_input_order():
    """Chunked concatenation must not reorder rows — a shuffle would attach
    evidence to the wrong chunk and silently corrupt retrieval."""
    session = _FakeSession()
    emb = _make_embedder(session)
    docs = [f"doc{i}" for i in range(70)]
    out = emb.embed_documents(docs)

    firsts = [row[0] for row in out]
    assert firsts == sorted(firsts), f"embedding order scrambled: {firsts[:6]}..."
    assert len(set(firsts)) == len(firsts), "duplicate embeddings produced"


def test_embed_query_applies_the_bge_instruction_exactly_once():
    """BGE retrieval quality depends on the query prefix. Double-prefixing it
    (a naive `instruction + text` on already-instructed input) degrades results
    without erroring."""
    session = _FakeSession()
    emb = _make_embedder(session, tokenizer_name="BAAI/bge-small-en-v1.5")
    assert emb._is_bge is True

    emb.embed_query("what is the token lifetime?")
    seen = emb.tokenizer.call_args_list[0].args[0][0]
    assert seen.count(emb._query_instruction) == 1, f"instruction repeated: {seen!r}"
    assert seen.startswith(emb._query_instruction), f"instruction missing: {seen!r}"


def test_non_bge_tokenizer_gets_no_instruction():
    session = _FakeSession()
    emb = _make_embedder(session, tokenizer_name="some/other-model")
    assert emb._is_bge is False
    emb.embed_query("plain text")
    seen = emb.tokenizer.call_args_list[0].args[0][0]
    assert seen == "plain text", f"instruction leaked to a non-BGE model: {seen!r}"


def test_embed_documents_with_empty_input_returns_empty():
    session = _FakeSession()
    emb = _make_embedder(session)
    assert emb.embed_documents([]) == []
    assert session.run_calls == [], "an empty batch still called the session"


def test_embed_query_returns_a_flat_float_list():
    session = _FakeSession()
    emb = _make_embedder(session)
    vec = emb.embed_query("hello")
    assert isinstance(vec, list)
    assert len(vec) == EMBED_DIM
    assert all(isinstance(x, float) for x in vec)


@pytest.mark.asyncio
async def test_async_wrappers_match_the_sync_results():
    """The graph calls aembed_query; if it diverged from embed_query the cache
    and the retrieval path would use different vectors."""
    # Sentinels are per-session, so each comparison uses a fresh engine and the
    # async call runs first on it.
    emb = _make_embedder(_FakeSession())
    got_async = await emb.aembed_query("hello")

    fresh = _make_embedder(_FakeSession())
    assert got_async == fresh.embed_query("hello")

    emb2 = _make_embedder(_FakeSession())
    docs_async = await emb2.aembed_documents(["a", "b"])

    fresh2 = _make_embedder(_FakeSession())
    assert docs_async == fresh2.embed_documents(["a", "b"])


def test_empty_input_size_does_not_hardcode_384():
    """A future model with a different dim must not silently return a
    wrongly-shaped zero vector from the empty path."""
    session = _FakeSession(dim=768)
    emb = _make_embedder(session)
    out = emb._encode_batch([])
    assert out.shape == (0, 768), f"empty batch used a hardcoded dim: {out.shape}"


# ─── Reranker ────────────────────────────────────────────────────────────────


def test_reranker_respects_its_batch_size():
    """Same RAM argument as the embedder: 20 candidates x fan-out must not be
    inferred in one shot."""
    session = _FakeRerankSession()
    rr = _make_reranker(session)
    pairs = [("q", f"doc {i}") for i in range(20)]
    scores = rr.predict(pairs, batch_size=8)

    assert len(scores) == 20, f"expected 20 scores, got {len(scores)}"
    assert len(session.run_calls) == 3, f"expected 3 batches of ≤8, got {len(session.run_calls)}"
    for call in session.run_calls:
        assert np.asarray(call["input_ids"]).shape[0] <= 8


def test_reranker_empty_input_is_an_empty_array():
    session = _FakeRerankSession()
    rr = _make_reranker(session)
    out = rr.predict([])
    assert len(out) == 0
    assert session.run_calls == []


def test_reranker_score_order_matches_pair_order():
    session = _FakeRerankSession()
    rr = _make_reranker(session)
    pairs = [("q", f"d{i}") for i in range(12)]
    scores = [float(s) for s in rr.predict(pairs, batch_size=5)]
    # Each batch carries a distinct increasing sentinel block, so a cross-batch
    # reorder or a dropped/duplicated row shows up as a non-monotonic sequence.
    assert scores == sorted(scores), f"reranker scores reordered: {scores}"
    assert len(scores) == len(pairs)
    assert len(set(scores)) == len(scores), f"duplicate scores: {scores}"


def test_reranker_only_sends_inputs_the_exported_graph_declares():
    """A cross-encoder exported without token_type_ids will error if we send
    one. The session's declared input set must drive what is passed."""
    session = _FakeRerankSession(input_names=("input_ids", "attention_mask"))
    rr = _make_reranker(session)
    rr.predict([("q", "doc")], batch_size=4)

    sent = set(session.run_calls[0])
    assert sent == {"input_ids", "attention_mask"}, f"sent unexpected inputs: {sent}"
    assert "token_type_ids" not in sent


def test_reranker_sends_token_type_ids_when_the_graph_expects_them():
    session = _FakeRerankSession(input_names=("input_ids", "attention_mask", "token_type_ids"))
    rr = _make_reranker(session)
    rr.predict([("q", "doc")], batch_size=4)
    assert "token_type_ids" in session.run_calls[0]


def test_reranker_handles_two_dimensional_logits():
    """A (N,1) logit head must collapse to N scores, not N x 1."""
    session = _FakeRerankSession()
    rr = _make_reranker(session)
    scores = rr.predict([("q", f"d{i}") for i in range(3)], batch_size=8)
    assert np.asarray(scores).shape == (3,), f"bad score shape: {np.asarray(scores).shape}"


def test_reranker_handles_one_dimensional_logits():
    class _Flat(_FakeSession):
        def run(self, output_names, inputs):
            self.run_calls.append(inputs)
            n = int(np.asarray(inputs["input_ids"]).shape[0])
            return [np.arange(n, dtype=np.float32)]

    session = _Flat(input_names=("input_ids", "attention_mask"))
    rr = _make_reranker(session)
    scores = rr.predict([("q", f"d{i}") for i in range(4)], batch_size=2)
    assert np.asarray(scores).shape == (4,)
