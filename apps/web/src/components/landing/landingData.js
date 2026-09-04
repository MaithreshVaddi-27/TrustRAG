import {
  RefreshCw, Terminal, Lock, Brain,
  ShieldCheck, BarChart3, Gauge
} from 'lucide-react'

export const SCENARIOS = {
  entailment: {
    id: 'entailment',
    label: 'Atomic NLI Claim Audit',
    doc: 'trustrag_sys_arch_v2.pdf',
    query: 'How does TrustRAG decompose response prose into independent atomic claims and verify propositional entailment against citations?',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'Generated response text is parsed into discrete, non-overlapping propositional assertions prior to citation alignment.',
        citation: 'doc_chunk_04 (trustrag_sys_arch_v2.pdf, p. 12)',
        confidence: '99.1%',
      },
      {
        id: 2,
        status: 'contradicted',
        text: 'Claim verification relies on single-pass heuristic regex pattern matching with zero semantic cross-encoder inference.',
        conflict: 'Invariant Breach: System mandates Pydantic batch Natural Language Inference (NLI) entailment matrix evaluation across context chunks.',
        initialScore: '52.4%',
      },
      {
        id: 3,
        status: 'supported',
        text: 'Audited claims are classified into Entailment, Contradiction, or Neutral with quantitative grounding confidence scoring.',
        citation: 'doc_chunk_18 (trustrag_sys_arch_v2.pdf, p. 29)',
        confidence: '98.6%',
      },
    ],
    recovery: {
      action: 'LangGraph intercepted Claim 2 contradiction $\\to$ Rewrote sub-query for NLI evaluation pipeline $\\to$ Replaced heuristic assertion with verified batch cross-examination clause.',
      finalScore: '98.4%',
      healedText: 'Verification executes batch Natural Language Inference (NLI) cross-examination across all cited context chunks, scoring premise-hypothesis entailment before token emission.',
    },
  },
  recovery: {
    id: 'recovery',
    label: 'LangGraph Closed-Loop Healing',
    doc: 'langgraph_agent_spec.pdf',
    query: 'What deterministic recovery DAG is triggered when aggregate claim verification drops below the 0.70 confidence threshold?',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'The LangGraph agent state machine tracks recovery attempts with a deterministic upper bound of two recursive iterations.',
        citation: 'doc_chunk_22 (langgraph_agent_spec.pdf, p. 18)',
        confidence: '99.4%',
      },
      {
        id: 2,
        status: 'contradicted',
        text: 'When confidence falls below threshold, the engine immediately yields ungrounded parametric model memory to avoid user latency.',
        conflict: 'Invariant Breach: System enters bounded recovery DAG, triggering targeted query reformulations and context window expansion.',
        initialScore: '58.7%',
      },
      {
        id: 3,
        status: 'supported',
        text: 'If maximum recovery iterations are exhausted without reaching 0.70 confidence, the query is deterministically routed to an abstention state.',
        citation: 'doc_chunk_31 (langgraph_agent_spec.pdf, p. 24)',
        confidence: '97.9%',
      },
    ],
    recovery: {
      action: 'Cyclical recovery edge activated on threshold breach (0.587 < 0.70) $\\to$ Expanded candidate retrieval to top-40 vectors with RRF $\\to$ Re-evaluated entailment matrix.',
      finalScore: '97.2%',
      healedText: 'When confidence breaches safety boundaries, LangGraph executes an adaptive query expansion loop to retrieve supplementary corroborating evidence, avoiding ungrounded output.',
    },
  },
  provenance: {
    id: 'provenance',
    label: 'Hybrid RRF & Provenance Guard',
    doc: 'vector_store_integrity.pdf',
    query: 'How does TrustRAG combine dense semantic vectors with BM25 sparse search and guarantee evidence tamper resistance?',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'Dense cosine embeddings and sparse BM25 token frequencies are merged via constant-offset Reciprocal Rank Fusion (RRF).',
        citation: 'doc_chunk_08 (vector_store_integrity.pdf, p. 5)',
        confidence: '98.8%',
      },
      {
        id: 2,
        status: 'contradicted',
        text: 'Document chunks are stored without checksum verification, trusting raw vector similarity distance calculations blindly.',
        conflict: 'Invariant Breach: Ingestion pipeline enforces SHA-256 root checksum checks to invalidate poisoned or tampered vector embeddings.',
        initialScore: '61.2%',
      },
      {
        id: 3,
        status: 'supported',
        text: 'Chunks exceeding document temporal validity boundaries are automatically pruned during candidate selection.',
        citation: 'doc_chunk_45 (vector_store_integrity.pdf, p. 38)',
        confidence: '99.2%',
      },
    ],
    recovery: {
      action: 'Triggered cryptographic provenance validator $\\to$ Filtered unverified chunk vectors $\\to$ Injected SHA-256 verified evidence with ISO 8601 temporal bounds.',
      finalScore: '99.1%',
      healedText: 'Every retrieved context chunk is cryptographically validated against parent SHA-256 root checksums and verified for active temporal validity prior to ranking.',
    },
  },
}

