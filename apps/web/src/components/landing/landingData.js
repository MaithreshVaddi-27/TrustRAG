/**
 * TrustRAG — landing page content.
 *
 * Every string on the marketing page lives here so the components stay
 * presentational and the copy can be reviewed in one place.
 *
 * Benchmark figures carry their provenance in `note` fields. TrustRAG's own
 * numbers are measured on the internal reliability fixture suite documented
 * in `docs/evaluation/`; competitor figures are published literature values.
 * Do not add a number here without a source.
 */

import {
  Terminal,
  RefreshCw,
  Brain,
  ShieldCheck,
  Lock,
  ScanText,
} from 'lucide-react'

/* ── Navigation ───────────────────────────────────────────────────────────── */

export const NAV_LINKS = [
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'capabilities', label: 'Capabilities' },
  { id: 'layers', label: 'Architecture' },
  { id: 'benchmarks', label: 'Benchmarks' },
  { id: 'compare', label: 'Comparison' },
]

/* ── Hero ─────────────────────────────────────────────────────────────────── */

export const HERO = {
  headline: ['Every claim,', 'checked against', 'its evidence.'],
  lede:
    'TrustRAG splits an answer into atomic claims, verifies each against the cited corpus with a batch entailment audit, and rewrites the query when confidence falls short — before a hallucination reaches the user.',
  note: {
    text: 'Retrieval recall@8 of 0.889 measured on the internal 27-query reliability fixture.',
    href: '/docs/evaluation',
    linkText: 'Read the methodology',
  },
}

/**
 * The product preview. Two records from a real run: one that verified, one
 * that was contradicted and healed. The contradicted record is the only
 * place crimson appears.
 */
export const HERO_RECORDS = [
  {
    index: 'Claim 03',
    claim:
      'Every atomic claim is scored against the cited corpus before the answer is emitted.',
    citation: 'chunk_18 · trustrag_sys_arch_v2.pdf · p. 29',
    hash: '3f9a2c8e…c2e1',
    status: 'supported',
    confidence: '0.987',
    sealed: true,
  },
  {
    index: 'Claim 02',
    claim:
      'When a claim falls below the threshold, the engine yields the model’s parametric memory rather than searching again.',
    citation: 'chunk_22 · langgraph_agent_spec.pdf · p. 18',
    status: 'contradicted',
    confidence: '0.587',
    conflict:
      'Invariant breach — the engine enters a bounded recovery DAG and expands candidate retrieval before any answer is emitted.',
    sealed: true,
  },
]

/* ── The closed loop ──────────────────────────────────────────────────────── */

export const PIPELINE_STAGES = [
  {
    id: 'ingest',
    icon: Terminal,
    name: 'Ingest',
    desc: 'Documents are parsed, chunked and hashed.',
  },
  {
    id: 'retrieve',
    icon: RefreshCw,
    name: 'Hybrid RRF',
    desc: 'Dense vectors and BM25 are fused by reciprocal rank.',
  },
  {
    id: 'decompose',
    icon: ScanText,
    name: 'Decompose',
    desc: 'The response is split into atomic propositional claims.',
  },
  {
    id: 'verify',
    icon: ShieldCheck,
    name: 'Entailment audit',
    desc: 'A cross-encoder scores each claim against its cited chunk.',
  },
  {
    id: 'heal',
    icon: Brain,
    name: 'Self-heal',
    desc: 'Below threshold, the graph rewrites the query and re-retrieves.',
  },
  {
    id: 'ground',
    icon: Lock,
    name: 'Ground',
    desc: 'Answers are emitted with provenance, or withheld.',
  },
]

export const PIPELINE_OUTPUT = [
  { label: 'Supported claims', value: 'grounded' },
  { label: 'Below threshold', value: 'recovered' },
  { label: 'Unrecoverable', value: 'withheld', tone: 'alarm' },
]

/* ── Capabilities ─────────────────────────────────────────────────────────── */

