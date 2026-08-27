import { BarChart3, Brain, Database, FileSearch, GitMerge, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import AppLayout from '@/layouts/AppLayout'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'

// Static summary cards — wired to real data in Phase 3+
const STAT_CARDS = [
  { label: 'Knowledge Bases', value: '—', icon: Database,    to: '/knowledge-bases', color: 'text-primary-400' },
  { label: 'Analyses Run',    value: '—', icon: Zap,         to: '/playground',      color: 'text-indigo-400' },
  { label: 'Claims Verified', value: '—', icon: Brain,       to: '/claims',          color: 'text-blue-400'   },
  { label: 'Conflicts Found', value: '—', icon: GitMerge,    to: '/conflicts',       color: 'text-amber-400'  },
]

// Pipeline steps — shows the TRUSTRAG flow to new users
const PIPELINE = [
  { step: 'Query',             desc: 'Submit a question to your knowledge base' },
  { step: 'Retrieve',          desc: 'Hybrid dense + sparse BM25 retrieval with RRF fusion' },
  { step: 'Rerank',            desc: 'Optional cross-encoder reranking' },
  { step: 'Generate',          desc: 'Gemini-backed answer grounded in evidence' },
  { step: 'Decompose Claims',  desc: 'Break answer into individually verifiable claims' },
  { step: 'Verify Claims',     desc: 'Match each claim against evidence' },
  { step: 'Integrity Analysis',desc: 'Check provenance, temporal validity, conflicts' },
  { step: 'Diagnose',          desc: 'Identify specific failure types' },
  { step: 'Recover',           desc: 'Apply targeted recovery strategies' },
  { step: 'Grounded Answer',   desc: 'Final answer with reliability score or abstention' },
]

export default function DashboardPage() {
  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">
            AI Reliability Workbench — Retrieve, Verify, Diagnose, Recover
          </p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_CARDS.map(({ label, value, icon: Icon, to, color }) => (
            <Link
              key={label}
              to={to}
              className="glass-card p-4 hover:border-slate-600/60 transition-colors group"
            >
              <div className="flex items-center justify-between mb-3">
                <Icon size={18} className={color} />
              </div>
              <p className="text-2xl font-bold text-white">{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </Link>
          ))}
        </div>

        {/* Quick action */}
        <div className="glass-card p-5 flex items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-white">Ready to analyze?</p>
            <p className="text-sm text-slate-400 mt-0.5">
              Upload documents to a knowledge base, then open the Playground.
            </p>
          </div>
          <div className="flex gap-3 shrink-0">
            <Link to="/knowledge-bases" className="btn-secondary">
              Manage KBs
            </Link>
            <Link to="/playground" className="btn-primary flex items-center gap-1.5">
              <Zap size={14} /> Playground
            </Link>
          </div>
        </div>

        {/* Reliability pipeline diagram */}
        <div>
          <p className="section-heading">The TRUSTRAG Pipeline</p>
          <div className="glass-card overflow-hidden">
            {PIPELINE.map(({ step, desc }, i) => (
              <div
                key={step}
                className="flex items-start gap-4 px-5 py-3 border-b border-slate-800/50 last:border-0 hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex flex-col items-center shrink-0 pt-0.5">
                  <div className="w-6 h-6 rounded-full bg-primary-600/20 border border-primary-700/50 flex items-center justify-center text-xs font-bold text-primary-400">
                    {i + 1}
                  </div>
                  {i < PIPELINE.length - 1 && (
                    <div className="w-px h-4 bg-slate-800 mt-1" />
                  )}
                </div>
                <div className="pt-0.5">
                  <p className="text-sm font-medium text-slate-200">{step}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Example reliability badge states */}
        <div>
          <p className="section-heading">Reliability Score Bands</p>
          <div className="glass-card p-4 flex flex-wrap gap-3">
            <ReliabilityBadge score={0.91} status="TRUSTED"   size="md" />
            <ReliabilityBadge score={0.62} status="UNCERTAIN" size="md" />
            <ReliabilityBadge score={0.34} status="ABSTAINED" size="md" />
            <ReliabilityBadge score={null} status={undefined} size="md" />
          </div>
          <p className="text-xs text-slate-600 mt-2">
            Scores are heuristic composites — not calibrated probabilities. See docs/evaluation/methodology.md.
          </p>
        </div>
      </div>
    </AppLayout>
  )
}
