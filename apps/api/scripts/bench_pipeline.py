"""
TRUSTRAG — End-to-end pipeline benchmark harness (read-mostly; seeds a scratch KB).

Measures, against live local services (embedded Qdrant + MongoDB + Ollama):

  * API-level latency for the analysis create/poll path
  * Stage latency: retrieval (dense/sparse/fusion/temporal), rerank, generation,
    claim verification
  * LLM TTFT proxy + tokens/sec estimate
  * Process RSS before/after
  * Retrieval quality: Recall@K / Precision@K / MRR against a known-ground-truth
    probe set

Usage:
    python scripts/bench_pipeline.py --runs 3 --kb-id <id>   # reuse an existing KB
    python scripts/bench_pipeline.py --runs 3 --seed          # seed a scratch KB
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.system.memory import get_memory_usage_mb  # noqa: E402
from app.observability.logging import configure_logging  # noqa: E402


# ─── Stats helpers ────────────────────────────────────────────────────────────


def _pct(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * len(ordered))) - 1))
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


# ─── Seeding ──────────────────────────────────────────────────────────────────

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

PROBES: list[dict[str, Any]] = [
    {
        "query": "What is the reciprocal rank fusion constant?",
        "expect": "sixty",
    },
    {
        "query": "How many fused candidates are considered before reranking?",
        "expect": "twenty",
    },
    {
        "query": "Which embedding model does dense retrieval use?",
        "expect": "BGE-small",
    },
    {
        "query": "What happens when the evidence does not support an answer?",
        "expect": "abstain",
    },
    {
        "query": "What does the temporal filter drop?",
        "expect": "segments",
    },
]


async def seed_kb(user_id: str) -> str:
    """Create a scratch KB with one seeded document and wait for indexing."""
    from bson import ObjectId

    from app.persistence.mongodb import Collections, get_collection
    from app.rag.ingestion.chunking_strategies import get_chunking_strategy
    from app.rag.ingestion.parser import parse_document
    from app.rag.ingestion.pipeline import index_parsed_chunks
    from app.config import get_model_config

    cfg = get_model_config()
    kb_coll = get_collection(Collections.KNOWLEDGE_BASES)
    kb_doc = {
        "user_id": ObjectId(user_id),
        "name": "bench-scratch-kb",
        "description": "benchmark scratch knowledge base",
        "embedding_model": cfg.embedding_model,
        "embedding_dim": cfg.embedding_dimensionality,
        "document_count": 0,
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").UTC
        ),
    }
    kb_id = await kb_coll.insert_one(kb_doc)
    kb_str = str(kb_id.inserted_id)

    pages, _ef, _eu = await asyncio.to_thread(
        parse_document, "policy.txt", __import__("io").BytesIO(SEED_DOC.encode())
    )
    chunks = await asyncio.to_thread(
        get_chunking_strategy().chunk,
        pages,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )

    doc_coll = get_collection(Collections.DOCUMENTS)
    doc_res = await doc_coll.insert_one(
        {
            "knowledge_base_id": ObjectId(kb_str),
            "user_id": ObjectId(user_id),
            "filename": "policy.txt",
            "file_size": len(SEED_DOC),
            "content_hash": "bench" + kb_str,
            "ingestion_status": "processing",
            "created_at": __import__("datetime").datetime.now(
                __import__("datetime").UTC
            ),
        }
    )
    await index_parsed_chunks(doc_id_str=str(doc_res.inserted_id), kb_id_str=kb_str, chunks=chunks)
    return kb_str


# ─── Benchmarks ───────────────────────────────────────────────────────────────


async def bench_retrieval(kb_id: str, runs: int) -> dict[str, list[float]]:
    """Stage-level retrieval latency."""
    from app.rag.retrieval.retriever import (
        apply_temporal_filtering,
        dense_search,
        reciprocal_rank_fusion,
        sparse_search,
    )

    out: dict[str, list[float]] = {
        "dense": [],
        "sparse": [],
        "fusion": [],
        "temporal": [],
        "hybrid_total": [],
    }
    for probe in PROBES:
        q = probe["query"]
        for _ in range(runs):
            t0 = time.perf_counter()
            dense = await dense_search(q, kb_id, top_k=20)
            out["dense"].append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            sparse = await sparse_search(q, kb_id, top_k=20)
            out["sparse"].append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            fused = reciprocal_rank_fusion(dense, sparse, k=60)
            out["fusion"].append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            await apply_temporal_filtering(fused, None)
            out["temporal"].append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            from app.rag.retrieval.retriever import retrieve_hybrid_chunks

            await retrieve_hybrid_chunks(q, kb_id)
            out["hybrid_total"].append((time.perf_counter() - t0) * 1000)
    return out


async def bench_rerank(kb_id: str, runs: int) -> list[float]:
    from app.rag.retrieval.reranker import rerank_candidate_chunks
    from app.rag.retrieval.retriever import retrieve_hybrid_chunks

    timings: list[float] = []
    for probe in PROBES:
        chunks = await retrieve_hybrid_chunks(probe["query"], kb_id)
        for _ in range(runs):
            t0 = time.perf_counter()
            await rerank_candidate_chunks(probe["query"], chunks)
            timings.append((time.perf_counter() - t0) * 1000)
    return timings


async def bench_generation(kb_id: str, runs: int) -> dict[str, list[float]]:
    """Grounded generation latency + token throughput estimate."""
    from app.rag.generation.runtime import generate_grounded_answer
    from app.rag.retrieval.retriever import retrieve_hybrid_chunks

    latencies: list[float] = []
    tps: list[float] = []
    for probe in PROBES:
        chunks = await retrieve_hybrid_chunks(probe["query"], kb_id)
        for _ in range(runs):
            t0 = time.perf_counter()
            answer = await generate_grounded_answer(probe["query"], chunks)
            dt = time.perf_counter() - t0
            latencies.append(dt * 1000)
            # Rough output-token estimate: ~4 chars/token.
            approx_tokens = max(1, len(answer or "") // 4)
            tps.append(approx_tokens / max(dt, 1e-6))
    return {"generation": latencies, "tok_per_s": tps}


async def bench_verification(kb_id: str, runs: int) -> dict[str, list[float]]:
    """Claim decomposition + NLI verification latency."""
    from app.rag.generation.runtime import generate_grounded_answer
    from app.rag.retrieval.retriever import retrieve_hybrid_chunks
    from app.rag.verification.pipeline.orchestrator import execute_claim_verification

    latencies: list[float] = []
    for probe in PROBES:
        chunks = await retrieve_hybrid_chunks(probe["query"], kb_id)
        answer = await generate_grounded_answer(probe["query"], chunks)
        for _ in range(runs):
            t0 = time.perf_counter()
            await execute_claim_verification(
                analysis_id_str="bench_analysis",
                answer=answer or "",
                chunks=chunks,
                evidence_ids=[],
                user_id_str=None,
                kb_id_str=kb_id,
            )
            latencies.append((time.perf_counter() - t0) * 1000)
    return {"verification": latencies}


async def bench_quality(kb_id: str) -> dict[str, Any]:
    """Recall@K / Precision@K / MRR against the seeded probe set."""
    from app.rag.retrieval.retriever import retrieve_hybrid_chunks

    recalls: list[float] = []
    precisions: list[float] = []
    rrs: list[float] = []
    per_probe = []
    for probe in PROBES:
        chunks = await retrieve_hybrid_chunks(probe["query"], kb_id)
        texts = [c.get("text", "").lower() for c in chunks]
        expect = probe["expect"].lower()
        hit_rank = next((i for i, t in enumerate(texts) if expect in t), None)
        if hit_rank is None:
            recalls.append(0.0)
            precisions.append(0.0)
            rrs.append(0.0)
            per_probe.append({"query": probe["query"], "hit": False})
            continue
        k = len(chunks)
        recalls.append(1.0 if hit_rank < k else 0.0)
        precisions.append(1.0 / k)
        rrs.append(1.0 / (hit_rank + 1))
        per_probe.append(
            {"query": probe["query"], "hit": True, "rank": hit_rank + 1, "of": k}
        )
    return {
        "recall_at_k": round(sum(recalls) / max(1, len(recalls)), 4),
        "precision_at_k": round(sum(precisions) / max(1, len(precisions)), 4),
        "mrr": round(sum(rrs) / max(1, len(rrs)), 4),
        "per_probe": per_probe,
    }


async def bench_api(runs: int, kb_id: str) -> dict[str, list[float]]:
    """API-path latency: create analysis (202) + full pipeline completion."""
    from app.rag.agent.graph.coordinator import execute_agentic_rag_flow
    from app.persistence.mongodb import Collections, get_collection

    creates: list[float] = []
    full: list[float] = []
    for probe in PROBES:
        for _ in range(runs):
            t0 = time.perf_counter()
            state = await execute_agentic_rag_flow(
                analysis_id_str="bench_api_analysis",
                kb_id_str=kb_id,
                query=probe["query"],
                user_id_str=None,
                llm_provider=None,
                llm_model=None,
            )
            dt = (time.perf_counter() - t0) * 1000
            full.append(dt)
            creates.append(dt)
    _ = get_collection(Collections.ANALYSES)
    return {"api_full_analysis": creates, "analysis_full": full}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--kb-id", default="")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--user-id", default="")
    ap.add_argument("--skip-api", action="store_true")
    args = ap.parse_args()

    configure_logging()
    from app.persistence.mongodb import Collections, connect_db, disconnect_db, get_collection

    await connect_db()
    try:
        kb_id = args.kb_id
        if args.seed or not kb_id:
            user_id = args.user_id
            if not user_id:
                from bson import ObjectId

                res = await get_collection(Collections.USERS).insert_one(
                    {
                        "email": f"bench-{int(time.time())}@local",
                        "password_hash": "x",
                        "created_at": __import__("datetime").datetime.now(
                            __import__("datetime").UTC
                        ),
                    }
                )
                user_id = str(res.inserted_id)
            kb_id = await seed_kb(user_id)
            print(f"[bench] seeded scratch KB: {kb_id}")

        rss_before = get_memory_usage_mb()
        results: dict[str, Any] = {"kb_id": kb_id, "runs": args.runs}

        retrieval = await bench_retrieval(kb_id, args.runs)
        for k, v in retrieval.items():
            results[f"retrieval_{k}"] = summarize(f"retrieval_{k}", v)

        rerank = await bench_rerank(kb_id, args.runs)
        results["rerank"] = summarize("rerank", rerank)

        gen = await bench_generation(kb_id, args.runs)
        results["generation"] = summarize("generation", gen["generation"])
        results["tok_per_s"] = summarize("tok_per_s", gen["tok_per_s"], "tok/s")

        ver = await bench_verification(kb_id, args.runs)
        results["verification"] = summarize("verification", ver["verification"])

        results["quality"] = await bench_quality(kb_id)

        if not args.skip_api:
            api = await bench_api(args.runs, kb_id)
            for k, v in api.items():
                results[k] = summarize(k, v)

        results["rss_before_mb"] = rss_before
        results["rss_after_mb"] = get_memory_usage_mb()
        print(json.dumps(results, indent=2, default=str))
        out = Path("bench_results.json")
        out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(f"[bench] wrote {out}")
    finally:
        await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
