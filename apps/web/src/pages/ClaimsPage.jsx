import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { claimService } from '@/services/api'
import { Brain } from 'lucide-react'
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
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">Claims</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
                {claims.length} {claims.length === 1 ? 'Claim' : 'Claims'}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Atomic assertions decomposed from model answers with Natural Language Inference (NLI) verification.
            </p>
          </div>
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
          <div className="glass-card p-12 text-center text-slate-500 space-y-2">
            <Brain size={32} className="mx-auto text-slate-600 mb-2" />
            <p className="font-medium text-slate-300">No claims extracted yet</p>
            <p className="text-xs text-slate-500">
              Run an analysis in the Playground to generate and verify propositional assertions.
            </p>
          </div>
        ) : (
          <ClaimInspector claims={claims} />
        )}
      </div>
    </AppLayout>
  )
}
