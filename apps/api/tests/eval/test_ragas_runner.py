"""Contract tests for the offline RAGAS artifact reader."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "run_ragas_eval.py"

spec = importlib.util.spec_from_file_location("run_ragas_eval", SCRIPT)
assert spec and spec.loader
ragas_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ragas_runner)


def test_load_samples_reads_actual_run_data(tmp_path: Path) -> None:
    artifact = tmp_path / "baseline.json"
    artifact.write_text(
        json.dumps(
            {
                "dataset": "baseline_v1.jsonl",
                "config_version": "1.28",
                "queries": [
                    {
                        "query_id": "q001",
                        "evaluation_sample": {
                            "user_input": "What is the retention period?",
                            "response": "Thirty days.",
                            "retrieved_contexts": ["Tokens are retained for 30 days."],
                            "reference": "30 days",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    results, samples = ragas_runner.load_samples(artifact)

    assert results["config_version"] == "1.28"
    assert samples == [
        {
            "query_id": "q001",
            "user_input": "What is the retention period?",
            "response": "Thirty days.",
            "retrieved_contexts": ["Tokens are retained for 30 days."],
            "reference": "30 days",
        }
    ]


@pytest.mark.parametrize(
    "sample",
    [None, {"user_input": "q", "response": "a"}],
)
def test_load_samples_rejects_incomplete_run_data(tmp_path: Path, sample: dict | None) -> None:
    artifact = tmp_path / "legacy.json"
    artifact.write_text(
        json.dumps({"queries": [{"query_id": "q001", "evaluation_sample": sample}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="lacks a complete evaluation_sample"):
        ragas_runner.load_samples(artifact)
