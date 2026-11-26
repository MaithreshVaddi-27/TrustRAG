"""
The evaluation package is checked by the test suite, not by hand.

`scripts/eval/` holds the ground truth and the harness that scores it. If
the two drift apart — a probe whose expected substring is no longer in the
corpus, a harness that silently scores nothing — the evaluation would still
"run" and still produce a JSON file, and the number would be wrong. These
tests make that impossible to miss.

They are cheap and deterministic: no model, no network, no live services.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.eval.eval_set import (
    CORPUS,
    PROBES,
    answerable_probes,
    unanswerable_probes,
)

_EVAL_DIR = Path(__file__).resolve().parent.parent / "scripts" / "eval"


def test_the_corpus_is_the_four_document_set():
    """The corpus is the ground truth's other half: it must not be empty,
    and every document must be non-empty text."""
    assert len(CORPUS) == 4, f"the corpus changed: {len(CORPUS)} documents"
    for name, text in CORPUS:
        assert text.strip(), f"{name} is empty"
        assert len(text) > 200, f"{name} is suspiciously short ({len(text)} chars)"


def test_the_probe_set_covers_both_halves():
    """Both halves must be present. A set with no unanswerable probe cannot
    score abstention, and a set with no answerable probe cannot score
    answering."""
    answerable = answerable_probes()
    unanswerable = unanswerable_probes()
    assert len(answerable) == 27, f"answerable probes: {len(answerable)}"
    assert len(unanswerable) == 6, f"unanswerable probes: {len(unanswerable)}"
    assert len(PROBES) == 33, f"total probes: {len(PROBES)}"


def _flatten(text: str) -> str:
    """Collapse every whitespace run to a single space, case-folded.

    The corpus is hard-wrapped, so a phrase can straddle a line break:
    ``"a 429 response means the client exceeded its\nquota."``. The stored
    chunk keeps that break (``normalize_text`` preserves line breaks — the
    chunking heuristics depend on them), but the model reads the chunk and
    renders the phrase on one line, and the harness scores the *answer*. So
    "is this answerable from the corpus" is a whitespace-insensitive
    question, and the check has to be too.
    """
    return " ".join(text.split()).lower()


def test_every_answerable_probe_is_answerable_from_the_corpus():
    """The expected substring must actually be derivable from the corpus.

    This is the check that catches a corpus edit which quietly invalidates a
    probe: the probe would then be scored as a miss on every model, and the
    accuracy number would fall for a reason that has nothing to do with the
    model under test.
    """
    corpus = _flatten("\n".join(text for _, text in CORPUS))
    for query, expected in answerable_probes():
        assert expected.strip(), f"{query!r} has no expected substring"
        assert _flatten(expected) in corpus, (
            f"{query!r} expects {expected!r}, which is not in the corpus"
        )


def test_no_unanswerable_probe_has_its_expected_string_in_the_corpus():
    """An unanswerable probe whose answer IS in the corpus would punish a
    correct model for answering."""
    corpus = _flatten("\n".join(text for _, text in CORPUS))
    for query in unanswerable_probes():
        assert query.strip(), "an unanswerable probe has no query"
        # The unanswerable probes carry no expected string by construction
        # (answerable_probes()/unanswerable_probes() split on None), but if
        # one ever does, it must not be sitting in the corpus.
        expected = ""
        for q, a in PROBES:
            if q == query:
                expected = a or ""
                break
        if expected:
            assert _flatten(expected) not in corpus, (
                f"{query!r} is marked unanswerable but {expected!r} is in the corpus"
            )


def test_no_probe_is_duplicated():
    queries = [q for q, _ in PROBES]
    assert len(queries) == len(set(queries)), "the probe set contains a duplicate query"


def test_the_harness_imports_the_ground_truth_from_the_package():
    """The harness must score against the package's ground truth, not a
    copy of it. A duplicated ground truth is how an evaluation starts
    reporting a stale number."""
    source = (_EVAL_DIR / "eval_accuracy.py").read_text(encoding="utf-8")
    assert "from scripts.eval.eval_set import" in source, (
        "the harness does not import the ground truth from the eval package"
    )

    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert {"CORPUS", "PROBES"} <= imported, (
        f"the harness imports {sorted(imported)} — it needs CORPUS and PROBES"
    )


def test_the_matrix_driver_runs_the_packaged_harness():
    """The matrix must drive the packaged harness, not a path that no
    longer exists, and it must restore the shipped configuration however
    it ends."""
    source = (_EVAL_DIR / "run_matrix.sh").read_text(encoding="utf-8")
    assert "scripts/eval/eval_accuracy.py" in source, (
        "the matrix driver does not run the packaged harness"
    )
    assert "trap restore EXIT" in source, "the matrix driver does not restore models.yaml on exit"


def test_the_eval_package_is_importable_as_a_package():
    import scripts.eval as pkg

    assert pkg.__all__ == ["eval_accuracy", "eval_set"]


@pytest.mark.parametrize("name", ["eval_set.py", "eval_accuracy.py", "run_matrix.sh", "README.md"])
def test_every_eval_file_is_present(name):
    assert (_EVAL_DIR / name).is_file(), f"scripts/eval/{name} is missing"
