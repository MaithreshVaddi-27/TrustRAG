import { Brain, Database, GitMerge, Zap, ArrowRight, Clock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'
import { kbService, analysisService, claimService, conflictService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'

const PIPELINE = [
  { step: 'Query', desc: 'Submit a question to your knowledge base' },
  { step: 'Retrieve', desc: 'Hybrid dense + sparse BM25 retrieval with RRF fusion' },
  { step: 'Rerank', desc: 'Optional cross-encoder reranking' },
  { step: 'Generate', desc: 'Gemini-backed answer grounded in evidence' },
  { step: 'Decompose Claims', desc: 'Break answer into individually verifiable claims' },
  { step: 'Verify Claims', desc: 'Match each claim against evidence' },
  { step: 'Integrity Analysis', desc: 'Check provenance, temporal validity, conflicts' },
  { step: 'Diagnose', desc: 'Identify specific failure types' },
  { step: 'Recover', desc: 'Apply targeted recovery strategies' },
  { step: 'Grounded Answer', desc: 'Final answer with reliability score or abstention' },
]

export default function DashboardPage() {
  const { data: kbs = [] } = useQuery({ queryKey: ['knowledgeBases'], queryFn: kbService.list })
  const { data: analyses = [] } = useQuery({ queryKey: ['analyses'], queryFn: analysisService.list })
  const { data: claims = [] } = useQuery({ queryKey: ['all-claims'], queryFn: claimService.list })
  const { data: conflicts = [] } = useQuery({ queryKey: ['all-conflicts'], queryFn: conflictService.list })

  const statCards = [
    { label: 'Knowledge Bases', value: kbs.length, icon: Database, to: '/knowledge-bases', color: 'text-primary-400' },
    { label: 'Analyses Run', value: analyses.length, icon: Zap, to: '/playground', color: 'text-indigo-400' },
    { label: 'Claims Verified', value: claims.length, icon: Brain, to: '/claims', color: 'text-blue-400' },
    { label: 'Conflicts Found', value: conflicts.length, icon: GitMerge, to: '/conflicts', color: 'text-amber-400' },
  ]

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto space-y-8 animate-fade-in">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">
            AI Reliability Workbench — Retrieve, Verify, Diagnose, Recover
          </p>
        </div>

        {/* Live Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map(({ label, value, icon: Icon, to, color }) => (
            <Link
              key={label}
              to={to}
              className="glass-card p-4 hover:border-slate-600/60 transition-all hover:translate-y-[-1px] group"
            >
              <div className="flex items-center justify-between mb-3">
                <Icon size={18} className={color} />
                <ArrowRight size={13} className="text-slate-600 group-hover:text-slate-400 transition-colors" />
              </div>
              <p className="text-2xl font-bold text-white tracking-tight">{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </Link>
          ))}
        </div>

        {/* Quick action */}
        <div className="glass-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-white">Ready to analyze?</p>
            <p className="text-sm text-slate-400 mt-0.5">
              Select or upload documents to your knowledge base, then run grounded queries in the Playground.
            </p>
          </div>
          <div className="flex gap-3 shrink-0">
            <Link to="/knowledge-bases" className="btn-secondary text-sm">
              Manage KBs
            </Link>
            <Link to="/playground" className="btn-primary text-sm flex items-center gap-1.5">
              <Zap size={14} /> Playground
            </Link>
          </div>
        </div>

        {/* Recent Analyses Runs */}
        {analyses.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="section-heading mb-0">Recent Analysis Runs</p>
              <Link to="/playground" className="text-xs text-primary-400 hover:text-primary-300 transition-colors">
                Open Playground →
              </Link>
            </div>
            <div className="glass-card divide-y divide-slate-800/60 overflow-hidden">
              {analyses.slice(0, 5).map((a) => (
                <div key={a.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-white/[0.02] transition-colors">
                  <div className="space-y-1 min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-200 truncate">{a.query}</p>
                    <p className="text-xs text-slate-400 line-clamp-1">
                      {a.answer || (a.status === 'abstained' ? 'Agent abstained from answering.' : 'Analysis in progress...')}
                    </p>
                    <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono pt-1">
                      <span className="flex items-center gap-1">
                        <Clock size={11} /> {formatDistanceToNow(new Date(a.created_at))} ago
                      </span>
                    </div>
                  </div>
                  <div className="shrink-0 flex items-center gap-2">
                    <ReliabilityBadge score={a.reliability?.score} status={a.reliability?.status} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

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
                  {i < PIPELINE.length - 1 && <div className="w-px h-4 bg-slate-800 mt-1" />}
                </div>
                <div className="pt-0.5">
                  <p className="text-sm font-medium text-slate-200">{step}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
