"""
TRUSTRAG — End-to-end accuracy evaluation.

Runs the ground-truth probe set in `eval/eval_set.py` against a live API and scores
the two halves of the product's promise:

- **answer accuracy** — an answerable probe must be answered, and the answer
  must contain the expected substring;
- **abstention accuracy** — an unanswerable probe must abstain.

It also reports retrieval quality (Recall@K / Precision@K / MRR over the
stored evidence) so an accuracy change can be attributed to retrieval or to
verification rather than guessed at.

Unlike `analyze_quality.py` (which scores evidence that is already stored),
this harness creates the knowledge base, uploads the corpus and runs the
analyses, so it measures the whole path.

Usage:
    python scripts/eval_accuracy.py --out eval_accuracy.json
    python scripts/eval_accuracy.py --kb-id <existing>   # reuse a seeded KB
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench_auth import register_or_login
from scripts.eval.eval_set import CORPUS, PROBES


async def _seed_kb(client, base_url: str, token: str) -> str:
    """Create a knowledge base and upload the evaluation corpus."""
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        f"{base_url}/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "eval-corpus", "description": "ground-truth evaluation corpus"},
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"create kb failed: {r.status_code} {r.text[:200]}")
    kb_id = r.json()["id"]

    for filename, content in CORPUS:
        r = await client.post(
            f"{base_url}/api/v1/knowledge-bases/{kb_id}/documents",
            headers=headers,
            files={"file": (filename, content.encode(), "text/plain")},
        )
        if r.status_code not in (200, 201, 202):
            raise RuntimeError(f"upload {filename} failed: {r.status_code} {r.text[:200]}")
    return kb_id


async def _wait_for_indexing(client, base_url: str, token: str, kb_id: str) -> None:
    """Wait until every document has been ingested."""
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        r = await client.get(
            f"{base_url}/api/v1/knowledge-bases/{kb_id}/documents", headers=headers
        )
        if r.status_code == 200:
            docs = r.json()
            if docs and all(
                d.get("ingestion_status") in ("indexed", "ready", "completed") for d in docs
            ):
                return
        await asyncio.sleep(2)
    raise RuntimeError("documents were not indexed in time")


async def _run_probe(
    client,
    base_url: str,
    token: str,
    kb_id: str,
    query: str,
    timeout: float = 300.0,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run one analysis and return its terminal document."""
    headers = {"Authorization": f"Bearer {token}"}
    payload: dict[str, Any] = {"knowledge_base_id": kb_id, "query": query}
    if provider:
        payload["llm_provider"] = provider
    if model:
        payload["llm_model"] = model
    r = await client.post(
        f"{base_url}/api/v1/analyses",
        headers=headers,
        json=payload,
    )
    if r.status_code not in (200, 201):
        return {
            "status": f"http_{r.status_code}",
            "answer": "",
            "reliability": None,
            "diagnosis": None,
        }
    analysis_id = r.json()["id"]

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = await client.get(f"{base_url}/api/v1/analyses/{analysis_id}", headers=headers)
        if r.status_code == 200:
            doc = r.json()
            if doc.get("status") in ("completed", "abstained", "failed"):
                return doc
        await asyncio.sleep(1)
    return {"status": "timeout", "answer": "", "reliability": None, "diagnosis": None}


async def _fetch_evidence(
    client, base_url: str, headers: dict[str, str], analysis_id: str
) -> list[dict[str, Any]]:
    """The evidence actually served for one analysis."""
    r = await client.get(f"{base_url}/api/v1/analyses/{analysis_id}/evidence", headers=headers)
    if r.status_code != 200:
        return []
    payload = r.json()
    if isinstance(payload, dict):
        payload = payload.get("evidence") or payload.get("items") or []
    return payload if isinstance(payload, list) else []


async def _fetch_documents(
    client, base_url: str, headers: dict[str, str], kb_id: str
) -> dict[str, Any]:
    """The documents that were indexed into the evaluation knowledge base."""
    r = await client.get(f"{base_url}/api/v1/knowledge-bases/{kb_id}/documents", headers=headers)
    docs = r.json() if r.status_code == 200 else []
    return {"count": len(docs), "filenames": [d.get("filename") for d in docs]}


