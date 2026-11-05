"""
Dataset validation for the security_v0.jsonl boundary evaluation dataset.

Guards the security dataset: schema integrity, unique IDs, boundary coverage,
and cross-lingual balance across English, Hindi, and code-mixed inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
SECURITY_DATASET_PATH = EVAL_DIR / "datasets" / "security_v0.jsonl"

ALLOWED_BOUNDARIES = {"user_query", "ingest", "retrieved_chunk"}
ALLOWED_LANGUAGES = {"en", "hi", "mixed"}
ALLOWED_LABELS = {"benign", "injection"}
ALLOWED_PILOT_ACTIONS = {"annotate", "block"}

REQUIRED_KEYS = {
    "id",
    "boundary",
    "language",
    "text",
    "label",
    "attack_family",
    "expected_pilot_action",
    "notes",
}


def load_security_dataset() -> list[dict]:
    rows = []
    assert SECURITY_DATASET_PATH.exists(), f"Missing dataset: {SECURITY_DATASET_PATH}"
    with open(SECURITY_DATASET_PATH, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    f"{SECURITY_DATASET_PATH}:{lineno}: invalid JSON: {exc}"
                ) from exc
    return rows


def test_security_dataset_query_count_and_unique_ids():
    rows = load_security_dataset()
    assert len(rows) >= 16, f"security_v0 must contain ≥16 examples, got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == len(ids), f"Duplicate IDs detected: {ids}"


def test_security_dataset_schema():
    for row in load_security_dataset():
        missing = REQUIRED_KEYS - set(row)
        assert not missing, f"{row.get('id')}: missing keys {missing}"
        assert row["text"] and isinstance(row["text"], str)
        assert row["boundary"] in ALLOWED_BOUNDARIES, f"{row['id']}: bad boundary {row['boundary']}"
        assert row["language"] in ALLOWED_LANGUAGES, f"{row['id']}: bad language {row['language']}"
        assert row["label"] in ALLOWED_LABELS, f"{row['id']}: bad label {row['label']}"
        assert row["expected_pilot_action"] in ALLOWED_PILOT_ACTIONS, (
            f"{row['id']}: bad pilot action {row['expected_pilot_action']}"
        )
        if row["label"] == "benign":
            assert row["attack_family"] is None, (
                f"{row['id']}: benign case should have null attack_family"
            )
        else:
            assert row["attack_family"], f"{row['id']}: injection case must name attack_family"


def test_security_dataset_coverage():
    rows = load_security_dataset()
    boundaries = {r["boundary"] for r in rows}
    assert boundaries == ALLOWED_BOUNDARIES, (
        f"Missing boundary coverage: {ALLOWED_BOUNDARIES - boundaries}"
    )

    languages = {r["language"] for r in rows}
    assert "en" in languages and "hi" in languages, "Must cover English and Hindi"

    benign = [r for r in rows if r["label"] == "benign"]
    injection = [r for r in rows if r["label"] == "injection"]
    assert len(benign) >= 4, f"Need ≥4 benign controls, got {len(benign)}"
    assert len(injection) >= 8, f"Need ≥8 injection examples, got {len(injection)}"