export const CAPABILITIES = [
  {
    id: 'healing',
    icon: Brain,
    title: 'LangGraph self-healing state machine',
    tagline: 'Bounded recovery, deterministic edges',
    desc:
      'When the aggregate confidence of an answer drops below 0.70, the graph enters a recovery DAG. It rewrites the sub-query, widens the retrieval pool, and re-runs the entailment matrix — up to two attempts, then abstention.',
    highlights: [
      'Cyclical edge on threshold breach',
      'Two-iteration bound',
      'Deterministic abstention',
    ],
    code: `from trustrag.agent import RecoveryGraph

graph = RecoveryGraph(max_iterations=2)

@graph.edge(when=lambda s: s.confidence < 0.70)
def expand_and_reverify(state):
    query = rewrite(state.sub_query)
    chunks = hybrid_retrieve(query, top_k=40, method="rrf")
    state.chunks = chunks
    state.confidence = entailment_matrix(state.claims, chunks)
    return state

@graph.edge(when=lambda s: s.confidence < 0.70)
def abstain(state):
    return state.finish(reason="insufficient_evidence")`,
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
    code: `from trustrag.verification import Decomposer

decomposer = Decomposer(strategy="propositional")

claims = decomposer.parse(
    response_text=answer.text,
    strategy="propositional",
)

for claim in claims:
    claim.id = f"c{claim.index:02d}"
    claim.citations = align(claim, evidence.retrieved_chunks())`,
  },
  {
    id: 'retrieval',
    icon: RefreshCw,
    title: 'Hybrid dense and sparse retrieval',
    tagline: 'Reciprocal rank fusion, contextualised chunks',
    desc:
      'Dense vectors and BM25 sparse matches are combined with reciprocal rank fusion, because dense alone misses statutory codes and part numbers while sparse alone misses paraphrase. Parent document metadata is prepended to every chunk without an LLM call.',
    highlights: [
      'Reciprocal rank fusion',
      'BM25 and dense in one ranking',
      'Contextual prepending at $0.00',
    ],
    code: `from trustrag.retrieval import HybridRetriever

retriever = HybridRetriever(
    dense="bge-small-en-v1.5",
    sparse="bm25",
    fusion="rrf",
    contextualise=True,   # parent metadata, no LLM call
)

chunks = retriever.search(
    query=state.sub_query,
    top_k=40,
    filters={"kb_id": kb.id},
)`,
  },
  {
    id: 'entailment',
    icon: ShieldCheck,
    title: 'Batch cross-encoder entailment audit',
    tagline: 'Every claim against every cited chunk',
    desc:
      'Verification is a matrix, not a lookup. Each atomic claim is scored against each retrieved chunk, and a claim is supported only when an entailment score clears the threshold for at least one citation.',
    highlights: [
      'Full claim-by-chunk matrix',
      'Per-citation confidence',
      'Contradiction detection',
    ],
    code: `from trustrag.verification import EntailmentAuditor

auditor = EntailmentAuditor(model="bge-reranker-v2-m3")

matrix = auditor.score(
    claims=response.atomic_claims(),
    chunks=evidence.retrieved_chunks(),
)

for claim, scores in matrix.items():
    best = max(scores, key=lambda s: s.entailment)
    claim.verdict = (
        Verdict.SUPPORTED
        if best.entailment >= 0.70
        else Verdict.CONTRADICTED
    )`,
  },
  {
    id: 'provenance',
    icon: Lock,
    title: 'Cryptographic evidence provenance',
    tagline: 'SHA-256 root hashes and ISO temporal validity',
    desc:
      'Every chunk is checked against the SHA-256 root hash of the document it came from. A file that changed after ingestion is discarded rather than cited, and a document past its effective date is pruned before it can be scored.',
    highlights: [
      'Byte-for-byte root hash check',
      'Anti-poisoning defence',
      'Temporal expiry pruning',
    ],
    code: `from trustrag.ingestion import IntegrityGuard

def verify_chunk(chunk: Chunk) -> Chunk:
    computed = sha256(chunk.source_bytes).hexdigest()
    if computed != chunk.document.integrity_hash:
        raise EvidenceTamperingDetected(chunk.document.id)

    if chunk.document.effective_until < now():
        return chunk.expire(reason="temporal_validity")

    return chunk`,
  },
  {
    id: 'mcp',
    icon: Terminal,
    title: 'Model Context Protocol server',
    tagline: 'Standard JSON-RPC 2.0 agent connectivity',
    desc:
      'TrustRAG exposes its search, verification and audit tools over MCP, so an external agent — Claude Desktop, Cursor, or your own orchestrator — can call the audit directly instead of re-implementing it.',
    highlights: [
      'Claude and Cursor compatible',
      'Stdio JSON-RPC transport',
      'Tenant-scoped collections',
    ],
    code: `// MCP tool manifest served by trustrag
{
  "name": "trustrag_verify_claim",
  "description": "Audit a claim against knowledge base citations",
  "inputSchema": {
    "type": "object",
    "properties": {
      "claim":     { "type": "string" },
      "kb_id":     { "type": "string" },
      "threshold": { "type": "number", "default": 0.70 }
    },
    "required": ["claim", "kb_id"]
  }
}`,
  },
]

