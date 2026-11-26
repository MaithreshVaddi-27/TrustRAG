"""
TRUSTRAG — HTTP-level API benchmark (black box, against a running server).

Measures API p50/p95/p99 for the analysis lifecycle and read endpoints, plus
a coarse CPU/RAM view of the server process.

Usage:
    python scripts/bench_api.py --base-url http://127.0.0.1:8000 --runs 5
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench_auth import register_or_login


def _pct(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((pct / 100.0) * len(ordered)) - 1))
    return round(ordered[idx], 2)


def summarize(name: str, values: list[float], unit: str = "ms") -> dict[str, Any]:
    if not values:
        return {"name": name, "unit": unit, "n": 0}
    return {
        "name": name,
        "unit": unit,
        "n": len(values),
        "min": round(min(values), 2),
        "p50": _pct(values, 50),
        "p95": _pct(values, 95),
        "p99": _pct(values, 99),
        "max": round(max(values), 2),
        "mean": round(statistics.mean(values), 2),
    }


SEED_DOC = """TrustRAG Retrieval Policy

The hybrid retrieval policy combines dense semantic search with sparse
lexical search. Dense retrieval uses BGE-small embeddings computed locally
through ONNX Runtime. Sparse retrieval uses BM25 style term weights with
server side inverse document frequency applied by Qdrant.

Reciprocal rank fusion merges the two ranked lists. The fusion constant is
sixty. Only the top twenty fused candidates are considered for reranking.

The reranker is a cross encoder based on MS Marco MiniLM. It scores each
query and segment pair jointly and sorts the candidates by relevance.

Temporal filtering excludes segments whose parent document is not effective
at the reference time. A document may declare an effective from date and an
effective until date. Segments outside that window are dropped before the
context is assembled.

Abstention is a first class outcome. When the evidence does not support a
grounded response the pipeline must abstain rather than guess. The verdict
engine computes an evidence coverage ratio and a contradiction rate from the
verified claims. Answers below the abstain threshold are withheld.
"""

PROBES = [
    "What is the reciprocal rank fusion constant?",
    "How many fused candidates are considered before reranking?",
    "Which embedding model does dense retrieval use?",
    "What happens when the evidence does not support an answer?",
]


async def _setup_kb(client: httpx.AsyncClient, base_url: str, token: str) -> str:
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        f"{base_url}/api/v1/knowledge-bases",
        headers=h,
        json={"name": "bench-api-kb", "description": "benchmark"},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"kb create failed: {r.status_code} {r.text[:300]}")
    kb_id = r.json()["id"]

    r = await client.post(
        f"{base_url}/api/v1/knowledge-bases/{kb_id}/documents",
        headers=h,
        files={"file": ("policy.txt", SEED_DOC.encode(), "text/plain")},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload failed: {r.status_code} {r.text[:300]}")
    doc_id = r.json()["id"]
    # Wait for background indexing to land.
    for _ in range(120):
        await asyncio.sleep(0.5)
        d = await client.get(f"{base_url}/api/v1/documents/{doc_id}", headers=h)
        if d.status_code == 200 and d.json().get("ingestion_status") in (
            "completed",
            "degraded",
            "failed",
        ):
            break
    return kb_id


async def main() -> None:
    import asyncio

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="bench_api_results.json")
    args = ap.parse_args()

    results: dict[str, Any] = {"base_url": args.base_url, "runs": args.runs}
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        token, _email = await register_or_login(client, args.base_url)
        h = {"Authorization": f"Bearer {token}"}
        kb_id = await _setup_kb(client, args.base_url, token)
        results["kb_id"] = kb_id

        # ── Read endpoint latency (cheap paths) ────────────────────────────
        reads: dict[str, list[float]] = {
            "health": [],
            "models_providers": [],
            "knowledge_bases": [],
            "metrics": [],
        }
        for _ in range(args.runs):
            for name, path in [
                ("health", "/api/v1/health"),
                ("models_providers", "/api/v1/models/providers"),
                ("knowledge_bases", "/api/v1/knowledge-bases"),
                ("metrics", "/api/v1/metrics"),
            ]:
                t0 = time.perf_counter()
                r = await client.get(f"{args.base_url}{path}", headers=h)
                reads[name].append((time.perf_counter() - t0) * 1000)
                if name == "health":
                    assert r.status_code == 200, r.text[:200]
        for k, v in reads.items():
            results[k] = summarize(k, v)

        # ── Analysis lifecycle ─────────────────────────────────────────────
        create_ms: list[float] = []
        full_ms: list[float] = []
        statuses: dict[str, int] = {}
        scores: list[float] = []
        for probe in PROBES:
            for _ in range(args.runs):
                t0 = time.perf_counter()
                r = await client.post(
                    f"{args.base_url}/api/v1/analyses",
                    headers=h,
                    json={"knowledge_base_id": kb_id, "query": probe},
                )
                create_ms.append((time.perf_counter() - t0) * 1000)
                if r.status_code not in (200, 201):
                    statuses[f"http_{r.status_code}"] = statuses.get(f"http_{r.status_code}", 0) + 1
                    continue
                aid = r.json()["id"]
                deadline = time.time() + 600
                while time.time() < deadline:
                    await asyncio.sleep(0.4)
                    d = await client.get(f"{args.base_url}/api/v1/analyses/{aid}", headers=h)
                    if d.status_code != 200:
                        break
                    st = d.json().get("status")
                    if st in ("completed", "abstained", "failed"):
                        full_ms.append((time.perf_counter() - t0) * 1000)
                        statuses[st] = statuses.get(st, 0) + 1
                        sc = (d.json().get("reliability") or {}).get("score")
                        if isinstance(sc, (int, float)):
                            scores.append(float(sc))
                        break

        results["analysis_create"] = summarize("analysis_create", create_ms)
        results["analysis_end_to_end"] = summarize("analysis_end_to_end", full_ms)
        results["analysis_statuses"] = statuses
        results["reliability_scores"] = {
            "n": len(scores),
            "mean": round(statistics.mean(scores), 4) if scores else None,
        }

        # ── Detail endpoint (fan-out read) ─────────────────────────────────
        det: list[float] = []
        for _ in range(args.runs):
            t0 = time.perf_counter()
            await client.get(f"{args.base_url}/api/v1/analyses", headers=h)
            det.append((time.perf_counter() - t0) * 1000)
        results["analyses_list"] = summarize("analyses_list", det)

    print(json.dumps(results, indent=2))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"[bench] wrote {args.out}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
