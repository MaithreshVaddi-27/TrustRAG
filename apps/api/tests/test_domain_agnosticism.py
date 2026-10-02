"""
Domain-agnosticism regressions (audit G-4).

TrustRAG must answer from ANY knowledge base. Several subsystems previously
encoded one subject matter and silently degraded for everything else:

- `detect_chunk_zone` matched literal textbook/policy keywords, so a code,
  contract, paper or prose corpus was classified as BODY for every chunk and
  the BM25 zone weights never applied.
- `extract_claim_triple_heuristic` carried commerce/ops verbs only, and looped
  by predicate-list order rather than sentence order.
- Prompt few-shot examples named one subject, biasing the model toward it.

(URL document ingestion was removed 2026-10-01: uploads are the only intake,
so the former allowlist-extensibility section has no target. History in git.)

These tests pin the *behaviour across several domains*, not one domain, so
re-introducing a single-domain assumption fails loudly.
"""

from __future__ import annotations

import pytest

# ── Zone detection across domains ───────────────────────────────────────────

_ZONE_CASES = [
    pytest.param(
        "Northwind Retention Policy\nAccounts close after 14 days.",
        "title",
        id="policy",
    ),
    pytest.param("# Getting Started\nInstall the package with pip.", "title", id="source_readme"),
    pytest.param("SYSTEM DESIGN DOCUMENT\nRevision history follows.", "title", id="spec"),
    pytest.param("Article IV Limitation of Liability\nTerms follow.", "title", id="contract"),
    pytest.param("On the Origin of Species\nAbstract follows.", "title", id="paper"),
    pytest.param("Effective: 2026-01-01\nBody follows.", "metadata", id="date_field"),
    pytest.param("Version: 2.1\nDetails.", "metadata", id="semver_field"),
    pytest.param("Revision: a3f9c21b\nDetails.", "metadata", id="git_hash_field"),
    pytest.param("DOI: 10.1234/xyz\nAbstract follows.", "metadata", id="doi_field"),
    pytest.param("Author: Jane Smith\nThe rest.", "metadata", id="author_field"),
    pytest.param("Owner: platform-team\nThe rest.", "metadata", id="owner_field"),
    pytest.param("Summary:\nKey findings are below.", "summary", id="summary_field"),
    pytest.param(
        "This function validates the token before issuing it upstream.",
        "body",
        id="code_prose",
    ),
    pytest.param(
        "Note: the following section explains the configuration in some detail.",
        "body",
        id="prose_with_colon_is_not_metadata",
    ),
    pytest.param(
        "Section 12 of the agreement applies to all parties.",
        "body",
        id="prose_mentioning_section_is_not_outline",
    ),
    pytest.param(
        "Normal paragraph about widget tolerances and thermal limits.",
        "body",
        id="plain_body",
    ),
]


@pytest.mark.parametrize(("text", "expected"), _ZONE_CASES)
def test_zone_detection_is_domain_neutral(text: str, expected: str) -> None:
    from app.rag.ingestion.preprocessor import detect_chunk_zone

    assert detect_chunk_zone(text, page=1) == expected


def test_legacy_textbook_markers_still_detected() -> None:
    """Structural outline markers are kept — they are not subject-specific."""
    from app.rag.ingestion.preprocessor import detect_chunk_zone

    text = "Information Retrieval Systems\nUNIT-2 Syllabus\nCataloging"
    assert detect_chunk_zone(text, page=1) == "title"


# ── Claim triple extraction across domains ───────────────────────────────────

_TRIPLE_CASES = [
    pytest.param(
        "The retention policy allows returns within 30 days.",
        "The retention policy",
        id="policy",
    ),
    pytest.param(
        "The function validates the token before issuing it.",
        "The function",
        id="code",
    ),
    pytest.param(
        "The contract terminates upon material breach.",
        "The contract",
        id="contract",
    ),
    pytest.param(
        "The paper correlates dosage with recovery rate.",
        "The paper",
        id="science",
    ),
]


@pytest.mark.parametrize(("claim", "expected_subject"), _TRIPLE_CASES)
def test_claim_triples_split_on_first_relational_verb(claim: str, expected_subject: str) -> None:
    from app.rag.verification.verifier import extract_claim_triple_heuristic

    subject, predicate, obj = extract_claim_triple_heuristic(claim)
    assert subject == expected_subject
    assert predicate
    assert obj


def test_claim_triple_scans_sentence_order_not_verb_list_order() -> None:
    """Regression: looping predicates-first made a late low-priority verb win.

    "The rate is 5% and it allows records." produced the nonsensical subject
    "The rate is 5% and it" because "allows" was searched before "is". The
    subject must be the text before the FIRST relational verb in the sentence.
    """
    from app.rag.verification.verifier import extract_claim_triple_heuristic

    subject, predicate, _ = extract_claim_triple_heuristic("The rate is 5% and it allows records.")
    assert subject == "The rate"
    assert predicate == "is"


def test_predicate_vocabulary_spans_multiple_domains() -> None:
    from app.rag.verification.verifier import _PREDICATE_VERBS

    # code, legal, scientific, and general relational verbs all present
    for verb in ("returns", "raises", "imports", "terminates", "obliges", "correlates", "is"):
        assert verb in _PREDICATE_VERBS, verb
    # The commerce-only verb from the old list is gone. Pinned literally (not
    # via a synonym) so a broad vocabulary regression is caught.
    assert "refunds" not in _PREDICATE_VERBS


# ── Prompts must not exemplify one subject ───────────────────────────────────


def test_fused_verify_example_is_domain_neutral() -> None:
    """The fused decompose+verify few-shot example must not name a subject.

    An example that says "Records are available within 30 days" biases a
    domain-agnostic verifier toward commerce-shaped claims.
    """
    from app.rag.verification.verifier import FUSED_DECOMPOSE_VERIFY_PROMPT_TEMPLATE as T

    assert "Record" not in T
    assert "record" not in T
    assert "shape" in T.lower(), "the example must be framed as a shape"


def test_generation_scope_block_is_not_structure_locked() -> None:
    """The <scope> block must not enumerate one corpus's structural vocabulary."""
    from app.rag.generation.generator import GROUNDING_SYSTEM_PROMPT as P

    scope = P.split("<scope>", 1)[1].split("</scope>", 1)[0].lower()
    # It should delegate structure to the Context, not list subject headings.
    for word in ("syllabus", "textbook", "chapter", "unit"):
        assert word not in scope, f"{word!r} re-locks the prompt to one corpus"
