import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import AppLayout from '@/layouts/AppLayout'
import { conflictService } from '@/services/api'
import { AlertTriangle, ShieldAlert, CheckCircle, ArrowRight, ShieldCheck, Scale, RefreshCw } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

export default function ConflictsPage() {
  const { data: conflicts = [], isLoading, error } = useQuery({
    queryKey: ['all-conflicts'],
    queryFn: conflictService.list,
  })

  return (
    <AppLayout>
      <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6 animate-fade-in stagger-children">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-mono bg-amber-950/80 text-amber-300 border border-amber-800/60 shadow-sm">
              <ShieldAlert size={12} />
              <span>Contradiction Engine</span>
            </div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Source & Claim <span className="text-amber-400">Conflicts</span>
              </h1>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border font-mono ${
                conflicts.length > 0
                  ? 'bg-amber-950/80 text-amber-400 border-amber-800/60'
                  : 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'
              }`}>
                {conflicts.length} {conflicts.length === 1 ? 'Conflict' : 'Conflicts'}
              </span>
            </div>
            <p className="text-slate-400 text-sm">
              Detected evidence contradictions and integrity flags across document versions and queries.
            </p>
          </div>

          <Link
            to="/playground"
            className="self-start sm:self-auto inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-md shadow-primary-950/50 transition-all cursor-pointer"
          >
            <span>Run New Query</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        {/* Informational Banner */}
        <div className="glass-card p-5 flex items-start gap-3.5 border-amber-800/40 bg-amber-950/15">
          <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-semibold text-amber-300">Deterministic Conflict Detection</p>
            <p className="text-xs text-slate-300 leading-relaxed">
              When documents contain opposing assertions or when NLI verification detects a direct contradiction
              against source evidence, TrustRAG isolates and surfaces the conflict rather than making an arbitrary or hallucinated choice.
            </p>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-4">
            <ThinkingOrbs size="md" />
            <span className="text-sm text-slate-400">Auditing source conflicts...</span>
          </div>
        ) : error ? (
          <div className="glass-card p-6 text-center text-red-400 border border-red-800/40">
            Failed to load conflicts: {error.message || 'An unexpected error occurred'}
          </div>
        ) : conflicts.length === 0 ? (
          <div className="space-y-6">
            <div className="glass-card p-10 sm:p-14 text-center space-y-4 border-slate-800">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto text-emerald-400 shadow-inner">
                <CheckCircle size={28} />
              </div>
              <div className="space-y-1.5 max-w-md mx-auto">
                <h3 className="text-base font-semibold text-white tracking-tight">No active conflicts detected</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  All processed evidence and claims across your active analyses are coherent and free of contradictory assertions or integrity violations.
                </p>
              </div>
              <div className="pt-2">
                <Link
                  to="/playground"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-800 hover:bg-surface-750 border border-slate-700 text-slate-200 text-xs font-semibold shadow-sm transition-all cursor-pointer"
                >
                  <RefreshCw size={12} className="text-emerald-400" />
                  <span>Test Adversarial Prompts in Playground</span>
                  <ArrowRight size={12} />
                </Link>
              </div>
            </div>

            {/* Conflict Resolution Architecture Explainer */}
            <div className="p-5 rounded-2xl bg-surface-900/60 border border-slate-800/80 space-y-3.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                <Scale size={14} className="text-amber-400" />
                <span>Conflict Resolution & Self-Healing Protocol</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-amber-300">
                    <ShieldAlert size={13} />
                    <span>Cross-Document Divergence</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Identifies semantic conflicts between distinct files within the same knowledge base partition, preventing synthesis from silently hallucinating a synthesis.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-cyan-300">
                    <ShieldCheck size={13} />
                    <span>Entailment Refutation Guard</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    NLI refutation scores exceeding 0.70 automatically trigger query reformulation, retrieving corroborating citations to resolve factual ambiguities.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {conflicts.map((conflict) => (
              <div
                key={conflict.id}
                className="glass-card p-5 space-y-3 border-amber-900/40 hover:border-amber-700/60 transition-colors"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <ShieldAlert size={16} className="text-amber-400 shrink-0" />
                    <span className="text-sm font-semibold text-slate-200">{conflict.title}</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400 shrink-0">
                    {conflict.type}
                  </span>
                </div>

                <blockquote className="border-l-2 border-amber-500/60 pl-3 text-sm text-slate-300 leading-relaxed font-sans">
                  {conflict.claim}
                </blockquote>

                <div className="bg-surface-800/50 rounded-lg p-2.5 text-xs text-slate-400 space-y-1">
                  <p className="font-medium text-slate-300">Explanation:</p>
                  <p>{conflict.explanation}</p>
                </div>

                {conflict.query && (
                  <div className="text-[11px] text-slate-500 flex items-center gap-1.5 font-mono">
                    <span className="text-slate-400 font-sans font-medium">Query:</span> {conflict.query}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}

