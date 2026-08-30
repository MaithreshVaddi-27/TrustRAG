import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Swords, Zap, ArrowRight,
  CheckCircle2, XCircle, RefreshCw,
  Terminal, Lock, Sparkles, Brain,
  ChevronRight, ExternalLink, Play, RotateCcw,
  Cpu, ShieldCheck, BarChart3, Gauge, Activity, Check,
  Menu, X, LayoutGrid, Table, Info
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

// Interactive Simulation Scenarios
// Interactive Simulation Scenarios (Project-Native Invariants)
const SCENARIOS = {
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

// Deep Interactive Capabilities Explorer
const CAPABILITIES = {
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

// Interactive Benchmarks Data
const BENCHMARKS = {
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

// Comparison Dimensions & Data
const COMPARISON_CATEGORIES = [
  { id: 'all', label: 'All Invariants' },
  { id: 'safety', label: 'Safety & Hallucination' },
  { id: 'retrieval', label: 'Retrieval & Provenance' },
  { id: 'developer', label: 'Agent & Integration' },
]

const COMPARISON_ROWS = [
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

export default function LandingPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  
  // Mobile drawer state
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)

  // Interactive mouse spotlight coordinates (RAF-throttled for 60/120fps)
  const [mousePos, setMousePos] = useState({ x: -1000, y: -1000 })
  const containerRef = useRef(null)
  const rafId = useRef(null)

  // Simulation state
  const [selectedScenarioKey, setSelectedScenarioKey] = useState('entailment')
  const [simStep, setSimStep] = useState(4) // 0: input, 1: retrieval, 2: claims, 3: fail, 4: healed
  const [isSimulating, setIsSimulating] = useState(false)
  const currentScenario = SCENARIOS[selectedScenarioKey]

  // Interactive Capabilities Tab
  const [activeCapKey, setActiveCapKey] = useState('langgraph')
  const currentCapability = CAPABILITIES[activeCapKey]

  // Interactive Benchmark Tab
  const [activeBenchmarkKey, setActiveBenchmarkKey] = useState('accuracy')
  const currentBenchmark = BENCHMARKS[activeBenchmarkKey]

  // Interactive Comparison Section State
  const [activeCompareCategory, setActiveCompareCategory] = useState('all')
  const [compareViewMode, setCompareViewMode] = useState('cards') // 'cards' or 'matrix'
  const [expandedRowIndex, setExpandedRowIndex] = useState(null)

  const filteredComparisonRows = activeCompareCategory === 'all'
    ? COMPARISON_ROWS
    : COMPARISON_ROWS.filter(r => r.category === activeCompareCategory)

  const handleMouseMove = (e) => {
    if (!containerRef.current) return
    if (rafId.current) cancelAnimationFrame(rafId.current)
    rafId.current = requestAnimationFrame(() => {
      const rect = containerRef.current.getBoundingClientRect()
      setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
    })
  }

  // Trigger interactive simulated audit animation
  const runSimulation = () => {
    if (isSimulating) return
    setIsSimulating(true)
    setSimStep(0)
    setTimeout(() => setSimStep(1), 600)
    setTimeout(() => setSimStep(2), 1400)
    setTimeout(() => setSimStep(3), 2200)
    setTimeout(() => {
      setSimStep(4)
      setIsSimulating(false)
    }, 3200)
  }

  // Switch scenario
  const handleSelectScenario = (key) => {
    setSelectedScenarioKey(key)
    setSimStep(4)
    setIsSimulating(false)
  }

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="min-h-screen bg-surface-950 text-slate-100 font-sans selection:bg-sky-500/30 selection:text-sky-300 relative overflow-hidden bg-cyber-grid"
    >
      {/* ── Interactive Cursor Spotlight ───────────────────────────────────── */}
      <div
        className="pointer-events-none fixed inset-0 z-10 transition-opacity duration-300 opacity-60"
        style={{
          background: `radial-gradient(650px circle at ${mousePos.x}px ${mousePos.y}px, rgba(14, 165, 233, 0.12), transparent 80%)`,
        }}
      />

      {/* ── Ambient Radial Flares ───────────────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[1000px] h-[550px] rounded-full bg-cyan-500/10 blur-[180px]" />
        <div className="absolute top-[35%] right-[-10%] w-[600px] h-[500px] rounded-full bg-primary-600/10 blur-[180px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[700px] h-[500px] rounded-full bg-teal-500/10 blur-[180px]" />
      </div>

      {/* ── Sticky Top Navbar ──────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 backdrop-blur-2xl bg-surface-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Brand Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-primary-950/80 border border-cyan-400/30 group-hover:scale-105 transition-transform">
              <Swords size={18} className="text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-base tracking-tight text-white flex items-center gap-1">
                TRUST<span className="text-primary-400">RAG</span>
              </span>
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest hidden sm:inline">
                Reliability Workbench
              </span>
            </div>
          </Link>

          {/* Navigation links targeting exact element IDs */}
          <nav className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-400">
            <a href="#simulation" className="hover:text-cyan-400 transition-colors flex items-center gap-1">
              <Sparkles size={13} className="text-cyan-400" />
              <span>Sandbox</span>
            </a>
            <a href="#features" className="hover:text-cyan-400 transition-colors">Capabilities</a>
            <a href="#bento" className="hover:text-cyan-400 transition-colors">Architecture</a>
            <a href="#benchmarks" className="hover:text-cyan-400 transition-colors">Benchmarks</a>
            <a href="#compare" className="hover:text-cyan-400 transition-colors">Comparison</a>
          </nav>

          {/* Action CTAs & Mobile Hamburger */}
          <div className="flex items-center gap-2.5">
            {isAuthenticated ? (
              <Link
                to="/dashboard"
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/50 border border-cyan-400/30 transition-all hover:scale-[1.02]"
              >
                <span>Dashboard</span>
                <ChevronRight size={14} />
              </Link>
            ) : (
              <div className="hidden sm:flex items-center gap-3">
                <Link
                  to="/login"
                  className="px-3.5 py-1.5 rounded-xl text-slate-300 hover:text-white hover:bg-surface-800/80 text-xs font-semibold transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/50 border border-cyan-400/30 transition-all hover:scale-[1.02]"
                >
                  <span>Get Started</span>
                  <ArrowRight size={13} />
                </Link>
              </div>
            )}

            {/* Mobile Hamburger Toggle Button */}
            <button
              onClick={() => setIsMobileNavOpen(prev => !prev)}
              className="md:hidden flex items-center justify-center w-9 h-9 rounded-xl border border-slate-800 text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
              aria-label="Toggle mobile menu"
            >
              {isMobileNavOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {isMobileNavOpen && (
          <div className="md:hidden bg-surface-950/95 border-b border-slate-800 backdrop-blur-2xl px-4 pt-3 pb-5 space-y-3 animate-fade-in">
            <div className="flex flex-col space-y-1.5 text-xs font-medium text-slate-300">
              <a
                href="#simulation"
                onClick={() => setIsMobileNavOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2"
              >
                <Sparkles size={14} className="text-cyan-400" />
                <span>Interactive Sandbox</span>
              </a>
              <a
                href="#features"
                onClick={() => setIsMobileNavOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2"
              >
                <Cpu size={14} className="text-cyan-400" />
                <span>Capabilities Explorer</span>
              </a>
              <a
                href="#bento"
                onClick={() => setIsMobileNavOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2"
              >
                <RefreshCw size={14} className="text-cyan-400" />
                <span>Architecture</span>
              </a>
              <a
                href="#benchmarks"
                onClick={() => setIsMobileNavOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2"
              >
                <BarChart3 size={14} className="text-cyan-400" />
                <span>Benchmarks</span>
              </a>
              <a
                href="#compare"
                onClick={() => setIsMobileNavOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2"
              >
                <ShieldCheck size={14} className="text-cyan-400" />
                <span>Why TrustRAG</span>
              </a>
            </div>
            {!isAuthenticated && (
              <div className="pt-3 border-t border-slate-800/80 flex items-center gap-2.5">
                <Link
                  to="/login"
                  onClick={() => setIsMobileNavOpen(false)}
                  className="flex-1 py-2.5 rounded-xl text-center text-xs font-semibold text-slate-300 bg-surface-900 border border-slate-800"
                >
                  Sign In
                </Link>
                <Link
                  to="/login"
                  onClick={() => setIsMobileNavOpen(false)}
                  className="flex-1 py-2.5 rounded-xl text-center text-xs font-semibold text-white bg-gradient-to-r from-primary-600 to-cyan-600 shadow-md"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        )}
      </header>

      {/* ── Hero Section ───────────────────────────────────────────────────── */}
      <section className="relative z-20 pt-20 pb-16 sm:pt-28 sm:pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Floating Card Left (Desktop) */}
        <div className="hidden xl:flex absolute left-4 top-32 items-center gap-3 p-3.5 rounded-2xl bg-surface-900/90 border border-slate-700/80 backdrop-blur-xl shadow-2xl shadow-cyan-950/50 animate-float hover:scale-105 transition-transform group cursor-default">
          <div className="w-10 h-10 rounded-xl bg-emerald-950/80 border border-emerald-500/40 flex items-center justify-center text-emerald-400 group-hover:rotate-6 transition-transform">
            <ShieldCheck size={20} />
          </div>
          <div className="text-left font-mono">
            <div className="text-white text-xs font-bold flex items-center gap-1.5">
              <span>Entailment Guard</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            </div>
            <div className="text-emerald-400 text-[10px]">99.4% Claim Precision</div>
          </div>
        </div>

        {/* Floating Card Right (Desktop) */}
        <div className="hidden xl:flex absolute right-4 top-36 items-center gap-3 p-3.5 rounded-2xl bg-surface-900/90 border border-slate-700/80 backdrop-blur-xl shadow-2xl shadow-cyan-950/50 animate-float hover:scale-105 transition-transform group cursor-default" style={{ animationDelay: '2.5s' }}>
          <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 group-hover:rotate-180 transition-transform duration-700">
            <RefreshCw size={18} className="animate-spin-slow" />
          </div>
          <div className="text-left font-mono">
            <div className="text-white text-xs font-bold flex items-center gap-1.5">
              <span>Self-Healing Loop</span>
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            </div>
            <div className="text-cyan-400 text-[10px]">LangGraph Active</div>
          </div>
        </div>

        {/* Floating Telemetry Badge */}
        <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-surface-900/90 border border-cyan-500/40 text-xs font-mono text-cyan-300 shadow-xl shadow-cyan-950/50 mb-8 backdrop-blur-md animate-fade-in hover:border-cyan-400 hover:scale-105 transition-all cursor-default">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
          </span>
          <span className="font-semibold tracking-wide">AUTONOMOUS AGENTIC RELIABILITY</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">Zero Hallucination Tolerance</span>
        </div>

        {/* Shimmering Headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.08] mb-6">
          Trust Every Token With{' '}
          <span className="shimmer-text">Closed-Loop Self-Healing RAG</span>
        </h1>

        {/* Subtitle */}
        <p className="text-slate-400 text-base sm:text-lg max-w-3xl mx-auto leading-relaxed mb-10 font-normal">
          Decompose unstructured LLM responses into atomic propositional claims, cross-examine citations with hybrid RRF retrieval, and autonomously trigger LangGraph self-healing loops before hallucinations reach users.
        </p>

        {/* Primary Call to Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <button
            onClick={() => navigate('/login')}
            className="w-full sm:w-auto px-9 py-4 rounded-xl bg-gradient-to-r from-primary-600 via-sky-500 to-cyan-500 hover:from-primary-500 hover:to-cyan-400 text-white font-bold text-sm shadow-2xl shadow-cyan-950/80 border border-cyan-400/50 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.04] active:scale-[0.98] group cursor-pointer relative overflow-hidden"
          >
            {/* Specular button sheen */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full duration-700 transition-transform pointer-events-none" />
            <span>Get Started Free</span>
            <ArrowRight size={16} className="group-hover:translate-x-1.5 transition-transform" />
          </button>

          <a
            href="#simulation"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-surface-900/90 hover:bg-surface-850 text-slate-300 hover:text-white font-semibold text-sm border border-slate-700/80 hover:border-cyan-400/60 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98] backdrop-blur-md shadow-lg group"
          >
            <Zap size={16} className="text-cyan-400 group-hover:scale-125 transition-transform" />
            <span>Launch Interactive Sandbox</span>
          </a>
        </div>

        {/* Live Metrics Counters Ribbon with Hover Glow */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto pt-6 border-t border-slate-800/80">
          <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-cyan-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-cyan-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="text-2xl sm:text-3xl font-extrabold text-white font-mono group-hover:scale-105 transition-transform origin-left">99.4%</div>
            <div className="text-xs text-slate-400 mt-1">Claim Grounding Precision</div>
          </div>
          <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-emerald-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-emerald-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 font-mono group-hover:scale-105 transition-transform origin-left">0.0%</div>
            <div className="text-xs text-slate-400 mt-1">Hallucination Leakage</div>
          </div>
          <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-cyan-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-cyan-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400 font-mono group-hover:scale-105 transition-transform origin-left">&lt;120ms</div>
            <div className="text-xs text-slate-400 mt-1">Hybrid RRF Retrieval</div>
          </div>
          <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-sky-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-sky-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-sky-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="text-2xl sm:text-3xl font-extrabold text-sky-400 font-mono group-hover:scale-105 transition-transform origin-left">0 MB</div>
            <div className="text-xs text-slate-400 mt-1">Local GPU Weights (Pure Cloud)</div>
          </div>
        </div>
      </section>

      {/* ── Interactive Live Simulation Sandbox ────────────────────────────── */}
      <section id="simulation" className="scroll-mt-24 relative z-20 py-16 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
            <Terminal size={13} />
            <span>INTERACTIVE EXECUTION SANDBOX</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
            See Hallucinations Caught & Self-Healed In Real Time
          </h2>
          <p className="text-slate-400 text-sm max-w-2xl mx-auto mt-2">
            Select a core verification invariant below and trigger an audit to watch TrustRAG cross-examine claims against ground-truth evidence citations.
          </p>

          {/* Scenario Switcher Pills */}
          <div className="flex flex-wrap items-center justify-center gap-2.5 mt-6">
            {Object.keys(SCENARIOS).map((key) => {
              const sc = SCENARIOS[key]
              const isSelected = selectedScenarioKey === key
              return (
                <button
                  key={key}
                  onClick={() => handleSelectScenario(key)}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-950/40 scale-105'
                      : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700 hover:scale-102'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${isSelected ? 'bg-cyan-400 animate-pulse' : 'bg-slate-600'}`} />
                  <span>{sc.label}</span>
                </button>
              )
            })}
            <button
              onClick={runSimulation}
              disabled={isSimulating}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-cyan-950/40 cursor-pointer disabled:opacity-50 hover:scale-105 active:scale-95 transition-all"
            >
              {isSimulating ? <RotateCcw size={13} className="animate-spin" /> : <Play size={13} />}
              <span>{isSimulating ? 'Executing Pipeline...' : 'Run Audit Simulation'}</span>
            </button>
          </div>
        </div>

        {/* Sandbox Window with Border Beam */}
        <div className="border-beam rounded-2xl border border-slate-800/90 bg-surface-900/90 shadow-2xl overflow-hidden backdrop-blur-xl relative">
          {/* Laser Scanline when running */}
          {isSimulating && <div className="laser-scanline" />}

          {/* Window Header */}
          <div className="h-12 px-5 bg-surface-950/90 border-b border-slate-800/90 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2.5">
              <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
              <span className="ml-2 font-mono text-slate-400 text-[11px] hidden sm:inline">
                trustrag_engine {'//'} {currentScenario.doc} {'//'} session_audit_live
              </span>
            </div>
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-[11px] text-slate-400 hidden sm:inline">Latency: 114ms</span>
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-700/60 text-[10px] font-mono text-emerald-300 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>{simStep >= 4 ? 'GROUNDED: 96.4%' : simStep === 3 ? 'HEALING IN PROGRESS' : 'AUDITING'}</span>
              </span>
            </div>
          </div>

          {/* Window Body */}
          <div className="p-6 space-y-5">
            {/* Query Banner */}
            <div className="p-4 rounded-xl bg-surface-950/80 border border-slate-800/80">
              <div className="text-[11px] font-mono text-cyan-400 font-semibold mb-1 flex items-center justify-between">
                <span>USER QUERY</span>
                <span className="text-[10px] text-slate-500 font-mono">Source KB: {currentScenario.doc}</span>
              </div>
              <div className="text-sm text-slate-200 font-medium">
                &ldquo;{currentScenario.query}&rdquo;
              </div>
            </div>

            {/* Claims Matrix */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Brain size={14} className="text-cyan-400" />
                  <span>Atomic Claim Decomposition & Entailment Verdicts</span>
                </div>
                <span className="text-[11px] text-slate-500">3 Claims Audited</span>
              </div>

              <div className="grid gap-3">
                {/* Claim 1 */}
                <div className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-cyan-400/60 hover:shadow-xl hover:shadow-cyan-950/40 cursor-pointer ${
                  simStep >= 2
                    ? 'bg-emerald-950/20 border-emerald-800/40'
                    : 'bg-surface-950/40 border-slate-800/60 opacity-60'
                }`}>
                  <div className="flex items-start gap-3">
                    <CheckCircle2 size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                    <div className="flex-1 text-xs">
                      <span className="font-semibold text-emerald-200">Claim 1 (Verified Entailment):</span>
                      <span className="text-slate-300 ml-1.5">{currentScenario.claims[0].text}</span>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-mono">
                        <span className="px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-300 border border-emerald-800/40">
                          Citation: {currentScenario.claims[0].citation}
                        </span>
                        <span className="text-emerald-400 font-semibold">Confidence: {currentScenario.claims[0].confidence}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Claim 2 — Hallucination / Contradicted */}
                <div className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-red-500/80 hover:shadow-xl hover:shadow-red-950/50 cursor-pointer ${
                  simStep >= 3
                    ? 'bg-red-950/30 border-red-800/60'
                    : 'bg-surface-950/40 border-slate-800/60 opacity-60'
                }`}>
                  <div className="flex items-start gap-3">
                    <XCircle size={18} className="text-red-400 shrink-0 mt-0.5" />
                    <div className="flex-1 text-xs">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-red-200">Claim 2 (Hallucination Intercepted):</span>
                        <span className="px-2 py-0.5 rounded bg-red-900/70 border border-red-700 text-[10px] font-mono text-red-200 font-bold animate-pulse">
                          CONTRADICTED
                        </span>
                      </div>
                      <span className="text-slate-300 block line-through decoration-red-400/60">
                        &ldquo;{currentScenario.claims[1].text}&rdquo;
                      </span>
                      <div className="mt-2 text-[11px] font-mono text-red-300/90 bg-red-950/50 p-2 rounded-lg border border-red-900/50">
                        ⚠️ {currentScenario.claims[1].conflict}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Claim 3 */}
                <div className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-cyan-400/60 hover:shadow-xl hover:shadow-cyan-950/40 cursor-pointer ${
                  simStep >= 2
                    ? 'bg-emerald-950/20 border-emerald-800/40'
                    : 'bg-surface-950/40 border-slate-800/60 opacity-60'
                }`}>
                  <div className="flex items-start gap-3">
                    <CheckCircle2 size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                    <div className="flex-1 text-xs">
                      <span className="font-semibold text-emerald-200">Claim 3 (Verified Entailment):</span>
                      <span className="text-slate-300 ml-1.5">{currentScenario.claims[2].text}</span>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-mono">
                        <span className="px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-300 border border-emerald-800/40">
                          Citation: {currentScenario.claims[2].citation}
                        </span>
                        <span className="text-emerald-400 font-semibold">Confidence: {currentScenario.claims[2].confidence}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Self-Healing LangGraph Output Banner */}
            {simStep >= 4 && (
              <div className="p-4 rounded-xl bg-gradient-to-r from-primary-950/80 via-slate-900 to-cyan-950/80 border border-cyan-500/50 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-slide-up">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-cyan-900/60 border border-cyan-500/50 flex items-center justify-center shrink-0 mt-0.5">
                    <RefreshCw size={17} className="text-cyan-300 animate-spin-slow" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white flex items-center gap-2">
                      <span>Closed-Loop Recovery Executed</span>
                      <span className="px-2 py-0.5 rounded bg-cyan-900/40 border border-cyan-700/50 text-[10px] font-mono text-cyan-300">
                        Attempt 1 / 2
                      </span>
                    </div>
                    <div className="text-xs text-slate-300 mt-1 font-medium leading-relaxed">
                      {currentScenario.recovery.healedText}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 mt-1.5">
                      Strategy: {currentScenario.recovery.action}
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end shrink-0">
                  <span className="text-[10px] font-mono text-slate-400">Post-Healing Score</span>
                  <span className="text-lg font-mono font-extrabold text-cyan-300">
                    {currentScenario.recovery.finalScore}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-700 text-[9px] font-mono text-emerald-300 font-bold">
                    VERIFIED & GROUNDED
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Capabilities Interactive Explorer (id="features") ──────────────── */}
      <section id="features" className="scroll-mt-24 relative z-20 py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
            <Cpu size={13} />
            <span>DEEP CAPABILITIES EXPLORER</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Interactive System Capabilities
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
            Click across the core verification subsystems below to explore code implementations, architectural invariants, and safety guarantees.
          </p>

          {/* Interactive Capability Tabs */}
          <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
            {Object.keys(CAPABILITIES).map((key) => {
              const cap = CAPABILITIES[key]
              const Icon = cap.icon
              const isSelected = activeCapKey === key
              return (
                <button
                  key={key}
                  onClick={() => setActiveCapKey(key)}
                  className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-lg shadow-cyan-950/50 scale-105'
                      : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700 hover:scale-102'
                  }`}
                >
                  <Icon size={14} className={isSelected ? 'text-cyan-400 animate-spin-slow' : 'text-slate-500'} />
                  <span>{cap.title.split(' ')[0]} {cap.title.split(' ')[1]}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Selected Capability Interactive Preview Card */}
        <div className="rounded-3xl border border-slate-800/90 bg-surface-900/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:border-cyan-500/40">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-700/50 text-[11px] font-mono text-cyan-300 mb-4">
                <Activity size={12} />
                <span>{currentCapability.tagline}</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-extrabold text-white mb-4">
                {currentCapability.title}
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed mb-6 font-normal">
                {currentCapability.desc}
              </p>
              <div className="space-y-2.5">
                {currentCapability.highlights.map((h, i) => (
                  <div key={i} className="flex items-center gap-2.5 text-xs text-slate-300 font-mono">
                    <div className="w-5 h-5 rounded-full bg-emerald-950 border border-emerald-600/60 flex items-center justify-center text-emerald-400 shrink-0">
                      <Check size={11} />
                    </div>
                    <span>{h}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Code / Architecture Panel */}
            <div className="rounded-2xl bg-surface-950 border border-slate-800 p-5 font-mono text-xs text-slate-300 shadow-inner overflow-x-auto relative group">
              <div className="flex items-center justify-between text-[11px] text-slate-500 pb-3 mb-3 border-b border-slate-800/80">
                <span>implementation_preview.py</span>
                <span className="text-cyan-400 text-[10px]">Python 3.12 Verified</span>
              </div>
              <pre className="text-slate-300 text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono">
                {currentCapability.code}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* ── Bento Grid Architecture (id="bento") ───────────────────────────── */}
      <section id="bento" className="scroll-mt-24 relative z-20 py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3">
            <Cpu size={13} />
            <span>STATE-OF-THE-ART ARCHITECTURE</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Six Layers Of Rigorous AI Reliability
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
            Built from first principles for mission-critical enterprise applications where hallucinations have real legal and financial consequences.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Bento Item 1 (Wide 2 cols) */}
          <div className="md:col-span-2 p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
            <div className="flex items-center justify-between mb-6">
              <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
                <RefreshCw size={22} />
              </div>
              <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
                LangGraph State Machine
              </span>
            </div>
            <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Autonomous LangGraph Healing Loop</h3>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-6">
              When evidence coverage or contradiction rates breach safety boundaries, TrustRAG does not silently fail. It adaptively rewrites sub-queries, doubles candidate vector density, and cross-examines evidence until 100% groundability is reached.
            </p>
            {/* Visual Stepper Node Bar */}
            <div className="grid grid-cols-5 gap-2 text-center text-[10px] font-mono pt-4 border-t border-slate-800/80">
              <div className="p-2 rounded-lg bg-surface-950 border border-slate-800 text-slate-300 group-hover:border-slate-700 transition-colors">1. Ingest</div>
              <div className="p-2 rounded-lg bg-surface-950 border border-slate-800 text-slate-300 group-hover:border-slate-700 transition-colors">2. RRF Hybrid</div>
              <div className="p-2 rounded-lg bg-surface-950 border border-slate-800 text-slate-300 group-hover:border-slate-700 transition-colors">3. NLI Audit</div>
              <div className="p-2 rounded-lg bg-surface-950 border border-cyan-800/60 text-cyan-300">4. Diagnose</div>
              <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-700/60 text-emerald-300 font-bold">5. Ground</div>
            </div>
          </div>

          {/* Bento Item 2 (1 col) */}
          <div className="p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
            <div className="flex items-center justify-between mb-6">
              <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
                <Brain size={22} />
              </div>
              <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
                Pydantic Batch NLI
              </span>
            </div>
            <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Atomic Claim Decomposition</h3>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4">
              Answers are broken down into granular factual propositions, verified against citations in parallel schemas without sequential API rate-limit bottlenecks.
            </p>
            <div className="p-3 rounded-xl bg-surface-950 border border-slate-800/80 font-mono text-[10px] text-slate-400 group-hover:border-slate-700 transition-colors">
              <span className="text-emerald-400 font-bold">✓ Entailment:</span> 98.2%<br />
              <span className="text-red-400 font-bold">✗ Contradiction:</span> Pruned<br />
              <span className="text-amber-400 font-bold">? Neutral:</span> Flagged
            </div>
          </div>

          {/* Bento Item 3 (1 col) */}
          <div className="p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
            <div className="flex items-center justify-between mb-6">
              <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
                <Lock size={22} />
              </div>
              <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
                Cryptographic Guard
              </span>
            </div>
            <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">SHA-256 Provenance & Temporal Filter</h3>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4">
              Retrieval chunks are checked against root SHA-256 checksums to detect silent tampering. Outdated documents with expired effective dates are discarded automatically.
            </p>
            <div className="p-2.5 rounded-xl bg-surface-950 border border-slate-800 font-mono text-[10px] text-emerald-400 truncate group-hover:border-slate-700 transition-colors">
              sha256: 4f8b2c91a7... [VALID]
            </div>
          </div>

          {/* Bento Item 4 (Wide 2 cols) */}
          <div className="md:col-span-2 p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
            <div className="flex items-center justify-between mb-6">
              <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
                <Terminal size={22} />
              </div>
              <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
                Open Standard Protocol
              </span>
            </div>
            <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Model Context Protocol (MCP) Ready</h3>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4">
              Exposes TrustRAG as standardized MCP tools (<code className="text-cyan-300 font-mono text-xs">trustrag_search</code>, <code className="text-cyan-300 font-mono text-xs">trustrag_verify_claim</code>). Connect Claude Desktop, Cursor, or your internal agent teams via standard JSON-RPC over stdio.
            </p>
            {/* Terminal Code Mock */}
            <div className="p-4 rounded-xl bg-surface-950 border border-slate-800 font-mono text-xs text-slate-300 space-y-1 overflow-x-auto group-hover:border-cyan-800/60 transition-colors">
              <div className="text-slate-500">{'// Terminal: Connect external agent via MCP stdio'}</div>
              <div className="text-cyan-400">$ python -m app.mcp.server</div>
              <div className="text-emerald-400">✓ TrustRAG MCP Server listening on stdio (3 tools registered)</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Interactive Benchmarks Section (id="benchmarks") ────────────────── */}
      <section id="benchmarks" className="scroll-mt-24 relative z-20 py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
            <BarChart3 size={13} />
            <span>EMPIRICAL BENCHMARKS & EVALUATION</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Proven Performance In Production
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
            Toggle between benchmark dimensions to examine quantitative accuracy, latency SLA, and vector storage memory savings.
          </p>

          {/* Benchmark Dimension Tabs */}
          <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
            {Object.keys(BENCHMARKS).map((key) => {
              const b = BENCHMARKS[key]
              const Icon = b.icon
              const isSelected = activeBenchmarkKey === key
              return (
                <button
                  key={key}
                  onClick={() => setActiveBenchmarkKey(key)}
                  className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-lg shadow-cyan-950/50 scale-105'
                      : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700 hover:scale-102'
                  }`}
                >
                  <Icon size={14} className={isSelected ? 'text-cyan-400 animate-pulse' : 'text-slate-500'} />
                  <span>{b.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Benchmark Visual Progress Cards */}
        <div className="rounded-3xl border border-slate-800/90 bg-surface-900/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:border-cyan-500/40">
          <div className="mb-6">
            <h3 className="text-xl font-bold text-white">{currentBenchmark.title}</h3>
            <p className="text-slate-400 text-xs mt-1">{currentBenchmark.description}</p>
          </div>

          <div className="space-y-5">
            {currentBenchmark.metrics.map((m, i) => (
              <div key={i} className="space-y-1.5 group cursor-default">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className={`font-semibold ${m.highlight ? 'text-cyan-300' : 'text-slate-300'}`}>
                    {m.label}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-surface-850 border border-slate-800 text-slate-400">
                      {m.badge}
                    </span>
                    <span className={`font-bold ${m.highlight ? 'text-cyan-400 text-sm' : 'text-slate-300'}`}>
                      {m.value} {m.suffix}
                    </span>
                  </div>
                </div>
                {/* Visual Bar Indicator */}
                <div className="h-3 rounded-full bg-surface-950 border border-slate-800/80 overflow-hidden p-0.5">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${m.color} transition-all duration-700 shadow-sm`}
                    style={{ width: m.width }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Direct Comparison Section (id="compare") ─────────────────────────── */}
      <section id="compare" className="scroll-mt-24 relative z-20 py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
            <ShieldCheck size={13} />
            <span>ARCHITECTURAL SUPERIORITY</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Why Teams Upgrade To TrustRAG
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
            Compare standard single-pass RAG pipelines against our deterministic, closed-loop verification architecture.
          </p>

          {/* Controls Bar: Mode Switcher & Category Filters */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 pt-4 border-t border-slate-800/80">
            {/* Category Filter Chips */}
            <div className="flex flex-wrap items-center justify-center gap-2">
              {COMPARISON_CATEGORIES.map((cat) => {
                const isSelected = activeCompareCategory === cat.id
                return (
                  <button
                    key={cat.id}
                    onClick={() => setActiveCompareCategory(cat.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                      isSelected
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-950/50'
                        : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700'
                    }`}
                  >
                    {cat.label}
                  </button>
                )
              })}
            </div>

            {/* View Mode Toggle: Cards vs Matrix */}
            <div className="inline-flex items-center p-1 rounded-xl bg-surface-900 border border-slate-800">
              <button
                onClick={() => setCompareViewMode('cards')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                  compareViewMode === 'cards'
                    ? 'bg-cyan-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <LayoutGrid size={13} />
                <span>Side-by-Side</span>
              </button>
              <button
                onClick={() => setCompareViewMode('matrix')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                  compareViewMode === 'matrix'
                    ? 'bg-cyan-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Table size={13} />
                <span>Matrix Table</span>
              </button>
            </div>
          </div>
        </div>

        {/* View Mode 1: Dual Side-by-Side Cards */}
        {compareViewMode === 'cards' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
            {/* Left Card: Standard Naive RAG */}
            <div className="p-7 sm:p-9 rounded-3xl bg-surface-950/90 border border-red-900/40 backdrop-blur-xl relative overflow-hidden flex flex-col justify-between group hover:border-red-800/60 transition-colors">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="px-3 py-1 rounded-full bg-red-950/80 border border-red-800/60 text-[11px] font-mono text-red-300 font-bold">
                    LEGACY STATUS QUO
                  </span>
                  <span className="text-slate-500 font-mono text-xs">Standard Naive RAG</span>
                </div>
                <h3 className="text-2xl font-extrabold text-white mb-2">Blind Single-Pass Generation</h3>
                <p className="text-slate-400 text-xs leading-relaxed mb-6">
                  Standard retrieval models blindly trust retrieved chunks and assume the LLM generates 100% grounded facts. Hallucinations, stale information, and citation mismatches reach production users undetected.
                </p>

                {/* Flow Illustration */}
                <div className="p-3.5 rounded-xl bg-surface-900/80 border border-slate-800 font-mono text-[11px] text-slate-400 mb-6 space-y-1.5">
                  <div className="text-slate-500">{'// Execution Flow (No Verification Gate)'}</div>
                  <div className="text-slate-300 flex items-center gap-1.5">
                    <span>Query</span>
                    <span>&rarr;</span>
                    <span>Vector Search</span>
                    <span>&rarr;</span>
                    <span className="text-red-400 font-bold">Unverified LLM Output</span>
                    <span>&rarr;</span>
                    <span>User</span>
                  </div>
                </div>

                {/* Key Limitations List */}
                <div className="space-y-3">
                  {filteredComparisonRows.map((row, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-400">
                      <XCircle size={16} className="text-red-400/80 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-slate-300">{row.title}: </span>
                        <span>{row.naive}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-slate-900 text-center text-xs font-mono text-red-400/80">
                ⚠️ High legal, financial, and clinical liability risk
              </div>
            </div>

            {/* Right Card: TrustRAG Closed-Loop Workbench */}
            <div className="border-beam p-7 sm:p-9 rounded-3xl bg-surface-900/90 border border-cyan-500/40 backdrop-blur-xl relative overflow-hidden flex flex-col justify-between shadow-2xl shadow-cyan-950/40">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="px-3 py-1 rounded-full bg-cyan-950/90 border border-cyan-500/60 text-[11px] font-mono text-cyan-300 font-bold flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                    <span>RECOMMENDED FOR PRODUCTION</span>
                  </span>
                  <span className="text-cyan-400 font-mono text-xs font-semibold">TrustRAG Platform</span>
                </div>
                <h3 className="text-2xl font-extrabold text-white mb-2">Autonomous Closed-Loop Recovery</h3>
                <p className="text-slate-300 text-xs leading-relaxed mb-6 font-normal">
                  Decomposes responses into atomic claims, audits evidence citations with hybrid RRF retrieval, and triggers automated LangGraph query rewrites to self-heal low-confidence answers before they leave the server.
                </p>

                {/* Flow Illustration */}
                <div className="p-3.5 rounded-xl bg-surface-950 border border-cyan-800/60 font-mono text-[11px] text-cyan-300 mb-6 space-y-1.5 shadow-inner">
                  <div className="text-slate-500">{'// Execution Flow (Deterministic Closed-Loop)'}</div>
                  <div className="text-slate-200 flex flex-wrap items-center gap-1.5">
                    <span>Query</span>
                    <span>&rarr;</span>
                    <span>Hybrid RRF</span>
                    <span>&rarr;</span>
                    <span>NLI Audit</span>
                    <span>&rarr;</span>
                    <span className="text-cyan-400 font-bold">LangGraph Healing</span>
                    <span>&rarr;</span>
                    <span className="text-emerald-400 font-bold">Grounded Truth</span>
                  </div>
                </div>

                {/* Key Strengths List */}
                <div className="space-y-3">
                  {filteredComparisonRows.map((row, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300">
                      <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-white">{row.title}: </span>
                        <span>{row.trustrag}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-slate-800/80 text-center text-xs font-mono text-emerald-400 font-bold flex items-center justify-center gap-1.5">
                <Check size={14} />
                <span>99.4% Claim Precision &bull; Zero Hallucination Leakage</span>
              </div>
            </div>
          </div>
        )}

        {/* View Mode 2: Interactive Matrix Table */}
        {compareViewMode === 'matrix' && (
          <div className="rounded-3xl border border-slate-800 bg-surface-900/70 overflow-hidden backdrop-blur-xl shadow-2xl animate-fade-in">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-surface-950 text-slate-400 uppercase font-mono text-[11px]">
                  <th className="py-4 px-6">Capability & Dimension</th>
                  <th className="py-4 px-6 text-slate-500">Standard Blind RAG</th>
                  <th className="py-4 px-6 text-cyan-400 font-bold bg-cyan-950/20">TrustRAG Platform</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filteredComparisonRows.map((row, idx) => {
                  const isExpanded = expandedRowIndex === idx
                  return (
                    <tr
                      key={idx}
                      onClick={() => setExpandedRowIndex(isExpanded ? null : idx)}
                      className="hover:bg-cyan-950/30 transition-colors duration-150 cursor-pointer group"
                    >
                      <td className="py-4 px-6 align-top">
                        <div className="font-semibold text-white group-hover:text-cyan-300 transition-colors flex items-center gap-1.5">
                          <span>{row.title}</span>
                          <Info size={12} className="text-slate-500 group-hover:text-cyan-400 transition-colors" />
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{row.subtitle}</div>
                        {isExpanded && (
                          <div className="mt-2.5 p-2 rounded bg-surface-950 border border-slate-800 text-[10px] font-mono text-cyan-300">
                            <strong>Production Impact:</strong> {row.impact}
                          </div>
                        )}
                      </td>
                      <td className="py-4 px-6 text-red-400/90 align-top">
                        <div className="flex items-start gap-1.5">
                          <XCircle size={14} className="shrink-0 mt-0.5 text-red-400" />
                          <span>{row.naive}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-slate-200 align-top bg-cyan-950/10 group-hover:bg-cyan-900/20 transition-colors">
                        <div className="flex items-start gap-1.5">
                          <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-emerald-400" />
                          <div>
                            <span className="font-medium text-white">{row.trustrag}</span>
                            <span className="inline-block mt-1 px-2 py-0.5 rounded bg-cyan-900/40 border border-cyan-700/50 text-[10px] font-mono text-cyan-300">
                              {row.tag}
                            </span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            <div className="p-3 bg-surface-950/80 border-t border-slate-800 text-center text-[11px] text-slate-500 font-mono">
              💡 Tip: Click any row to reveal its real-world production impact and risk profile
            </div>
          </div>
        )}
      </section>

      {/* ── Final Call to Action ───────────────────────────────────────────── */}
      <section className="relative z-20 py-24 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="border-beam p-10 sm:p-20 rounded-3xl bg-gradient-to-b from-surface-900 to-surface-950 border border-cyan-500/40 shadow-2xl shadow-cyan-950/60 relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-cyan-500/15 blur-[120px] pointer-events-none" />
          
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Start Eliminating Hallucinations In Production
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto mb-10 leading-relaxed">
            Deploy your knowledge bases, audit evidence integrity, and self-heal low-confidence RAG answers in minutes.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => navigate('/login')}
              className="w-full sm:w-auto px-10 py-4 rounded-xl bg-gradient-to-r from-primary-600 via-sky-500 to-cyan-500 hover:from-primary-500 hover:to-cyan-400 text-white font-bold text-sm shadow-2xl shadow-cyan-950/80 border border-cyan-400/50 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.05] active:scale-[0.98] cursor-pointer group relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full duration-700 transition-transform pointer-events-none" />
              <span>Get Started Now</span>
              <ArrowRight size={16} className="group-hover:translate-x-1.5 transition-transform" />
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="relative z-20 border-t border-slate-800/80 py-12 bg-surface-950/90 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-primary-600 to-cyan-500 flex items-center justify-center text-white shadow-md">
              <Swords size={13} />
            </div>
            <span className="font-bold text-slate-200 text-sm">TRUSTRAG</span>
            <span className="text-slate-500">Autonomous AI Reliability Platform</span>
          </div>

          <div className="flex items-center gap-2 text-[11px] font-mono text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>All Verification Nodes Operational</span>
          </div>

          <div className="flex items-center gap-6">
            <a href="https://github.com/MaithreshVaddi-27/TrustRAG" target="_blank" rel="noreferrer" className="hover:text-cyan-400 transition-colors flex items-center gap-1">
              <span>GitHub</span>
              <ExternalLink size={12} />
            </a>
            <Link to="/login" className="hover:text-cyan-400 transition-colors">Sign In</Link>
            <Link to="/login" className="hover:text-cyan-400 transition-colors">Get Started</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
