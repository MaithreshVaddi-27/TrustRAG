import AppLayout from '@/layouts/AppLayout'
import { ClaimStateBadge } from '@/components/workbench/ReliabilityBadge'
import { Brain } from 'lucide-react'

export default function ClaimsPage() {
  const STATES = ['SUPPORTED', 'CONTRADICTED', 'UNSUPPORTED', 'UNKNOWN']
  return (
    <AppLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Claims</h1>
          <p className="text-slate-400 text-sm mt-1">Claim-level verification across all analyses</p>
        </div>

        {/* State legend */}
        <div className="glass-card p-4 flex flex-wrap gap-3 items-center">
          <p className="section-heading mb-0 mr-2">States:</p>
          {STATES.map(s => <ClaimStateBadge key={s} state={s} />)}
        </div>

        <div className="glass-card p-12 text-center text-slate-500">
          <Brain size={28} className="mx-auto mb-3 text-slate-600" />
          <p className="font-medium text-slate-400">No claims yet</p>
          <p className="text-sm mt-1">Run an analysis in the Playground to generate claims.</p>
        </div>
      </div>
    </AppLayout>
  )
}