def _retrieval_scores(expected: str | None, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Recall@K / Precision@K / MRR over the served evidence."""
    texts = []
    for item in evidence:
        if isinstance(item, dict):
            texts.append(str(item.get("text") or "").lower())
        else:
            texts.append(str(item).lower())
    if expected is None:
        return {"n_evidence": len(texts)}
    want = expected.lower()
    rank = next((i for i, t in enumerate(texts) if want in t), None)
    return {
        "n_evidence": len(texts),
        "hit": rank is not None,
        "rank": (rank + 1) if rank is not None else None,
        "recall_at_k": 1.0 if rank is not None else 0.0,
        "precision_at_k": round(1.0 / len(texts), 4) if texts else 0.0,
        "mrr": round(1.0 / (rank + 1), 4) if rank is not None else 0.0,
    }


def _score(expected: str | None, doc: dict[str, Any]) -> dict[str, Any]:
    """Score one probe against its expectation."""
    status = doc.get("status")
    answer = (doc.get("answer") or "").lower()
    if expected is None:
        # Unanswerable: abstaining is the correct outcome.
        return {
            "kind": "unanswerable",
            "correct": status == "abstained",
            "expected": "abstain",
            "actual": status,
        }
    answered = status == "completed" and expected.lower() in answer
    return {
        "kind": "answerable",
        "correct": answered,
        "expected": expected,
        "actual": status,
        "answer_contains_expected": expected.lower() in answer,
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="eval_accuracy.json")
    ap.add_argument("--kb-id", default="", help="reuse an existing knowledge base")
    ap.add_argument("--label", default="", help="label for this run (e.g. 'gemma3-1b')")
    ap.add_argument("--provider", default="", help="llm provider override for the analyses")
    ap.add_argument("--model", default="", help="llm model override for the analyses")
    args = ap.parse_args()

    import httpx

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        token, email = await register_or_login(client, args.base_url)
        headers = {"Authorization": f"Bearer {token}"}

        kb_id = args.kb_id
        if not kb_id:
            kb_id = await _seed_kb(client, args.base_url, token)
            await _wait_for_indexing(client, args.base_url, token, kb_id)

        rows: list[dict[str, Any]] = []
        for query, expected in PROBES:
            started = time.perf_counter()
            doc = await _run_probe(
                client,
                args.base_url,
                token,
                kb_id,
                query,
                provider=args.provider or None,
                model=args.model or None,
            )
            elapsed = (time.perf_counter() - started) * 1000
            score = _score(expected, doc)
            evidence = await _fetch_evidence(client, args.base_url, headers, doc.get("id", ""))
            score["retrieval"] = _retrieval_scores(expected, evidence)
            score.update(
                {
                    "query": query,
                    "latency_ms": round(elapsed),
                    "answer": (doc.get("answer") or "")[:400],
                    "diagnosis_type": (doc.get("diagnosis") or {}).get("type"),
                    "diagnosis_failures": (doc.get("diagnosis") or {}).get("failures") or [],
                    "reliability_score": (doc.get("reliability") or {}).get("score"),
                    "reliability_status": (doc.get("reliability") or {}).get("status"),
                }
            )
            rows.append(score)

        # Retrieval quality over the evidence actually stored for this KB.
        documents = await _fetch_documents(client, args.base_url, headers, kb_id)

    answerable = [r for r in rows if r["kind"] == "answerable"]
    unanswerable = [r for r in rows if r["kind"] == "unanswerable"]
    answered = sum(1 for r in answerable if r["correct"])
    abstained = sum(1 for r in unanswerable if r["correct"])

    answerable_evidence = [r["retrieval"] for r in answerable if "retrieval" in r]
    retrieval_summary = {
        "n": len(answerable_evidence),
        "recall_at_k": round(
            sum(1 for e in answerable_evidence if e.get("hit")) / len(answerable_evidence), 4
        )
        if answerable_evidence
        else None,
        "precision_at_k": round(
            sum(e.get("precision_at_k", 0.0) for e in answerable_evidence)
            / len(answerable_evidence),
            4,
        )
        if answerable_evidence
        else None,
        "mrr": round(
            sum(e.get("mrr", 0.0) for e in answerable_evidence) / len(answerable_evidence), 4
        )
        if answerable_evidence
        else None,
    }

    report: dict[str, Any] = {
        "label": args.label,
        "provider": args.provider or "default",
        "model": args.model or "default",
        "kb_id": kb_id,
        "user": email,
        "n_probes": len(rows),
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
        # The headline numbers: how often a grounded answer was produced where
        # one was possible, and how often the system stayed silent where the
        # corpus was silent.
        "answer_accuracy": round(answered / len(answerable), 4) if answerable else None,
        "abstention_accuracy": round(abstained / len(unanswerable), 4) if unanswerable else None,
        "answerable_answered": answered,
        "unanswerable_abstained": abstained,
        "false_abstentions": [r["query"] for r in answerable if not r["correct"]],
        "false_answers": [r["query"] for r in unanswerable if not r["correct"]],
        "mean_latency_ms": round(sum(r["latency_ms"] for r in rows) / len(rows)) if rows else 0,
        "retrieval_quality": retrieval_summary,
        "documents": documents,
        "rows": rows,
    }

    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"[eval] wrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
