import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import AppLayout from '@/layouts/AppLayout'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { claimService } from '@/services/api'
import { Brain, ArrowRight, ShieldCheck, AlertCircle, HelpCircle, Layers } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

export default function ClaimsPage() {
  const { data: claims = [], isLoading, error } = useQuery({
    queryKey: ['all-claims'],
    queryFn: claimService.list,
  })

  return (
    <AppLayout>
      <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6 animate-fade-in stagger-children">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-mono bg-primary-950/80 text-primary-300 border border-primary-800/60 shadow-sm">
              <Brain size={12} />
              <span>Factual Assertion Inspector</span>
            </div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Atomic <span className="text-primary-400">Claims</span>
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary-950/80 text-primary-400 border border-primary-800/60 font-mono">
                {claims.length} {claims.length === 1 ? 'Claim' : 'Claims'}
              </span>
            </div>
            <p className="text-slate-400 text-sm">
              Atomic assertions decomposed from model answers with Natural Language Inference (NLI) verification.
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

        {/* Content */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-4">
            <ThinkingOrbs size="md" />
            <span className="text-sm text-slate-400">Loading verified claim records...</span>
          </div>
        ) : error ? (
          <div className="glass-card p-6 text-center text-red-400 border border-red-800/40">
            Failed to load claims: {error.message || 'An unexpected error occurred'}
          </div>
        ) : claims.length === 0 ? (
          <div className="space-y-6">
            <div className="glass-card p-10 sm:p-14 text-center space-y-5 border-slate-800">
              <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/30 flex items-center justify-center mx-auto text-primary-400 shadow-inner">
                <Brain size={28} />
              </div>
              <div className="space-y-1.5 max-w-md mx-auto">
                <h3 className="text-base font-semibold text-white tracking-tight">No claims extracted yet</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Execute an analysis in the Playground to decompose generated responses into atomic subject-predicate-object propositions and run NLI verification.
                </p>
              </div>
              <div>
                <Link
                  to="/playground"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shadow-md shadow-primary-950/60 transition-all cursor-pointer"
                >
                  <span>Decompose Claims in Playground</span>
                  <ArrowRight size={13} />
                </Link>
              </div>
            </div>

            {/* NLI Verification Classes Explainer */}
            <div className="p-5 rounded-2xl bg-surface-900/60 border border-slate-800/80 space-y-3.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                <Layers size={14} className="text-primary-400" />
                <span>Deterministic Natural Language Inference (NLI) Classifications</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-emerald-900/30 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                    <ShieldCheck size={13} />
                    <span>Supported (Entailment)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Proposition is explicitly substantiated by cited evidence spans with confidence ≥ 0.70.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-red-900/30 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-red-400">
                    <AlertCircle size={13} />
                    <span>Contradicted (Refutation)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Assertion directly conflicts with grounded evidence. Triggers automatic healing loop.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-amber-900/30 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-amber-400">
                    <HelpCircle size={13} />
                    <span>Neutral (Unverified)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Neither confirmed nor refuted by evidence. Treated as ungrounded extrapolation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <ClaimInspector claims={claims} />
        )}
      </div>
    </AppLayout>
  )
}
