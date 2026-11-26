/**
 * TrustRAG — landing page content.
 *
 * Every string on the marketing page lives here so the components stay
 * presentational and the copy can be reviewed in one place.
 *
 * Split by section. Each module owns one export; `data/index.js` re-exports
 * them for the components that want a single import.
 *
 * Benchmark figures carry their provenance in the `note` field. TrustRAG's
 * own numbers are measured on the internal reliability fixture documented in
 * `docs/evaluation/`; competitor figures are published literature values.
 * Do not add a number without a source.
 */

import {
  Brain,
  Lock,
  RefreshCw,
  ScanText,
  ShieldCheck,
  Terminal,
} from 'lucide-react'

/**
 * The six layers, each with the code that implements it.
 *
 * The imports are the ones the running system uses. The verifier is
 * natural-language inference served by the local `ollama/gemma3:1b` model
 * named in `apps/api/config/models.yaml` — there is no cross-encoder in the
 * verification path, and the reranker that ships alongside it is disabled
 * (`reranker_enabled: false`).
 */
export const CAPABILITIES = [
  {
    id: 'healing',
    icon: Brain,
    title: 'LangGraph self-healing state machine',
    tagline: 'Bounded recovery, deterministic edges',
    desc:
      'When the aggregate reliability of an answer falls below 0.50, the graph enters a recovery DAG. It rewrites the sub-query, widens the retrieval pool, and re-runs the audit — up to two attempts, then abstention. The bound is configuration, not a convention.',
    highlights: [
      'Cyclical edge on threshold breach',
      'Two-attempt bound from models.yaml',
      'Deterministic abstention',
    ],
    code: `from app.config import get_model_config
from app.rag.agent.graph.build import build_graph
from app.rag.agent.graph.edges import should_recover, should_end

cfg = get_model_config()
graph = build_graph()

# models.yaml — reliability.abstain_below / recovery.max_recovery_attempts
cfg.abstain_below          # 0.50
cfg.max_recovery_attempts  # 2

def should_recover(state) -> str:
    if state["verdict_status"] == "PASS":
        return "end"
    if state["attempts"] >= cfg.max_recovery_attempts:
        return "end"
    return "recover"`,
  },
  {
    id: 'decomposition',
    icon: ScanText,
    title: 'Atomic claim decomposition',
    tagline: 'Prose split before citation alignment',
    desc:
      'A response is parsed into discrete, non-overlapping propositional assertions before any citation is aligned. One sentence cannot hide an unverified half, and the audit matrix is built from assertions rather than spans of text.',
    highlights: [
      'Non-overlapping spans',
      'Pre-citation alignment',
      'One verdict per claim',
    ],
    code: `from app.rag.verification.pipeline.decomposition import (
    decompose_answer_to_claims,
)

claims: list[str] = await decompose_answer_to_claims(answer)

for index, claim in enumerate(claims, start=1):
    print(index, claim)

# Or fuse the split and the audit into one structured call:
from app.rag.verification.pipeline.nli import fused_decompose_verify

items = await fused_decompose_verify(answer=answer, chunks=chunks)`,
  },
  {
    id: 'retrieval',
    icon: RefreshCw,
    title: 'Hybrid dense and sparse retrieval',
    tagline: 'Reciprocal rank fusion, contextualised chunks',
    desc:
      'Dense vectors and BM25 sparse matches are combined with reciprocal rank fusion, because dense alone misses statutory codes and part numbers while sparse alone misses paraphrase. Both branches are required: if either fails, the whole retrieval fails rather than serving half the evidence.',
    highlights: [
      'Reciprocal rank fusion',
      'BM25 and dense in one ranking',
      'All-or-nothing retrieval',
    ],
    code: `from app.rag.retrieval.retriever import (
    retrieve_hybrid_chunks,
    reciprocal_rank_fusion,
)

chunks = await retrieve_hybrid_chunks(
    query=state["sub_query"],
    kb_id=kb.id,
    top_k_override=40,
)

# RRF score = 1 / (rank_dense + k) + 1 / (rank_sparse + k)
fused = reciprocal_rank_fusion(dense_results, sparse_results, k=60)`,
  },
  {
    id: 'entailment',
    icon: ShieldCheck,
    title: 'Batch NLI entailment audit',
    tagline: 'Every claim against every cited segment',
    desc:
      'Verification is a matrix, not a lookup. Each atomic claim is judged against the retrieved segments by natural-language inference, which returns SUPPORTED, CONTRADICTED or NEUTRAL together with the reasoning and the segment numbers that decided it. The reasoning is stored with the claim, so the verdict can be re-read rather than trusted.',
    highlights: [
      'Full claim-by-segment matrix',
      'Stored explanation per verdict',
      'Contradiction detection',
    ],
    code: `from app.rag.verification.pipeline.nli import (
    batch_verify_claims_nli,
    verify_claim_nli,
)

verdicts = await batch_verify_claims_nli(claims, chunks)
# {1: {"verdict": "SUPPORTED", "supporting_segments": [3],
#      "explanation": "The premise states that ..."}}

single = await verify_claim_nli(claim, chunks)`,
  },
  {
    id: 'provenance',
    icon: Lock,
    title: 'Cryptographic evidence provenance',
    tagline: 'SHA-256 root hashes and ISO temporal validity',
    desc:
      'Every segment is checked against the SHA-256 root hash of the document it came from, and a document past its effective date is pruned before it can be retrieved or scored. A file that changed after ingestion is marked CORRUPTED rather than cited.',
    highlights: [
      'Byte-for-byte root hash check',
      'Anti-poisoning defence',
      'Temporal expiry pruning',
    ],
    code: `from app.rag.verification.integrity import audit_evidence_integrity

audited = await audit_evidence_integrity(chunks)
# each chunk gains integrity_status: "VERIFIED" | "CORRUPTED"

# A document whose effective_until has passed is pruned before retrieval,
# so an expired specification is never a candidate for citation.`,
  },
  {
    id: 'mcp',
    icon: Terminal,
    title: 'Model Context Protocol server',
    tagline: 'Standard JSON-RPC 2.0 agent connectivity',
    desc:
      'TrustRAG exposes its search and verification tools over MCP, so an external agent — Claude Desktop, Cursor, or your own orchestrator — can call the audit directly instead of re-implementing it. Every call is scoped to the knowledge base the caller is allowed to read.',
    highlights: [
      'Claude and Cursor compatible',
      'Stdio JSON-RPC transport',
      'Tenant-scoped collections',
    ],
    code: `// app/mcp/server.py — the tools the server advertises
{
  "name": "trustrag_verify_claim",
  "description": "Audit and verify factual assertions against evidence chunks.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "claims":        { "type": "array", "items": { "type": "string" } },
      "evidence_texts":{ "type": "array", "items": { "type": "string" } }
    },
    "required": ["claims", "evidence_texts"]
  }
}`,
  },
]
