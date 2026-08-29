import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { conflictService } from '@/services/api'
import { AlertTriangle, GitMerge, Loader2, ShieldAlert, CheckCircle } from 'lucide-react'

export default function ConflictsPage() {
  const { data: conflicts = [], isLoading, error } = useQuery({
    queryKey: ['all-conflicts'],
    queryFn: conflictService.list,
  })

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">Source & Claim Conflicts</h1>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                conflicts.length > 0
                  ? 'bg-amber-950/80 text-amber-400 border-amber-800/60'
                  : 'bg-green-950/80 text-green-400 border-green-800/60'
              }`}>
                {conflicts.length} {conflicts.length === 1 ? 'Conflict' : 'Conflicts'}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Detected evidence contradictions and integrity flags across document versions and queries.
            </p>
          </div>
        </div>

        {/* Informational Banner */}
        <div className="glass-card p-4 flex items-start gap-3.5 border-amber-800/40 bg-amber-950/15">
          <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-semibold text-amber-300">Deterministic Conflict Detection</p>
            <p className="text-xs text-slate-300 leading-relaxed">
              When documents contain opposing assertions or when NLI verification detects a direct contradiction
              against source evidence, TRUSTRAG isolates and surfaces the conflict rather than making an arbitrary or hallucinated choice.
            </p>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <Loader2 size={24} className="animate-spin text-primary-400" />
            <span className="text-sm text-slate-400">Auditing source conflicts...</span>
          </div>
        ) : error ? (
          <div className="glass-card p-6 text-center text-red-400 border border-red-800/40">
            Failed to load conflicts: {error.message || 'An unexpected error occurred'}
          </div>
        ) : conflicts.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-500 space-y-3">
            <div className="w-12 h-12 rounded-full bg-green-950/40 border border-green-800/40 flex items-center justify-center mx-auto text-green-400">
              <CheckCircle size={22} />
            </div>
            <p className="font-semibold text-slate-200">No active conflicts detected</p>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              All processed evidence and claims across your active analyses are coherent and free of contradictory assertions or integrity violations.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {conflicts.map((conflict) => (
              <div
                key={conflict.id}
                className="glass-card p-4 space-y-3 border-amber-900/40 hover:border-amber-700/60 transition-colors"
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