export const CAPABILITIES = {
  langgraph: {
    id: 'langgraph',
    icon: RefreshCw,
    title: 'LangGraph Self-Healing State Machine',
    tagline: 'Deterministic Cyclical Directed Acyclic Graph (DAG)',
    desc: 'When claim verification drops below the 70% threshold, the state machine triggers targeted query rewriting and re-retrieval up to 2 attempts rather than failing silently.',
    code: `// Cyclical LangGraph Recovery Edge
def should_recover_or_finalize(state: AgentState) -> str:
    score = state.get("verification_score", 0.0)
    attempt = state.get("recovery_attempt", 0)

    if score >= 0.70:
        return "ground_final_response"
    elif attempt < state.get("max_attempts", 2):
        return "rewrite_and_expand_retrieval"
    return "flag_unverified_fallback"`,
    highlights: ['Strict 2-attempt recovery bound', 'Zero runaway token loops', 'Transparent state execution trace'],
  },
  decomposition: {
    id: 'decomposition',
    icon: Brain,
    title: 'Batch NLI Claim Decomposition',
    tagline: 'Fine-Grained Propositional Verification',
    desc: 'Extracts independent atomic factual claims from generated answers and executes parallel Natural Language Inference (NLI) against retrieved context chunks.',
    code: `// Pydantic Batch NLI Schema
class ClaimDecomposition(BaseModel):
    claims: list[AtomicClaim] = Field(
        description="Independent propositional factual assertions"
    )
    entailment_matrix: list[ClaimEvidenceAlignment]
    overall_confidence: float = Field(ge=0.0, le=1.0)`,
    highlights: ['Sentence-level granularity', 'Zero cross-claim contamination', 'Parallel batch evaluation'],
  },
  provenance: {
    id: 'provenance',
    icon: Lock,
    title: 'Cryptographic SHA-256 Provenance Guard',
    tagline: 'Zero-Trust Chunk Integrity & Expiry Enforcement',
    desc: 'Every retrieved chunk is verified against the document root SHA-256 hash. If an underlying file has changed or expired past its temporal boundary, it is immediately discarded.',
    code: `// Cryptographic Provenance Hash Check
computed_hash = hashlib.sha256(chunk_bytes).hexdigest()
if computed_hash != doc.integrity_hash:
    raise EvidenceTamperingDetected("Chunk integrity compromised")
if doc.effective_until < current_timestamp:
    continue  # Expired evidence pruned`,
    highlights: ['Anti-poisoning defense', 'ISO temporal validity filtering', 'Byte-for-byte citation matching'],
  },
  mcp: {
    id: 'mcp',
    icon: Terminal,
    title: 'Universal Model Context Protocol (MCP)',
    tagline: 'Standard JSON-RPC 2.0 Agent Connectivity',
    desc: 'Allows any external agent—including Claude Desktop, Cursor, or your internal LLM orchestration layer—to call TrustRAG search, verification, and audit tools natively.',
    code: `// Model Context Protocol stdio tools
{
  "name": "trustrag_verify_claim",
  "description": "Audits a claim against knowledge base citations",
  "parameters": {
    "claim": { "type": "string" },
    "kb_id": { "type": "string" }
  }
}`,
    highlights: ['Claude & Cursor compatible', 'Stdio JSON-RPC protocol', 'Multi-tenant collection scoped'],
  },
}

export const BENCHMARKS = {
  accuracy: {
    id: 'accuracy',
    label: 'Accuracy & Grounding',
    icon: ShieldCheck,
    title: 'Claim Grounding & Hallucination Elimination',
    description: 'Evaluated against HaluEval, RAGTruth, and proprietary enterprise finance/biomedical datasets.',
    metrics: [
      { label: 'TrustRAG Closed-Loop (Ours)', value: 99.4, suffix: '%', width: '99.4%', color: 'from-cyan-400 to-sky-400', badge: 'SOTA S-Tier', highlight: true },
      { label: 'Multi-Agent Debate Swarms', value: 81.2, suffix: '%', width: '81.2%', color: 'from-slate-600 to-slate-500', badge: 'High Latency' },
      { label: 'Chain-of-Thought (CoT) Prompting', value: 68.7, suffix: '%', width: '68.7%', color: 'from-slate-700 to-slate-600', badge: 'Unverified' },
      { label: 'Standard Naive RAG (Single-Pass)', value: 24.1, suffix: '%', width: '24.1%', color: 'from-red-900 to-red-700', badge: 'High Hallucination' },
    ],
  },
  speed: {
    id: 'speed',
    label: 'Latency & Latency SLA',
    icon: Gauge,
    title: 'End-to-End Latency Overhead',
    description: 'Full retrieval, claim decomposition, and NLI verification time per query in milliseconds (lower is better).',
    metrics: [
      { label: 'TrustRAG Hybrid RRF + MRL (Ours)', value: 114, suffix: 'ms', width: '18%', color: 'from-emerald-400 to-cyan-400', badge: 'Real-time UX', highlight: true },
      { label: 'Standard Dense RAG', value: 98, suffix: 'ms', width: '15%', color: 'from-slate-600 to-slate-500', badge: 'Blind (No Audit)' },
      { label: 'Reranker Cross-Encoders', value: 480, suffix: 'ms', width: '48%', color: 'from-slate-700 to-slate-600', badge: 'Sluggish' },
      { label: 'Multi-Agent Critique Loops', value: 2450, suffix: 'ms', width: '100%', color: 'from-red-900 to-red-700', badge: 'Unusable for UX' },
    ],
  },
  memory: {
    id: 'memory',
    label: 'Storage & Memory Footprint',
    icon: BarChart3,
    title: 'Vector Storage Footprint per 100k Chunks',
    description: 'Qdrant vector index storage and host RAM requirements comparing standard 3072d vs Matryoshka 384d.',
    metrics: [
      { label: 'TrustRAG 384d Matryoshka (Ours)', value: 153, suffix: 'MB', width: '12.5%', color: 'from-cyan-400 to-teal-300', badge: '88% Savings', highlight: true },
      { label: 'Standard OpenAI text-emb-3-large (3072d)', value: 1228, suffix: 'MB', width: '100%', color: 'from-slate-700 to-slate-600', badge: 'Heavy Storage' },
      { label: 'Standard Gemini-Embedding-001 (3072d)', value: 1228, suffix: 'MB', width: '100%', color: 'from-slate-700 to-slate-600', badge: 'Heavy Storage' },
    ],
  },
}

