import AppLayout from '@/layouts/AppLayout'
import { GitMerge, AlertTriangle } from 'lucide-react'

export default function ConflictsPage() {
  return (
    <AppLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Source Conflicts</h1>
          <p className="text-slate-400 text-sm mt-1">Detected evidence conflicts across document versions</p>
        </div>

        <div className="glass-card p-4 flex items-start gap-3 border-amber-800/30 bg-amber-950/10">
          <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-300">Conflict Detection</p>
            <p className="text-xs text-slate-400 mt-1">
              When multiple document versions provide conflicting evidence (e.g., Policy v3 → 30 days vs Policy v4 → 45 days),
              TRUSTRAG flags the conflict and exposes it rather than making an arbitrary choice.
            </p>
          </div>
        </div>

        <div className="glass-card p-12 text-center text-slate-500">
          <GitMerge size={28} className="mx-auto mb-3 text-slate-600" />
          <p className="font-medium text-slate-400">No conflicts detected</p>
          <p className="text-sm mt-1">Conflicts are surfaced during evidence integrity analysis.</p>
        </div>
      </div>
    </AppLayout>
  )
}