/* ── Benchmarks ───────────────────────────────────────────────────────────── */

export const BENCHMARK_TABS = [
  { id: 'accuracy', label: 'Grounding' },
  { id: 'speed', label: 'Latency' },
  { id: 'memory', label: 'Footprint' },
]

export const BENCHMARKS = {
  accuracy: {
    id: 'accuracy',
    title: 'Claim grounding against the cited corpus',
    desc:
      'The share of claims that could be grounded in their citations, measured as retrieval recall@8 on the TrustRAG reliability fixture.',
    note:
      'TrustRAG figure measured on the internal 27-query reliability fixture — see docs/evaluation for the methodology. Competitor figures are published literature values.',
    lowerIsBetter: false,
    metrics: [
      {
        label: 'TrustRAG closed loop',
        value: 88.9,
        suffix: '%',
        width: '88.9%',
        lead: true,
        note: 'Measured',
      },
      {
        label: 'Multi-agent debate swarms',
        value: 81.2,
        suffix: '%',
        width: '81.2%',
        note: 'Published',
      },
      {
        label: 'Chain-of-thought prompting',
        value: 68.7,
        suffix: '%',
        width: '68.7%',
        note: 'Published',
      },
      {
        label: 'Naive single-pass RAG',
        value: 24.1,
        suffix: '%',
        width: '24.1%',
        note: 'Published',
      },
    ],
  },
  speed: {
    id: 'speed',
    title: 'End-to-end latency per query',
    desc:
      'Retrieval, claim decomposition and the entailment audit, in milliseconds. Longer bars are slower.',
    note:
      'Measured on the TrustRAG fixture corpus. The naive baseline is faster because it performs no verification at all.',
    lowerIsBetter: true,
    metrics: [
      {
        label: 'TrustRAG hybrid RRF',
        value: 114,
        suffix: 'ms',
        width: '4.6%',
        lead: true,
        note: 'Verified',
      },
      {
        label: 'Dense RAG, no audit',
        value: 98,
        suffix: 'ms',
        width: '4%',
        note: 'Unverified',
      },
      {
        label: 'Cross-encoder reranker',
        value: 480,
        suffix: 'ms',
        width: '19.6%',
        note: 'No claims',
      },
      {
        label: 'Multi-agent critique loops',
        value: 2450,
        suffix: 'ms',
        width: '100%',
        note: 'No claims',
      },
    ],
  },
  memory: {
    id: 'memory',
    title: 'Vector storage per 100k chunks',
    desc:
      'Qdrant index footprint, comparing a 384-dimensional Matryoshka embedding against a 3072-dimensional one.',
    note: 'Index sizes measured from the local Qdrant collection.',
    lowerIsBetter: true,
    metrics: [
      {
        label: 'TrustRAG 384d Matryoshka',
        value: 153,
        suffix: 'MB',
        width: '12.5%',
        lead: true,
        note: 'Measured',
      },
      {
        label: 'text-embedding-3-large, 3072d',
        value: 1228,
        suffix: 'MB',
        width: '100%',
        note: 'Reference',
      },
      {
        label: 'gemini-embedding-001, 3072d',
        value: 1228,
        suffix: 'MB',
        width: '100%',
        note: 'Reference',
      },
    ],
  },
}

/* ── Comparison ───────────────────────────────────────────────────────────── */

export const COMPARISON_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'safety', label: 'Safety' },
  { id: 'retrieval', label: 'Retrieval' },
  { id: 'developer', label: 'Integration' },
]

