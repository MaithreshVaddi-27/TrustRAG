"""
TRUSTRAG — Retrieval quality analyser over stored evidence.

Reads completed analyses from MongoDB and scores the retrieved evidence
against a probe set (expected substring). Reports Recall@K, Precision@K,
MRR and the abstention breakdown per query.

Usage:
    python scripts/analyze_quality.py --expect "What is the reciprocal rank fusion constant?=sixty"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", action="append", default=[])
    ap.add_argument("--out", default="quality_results.json")
    ap.add_argument(
        "--newest",
        type=int,
        default=0,
        help=(
            "Only score the N most recent analyses (0 = all). Use this to compare "
            "a benchmark batch against the baseline batch without mixing them."
        ),
    )
    args = ap.parse_args()

    from app.persistence.mongodb import Collections, connect_db, disconnect_db, get_collection

    probes: dict[str, str] = {}
    for item in args.expect:
        q, _, expect = item.partition("=")
        probes[q.strip()] = expect.strip().lower()

    await connect_db()
    try:
        analyses = await get_collection(Collections.ANALYSES).find({}).to_list(500)
        analyses.sort(key=lambda a: a.get("created_at") or datetime.min, reverse=True)
        if args.newest > 0:
            analyses = analyses[: args.newest]
        evidence = await get_collection(Collections.EVIDENCE).find({}).to_list(5000)
        ev_by_analysis: dict[str, list[dict[str, Any]]] = {}
        for e in evidence:
            ev_by_analysis.setdefault(str(e["analysis_id"]), []).append(e)

        rows: list[dict[str, Any]] = []
        for a in analyses:
            q = str(a.get("query", ""))
            if q not in probes:
                continue
            expect = probes[q]
            evs = ev_by_analysis.get(str(a["_id"]), [])
            texts = [str(e.get("text", "")).lower() for e in evs]
            rank = next((i for i, t in enumerate(texts) if expect in t), None)
            rows.append(
                {
                    "query": q,
                    "status": a.get("status"),
                    "score": (a.get("reliability") or {}).get("score"),
                    "n_evidence": len(evs),
                    "hit": rank is not None,
                    "rank": (rank + 1) if rank is not None else None,
                    "claims": len(
                        await get_collection(Collections.CLAIMS)
                        .find({"analysis_id": a["_id"]})
                        .to_list(100)
                    ),
                }
            )

        by_query: dict[str, dict[str, Any]] = {}
        for r in rows:
            agg = by_query.setdefault(
                r["query"],
                {
                    "n": 0,
                    "hits": 0,
                    "reciprocal_rank_sum": 0.0,
                    "precision_sum": 0.0,
                    "statuses": {},
                    "scores": [],
                    "evidence_counts": [],
                },
            )
            agg["n"] += 1
            agg["hits"] += 1 if r["hit"] else 0
            agg["reciprocal_rank_sum"] += (1.0 / r["rank"]) if r["rank"] else 0.0
            agg["precision_sum"] += (1.0 / r["n_evidence"]) if r["n_evidence"] else 0.0
            agg["statuses"][r["status"]] = agg["statuses"].get(r["status"], 0) + 1
            if isinstance(r["score"], (int, float)):
                agg["scores"].append(float(r["score"]))
            agg["evidence_counts"].append(r["n_evidence"])

        out: dict[str, Any] = {}
        tot_n = tot_hits = 0
        tot_rr = tot_p = 0.0
        for q, agg in by_query.items():
            n = agg["n"]
            tot_n += n
            tot_hits += agg["hits"]
            tot_rr += agg["reciprocal_rank_sum"]
            tot_p += agg["precision_sum"]
            out[q] = {
                "n": n,
                "recall_at_k": round(agg["hits"] / n, 4) if n else 0,
                "precision_at_k": round(agg["precision_sum"] / n, 4) if n else 0,
                "mrr": round(agg["reciprocal_rank_sum"] / n, 4) if n else 0,
                "statuses": agg["statuses"],
                "mean_score": (
                    round(sum(agg["scores"]) / len(agg["scores"]), 4) if agg["scores"] else None
                ),
                "mean_evidence": (
                    round(sum(agg["evidence_counts"]) / len(agg["evidence_counts"]), 2)
                    if agg["evidence_counts"]
                    else 0
                ),
            }
        out["_overall"] = {
            "n": tot_n,
            "recall_at_k": round(tot_hits / tot_n, 4) if tot_n else 0,
            "precision_at_k": round(tot_p / tot_n, 4) if tot_n else 0,
            "mrr": round(tot_rr / tot_n, 4) if tot_n else 0,
        }
        print(json.dumps(out, indent=2))
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        print(f"[quality] wrote {args.out}")
    finally:
        await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
