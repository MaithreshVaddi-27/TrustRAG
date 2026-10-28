#!/usr/bin/env python3
"""Run optional Ragas faithfulness and context-recall evaluation locally."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "apps" / "api" / "config" / "evaluation" / "local-providers.yaml"
DATASET_DEFAULT = ROOT / "apps" / "api" / "tests" / "eval" / "datasets" / "baseline_v1.jsonl"


async def run_metrics(rows: list[dict], judge: object) -> list[dict]:
    eligible = [
        row
        for row in rows
        if row.get("gold_evidence") and row.get("gold_answer_keywords")
    ]
    if not eligible:
        return [
            {"query_id": row["id"], "faithfulness": None, "context_recall": None}
            for row in rows
        ]
    from ragas.metrics.collections import ContextRecall, Faithfulness

    faithfulness = Faithfulness(llm=judge)
    context_recall = ContextRecall(llm=judge)
    scores = []
    for row in rows:
        contexts = [item["snippet"] for item in row.get("gold_evidence", [])]
        reference = " ".join(row.get("gold_answer_keywords", []))
        if not contexts or not reference:
            scores.append({"query_id": row["id"], "faithfulness": None, "context_recall": None})
            continue
        sample = {
            "user_input": row["query"],
            "response": reference,
            "retrieved_contexts": contexts,
            "reference": reference,
        }
        faith = await faithfulness.ascore(
            user_input=sample["user_input"],
            response=sample["response"],
            retrieved_contexts=sample["retrieved_contexts"],
        )
        recall = await context_recall.ascore(
            user_input=sample["user_input"],
            retrieved_contexts=sample["retrieved_contexts"],
            reference=sample["reference"],
        )
        scores.append(
            {"query_id": row["id"], "faithfulness": faith.value, "context_recall": recall.value}
        )
        print(f"{row['id']}: faithfulness={faith.value} context_recall={recall.value}")
    return scores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--base-url", help="Override the local OpenAI-compatible judge URL")
    parser.add_argument("--model", help="Override the local judge model name")
    args = parser.parse_args()

    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    try:
        import yaml
        from openai import AsyncOpenAI
        from ragas.llms import llm_factory
    except ImportError as exc:
        parser.error(f"Install the optional extra with `uv sync --extra eval-ragas`: {exc}")

    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    base_url = args.base_url or profile["base_url"]
    parsed = urlsplit(base_url)
    try:
        loopback = parsed.hostname == "localhost" or (
            parsed.hostname is not None and ip_address(parsed.hostname).is_loopback
        )
    except ValueError:
        loopback = False
    if parsed.scheme != "http" or not loopback or parsed.username or parsed.password:
        parser.error("Ragas judge must use an HTTP loopback URL without credentials")

    model_name = args.model or profile["model"]
    client = AsyncOpenAI(api_key="local-only", base_url=base_url)
    judge = llm_factory(model_name, provider="openai", client=client)
    rows = [
        json.loads(line)
        for line in Path(args.dataset).read_text(encoding="utf-8").splitlines()
    ]
    scores = asyncio.run(run_metrics(rows, judge))

    valid = [row for row in scores if row["faithfulness"] is not None]
    output = {
        "dataset": Path(args.dataset).name,
        "judge": {"provider": "local OpenAI-compatible", "model": model_name, "base_url": base_url},
        "metrics": {
            "faithfulness": (
                sum(row["faithfulness"] for row in valid) / len(valid) if valid else None
            ),
            "context_recall": (
                sum(row["context_recall"] for row in valid) / len(valid) if valid else None
            ),
            "scored_queries": len(valid),
            "skipped_queries": len(scores) - len(valid),
        },
        "queries": scores,
        "limitations": (
            "Gold snippets and keywords are proxies; validate Ragas scores "
            "on a human-labeled set."
        ),
    }
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