export const COMPARISON_ROWS = [
  {
    category: 'safety',
    title: 'Hallucination detection',
    subtitle: 'Verification of individual factual statements in the output',
    naive:
      'Blind single-pass generation with no post-generation verification. A wrong statement passes silently to the reader.',
    ours:
      'Prose is decomposed into atomic propositional claims, then each is audited in parallel against its cited chunks.',
    impact: 'A wrong statement has to survive a check before it is shown.',
  },
  {
    category: 'safety',
    title: 'Closed-loop self-healing',
    subtitle: 'Recovery when a response fails verification',
    naive:
      'Broken or unverified output is returned directly, or the request fails with a generic error.',
    ours:
      'A LangGraph state machine rewrites the query and expands candidate retrieval, up to two attempts.',
    impact: 'Transient retrieval failures are resolved without a human in the loop.',
  },
  {
    category: 'retrieval',
    title: 'Retrieval algorithm and precision',
    subtitle: 'How documents are matched and ranked',
    naive:
      'Dense vectors only, which routinely misses statutory codes, part numbers and exact acronyms.',
    ours:
      'Dense and BM25 sparse retrieval combined with reciprocal rank fusion.',
    impact: 'Semantic context and exact keyword matches are both retrieved.',
  },
  {
    category: 'retrieval',
    title: 'Evidence provenance and tamper guard',
    subtitle: 'Integrity checking of the underlying sources',
    naive:
      'Blind trust in stored chunks. Silently tampered documents and stale cached vectors are cited.',
    ours:
      'SHA-256 root checksum checks and ISO temporal document expiry enforcement.',
    impact: 'A citation can be checked against the exact bytes it came from.',
  },
  {
    category: 'retrieval',
    title: 'Contextual disambiguation cost',
    subtitle: 'Parent document hierarchy and section context',
    naive:
      'Isolated chunks with no context, or an LLM call per chunk to restore it.',
    ours:
      'Parent document metadata is prepended without an LLM call, at no token cost.',
    impact: 'An orphaned passage arrives with the context needed to read it.',
  },
  {
    category: 'developer',
    title: 'Agent tooling and protocol support',
    subtitle: 'How external agents connect to the pipeline',
    naive:
      'A bespoke API wrapper per integration, each one to maintain.',
    ours:
      'A Model Context Protocol JSON-RPC 2.0 server, ready for Claude and Cursor.',
    impact: 'No SDK to adopt, and no custom client to maintain.',
  },
  {
    category: 'developer',
    title: 'Tenant vector isolation',
    subtitle: 'The security boundary between knowledge bases',
    naive:
      'Soft logical filters, or one shared vector space with a cross-tenant leakage risk.',
    ours:
      'Hard physical collection partitioning in Qdrant with tenant-scoped MongoDB indexes.',
    impact: 'The boundary is enforced by the store, not by application code.',
  },
]

/* ── Sandbox ──────────────────────────────────────────────────────────────── */