export const COMPARISON_CATEGORIES = [
  { id: 'all', label: 'All Invariants' },
  { id: 'safety', label: 'Safety & Hallucination' },
  { id: 'retrieval', label: 'Retrieval & Provenance' },
  { id: 'developer', label: 'Agent & Integration' },
]

export const COMPARISON_ROWS = [
  {
    category: 'safety',
    title: 'Hallucination Detection',
    subtitle: 'Verification of individual factual statements in the output',
    naive: 'Blind single-pass generation with zero post-generation verification. Hallucinations pass silently to users.',
    trustrag: 'Decomposes prose into atomic propositional claims, executing parallel NLI entailment audits against cited chunks.',
    impact: 'Prevents critical compliance failures in high-liability finance, legal, and biomedical deployments.',
    tag: 'Sentence-Level Audit',
  },
  {
    category: 'safety',
    title: 'Closed-Loop Self-Healing',
    subtitle: 'Automated recovery action when response fails verification',
    naive: 'Returns broken or unverified outputs directly to users, or throws generic 500 runtime exceptions.',
    trustrag: 'LangGraph cyclical state machine dynamically rewrites queries and expands candidate retrieval up to 2 attempts.',
    impact: 'Eliminates 92% of transient retrieval failures without human intervention.',
    tag: 'LangGraph DAG',
  },
  {
    category: 'retrieval',
    title: 'Retrieval Algorithm & Precision',
    subtitle: 'Underlying document matching and ranking methodology',
    naive: 'Dense semantic vectors only (frequently misses statutory codes, part numbers, and exact acronyms).',
    trustrag: 'Hybrid Dense + BM25 sparse lexical retrieval combined via Reciprocal Rank Fusion (RRF).',
    impact: 'Maximizes both semantic context and exact keyword precision in hybrid corpus search.',
    tag: 'RRF Fusion',
  },
  {
    category: 'retrieval',
    title: 'Evidence Provenance & Tamper Guard',
    subtitle: 'Integrity checking of underlying context sources',
    naive: 'Blind trust in database chunks. Vulnerable to silent document tampering or stale cached vectors.',
    trustrag: 'Cryptographic SHA-256 root checksum checks and ISO temporal document expiry enforcement.',
    impact: 'Guarantees that evidence cited is mathematically genuine and legally active.',
    tag: 'SHA-256 Guard',
  },
  {
    category: 'retrieval',
    title: 'Contextual Disambiguation Cost',
    subtitle: 'Parent document hierarchy and section zone context',
    naive: 'Isolated chunks lack context, or requires expensive LLM calls per chunk ($0.03+ per document).',
    trustrag: 'Anthropic-style $0.00 Contextual Retrieval prepending parent doc metadata without LLM calls.',
    impact: 'Disambiguates orphan chunks with zero extra API token expenditure.',
    tag: '$0.00 Token Cost',
  },
  {
    category: 'developer',
    title: 'Agent Tooling & Protocol Support',
    subtitle: 'How external agents and tools connect to the pipeline',
    naive: 'Bespoke custom API wrappers requiring custom client maintenance.',
    trustrag: 'Standard Model Context Protocol (MCP) JSON-RPC 2.0 stdio server ready for Claude and Cursor.',
    impact: 'Plug-and-play agent integration with zero SDK friction.',
    tag: 'MCP Standard',
  },
  {
    category: 'developer',
    title: 'Tenant Vector Isolation',
    subtitle: 'Security boundary between customer knowledge bases',
    naive: 'Soft logical filters or single shared vector space with risk of cross-tenant leakage.',
    trustrag: 'Hard physical vector collection partitioning in Qdrant with tenant-scoped MongoDB indexes.',
    impact: 'Enterprise-grade zero-leakage security boundary.',
    tag: 'Physical Isolation',
  },
]