export const SCENARIOS = {
  entailment: {
    id: 'entailment',
    label: 'Atomic claim audit',
    doc: 'trustrag_sys_arch_v2.pdf',
    query:
      'How does TrustRAG decompose response prose into atomic claims and verify entailment against citations?',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'Generated response text is parsed into discrete, non-overlapping propositional assertions before citation alignment.',
        citation: 'chunk_04 · trustrag_sys_arch_v2.pdf · p. 12',
        confidence: '0.991',
      },
      {
        id: 2,
        status: 'contradicted',
        text: 'Claim verification relies on single-pass heuristic pattern matching with no semantic cross-encoder inference.',
        conflict:
          'Invariant breach — the system runs a Pydantic batch entailment matrix across every context chunk.',
        initialScore: '0.524',
      },
      {
        id: 3,
        status: 'supported',
        text: 'Audited claims are classified as entailed, contradicted or neutral, with a quantitative confidence score.',
        citation: 'chunk_18 · trustrag_sys_arch_v2.pdf · p. 29',
        confidence: '0.986',
      },
    ],
    recovery: {
      action:
        'LangGraph intercepted the contradiction, rewrote the sub-query for the entailment path, and replaced the heuristic assertion with a verified clause.',
      finalScore: '0.984',
      healed:
        'Verification executes a batch entailment cross-examination across every cited chunk, scoring each claim before any token is emitted.',
    },
  },
  recovery: {
    id: 'recovery',
    label: 'Self-healing loop',
    doc: 'langgraph_agent_spec.pdf',
    query:
      'Which recovery graph is triggered when aggregate claim verification drops below the 0.70 confidence threshold?',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'The agent state machine tracks recovery attempts with a deterministic upper bound of two recursive iterations.',
        citation: 'chunk_22 · langgraph_agent_spec.pdf · p. 18',
        confidence: '0.994',
      },
      {
        id: 2,
        status: 'contradicted',
        text: 'When confidence falls below threshold, the engine yields ungrounded parametric model memory to avoid user latency.',
        conflict:
          'Invariant breach — the engine enters a bounded recovery DAG, triggering query reformulation and context expansion.',
        initialScore: '0.587',
      },
      {
        id: 3,
        status: 'supported',
        text: 'If the recovery bound is exhausted without reaching 0.70, the query is routed deterministically to an abstention state.',
        citation: 'chunk_31 · langgraph_agent_spec.pdf · p. 24',
        confidence: '0.979',
      },
    ],
    recovery: {
      action:
        'The cyclical recovery edge fired on the threshold breach, candidate retrieval was widened to top-40 vectors with RRF, and the entailment matrix was re-evaluated.',
      finalScore: '0.972',
      healed:
        'When confidence breaches a safety boundary, the engine expands the query and retrieves corroborating evidence rather than emitting ungrounded output.',
    },
  },
  provenance: {
    id: 'provenance',
    label: 'Provenance guard',
    doc: 'vector_store_integrity.pdf',
    query:
      'How does TrustRAG combine dense vectors with BM25, and guarantee that cited evidence has not been tampered with?',
    claims: [
      {
        id: 1,
        status: 'supported',
        text: 'Reciprocal rank fusion combines the dense and sparse result lists into a single ordering.',
        citation: 'chunk_07 · vector_store_integrity.pdf · p. 9',
        confidence: '0.989',
      },
      {
        id: 2,
        status: 'contradicted',
        text: 'Chunk integrity is assured by the vector index alone, so a modified document is still cited with confidence.',
        conflict:
          'Invariant breach — every chunk is checked against the SHA-256 root hash of its source document.',
        initialScore: '0.461',
      },
      {
        id: 3,
        status: 'supported',
        text: 'Documents carry an effective_until date, and expired evidence is pruned before it can be scored.',
        citation: 'chunk_14 · vector_store_integrity.pdf · p. 21',
        confidence: '0.976',
      },
    ],
    recovery: {
      action:
        'The contradiction was routed to the integrity path, the document root hash was recomputed, and the citation was bound to the verified bytes.',
      finalScore: '0.981',
      healed:
        'Evidence is bound to a SHA-256 root checksum and an ISO validity window, and a chunk that no longer matches is discarded before scoring.',
    },
  },
}

/* ── Closing CTA ──────────────────────────────────────────────────────────── */

export const CTA = {
  headline: 'Put a claim checker in front of your answers.',
  lede:
    'Deploy a knowledge base, audit what the model claims, and recover the answers that do not hold up — before a reader finds the gap.',
}

/* ── Footer ───────────────────────────────────────────────────────────────── */

export const FOOTER = {
  tagline:
    'An open reliability workbench for retrieval-augmented generation. Claim decomposition, entailment audit, and bounded self-healing.',
  groups: [
    {
      title: 'Workbench',
      links: [
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Playground', to: '/playground' },
        { label: 'Knowledge bases', to: '/knowledge-bases' },
      ],
    },
    {
      title: 'Evidence',
      links: [
        { label: 'Evidence vault', to: '/evidence' },
        { label: 'Claim inspector', to: '/claims' },
        { label: 'Conflicts', to: '/conflicts' },
      ],
    },
    {
      title: 'System',
      links: [
        { label: 'Settings', to: '/settings' },
        { label: 'Execution traces', to: '/dashboard' },
      ],
    },
  ],
  legal: [
    { label: 'Licence', to: '/settings' },
    { label: 'Documentation', to: '/settings' },
  ],
}
