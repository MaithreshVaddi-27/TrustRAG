import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { evidenceService } from '@/services/api'
import { FileSearch } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

export default function EvidencePage() {
  const { data: evidence = [], isLoading, error } = useQuery({
    queryKey: ['all-evidence'],
    queryFn: evidenceService.list,
  })

  return (
    <AppLayout>
      <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6 animate-fade-in stagger-children">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">Evidence</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
                {evidence.length} {evidence.length === 1 ? 'Record' : 'Records'}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Retrieved evidence chunks across all analyses, with provenance, score breakdown, and integrity audits.
            </p>
          </div>
        </div>

        {/* Body */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-4">
            <ThinkingOrbs size="md" />
            <span className="text-sm text-slate-400">Loading retrieved evidence records...</span>
          </div>
        ) : error ? (
          <div className="glass-card p-6 text-center text-red-400 border border-red-800/40">
            Failed to load evidence: {error.message || 'An unexpected error occurred'}
          </div>
        ) : evidence.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-500 space-y-2">
            <FileSearch size={32} className="mx-auto text-slate-600 mb-2" />
            <p className="font-medium text-slate-300">No evidence segments retrieved</p>
            <p className="text-xs text-slate-500">
              Run an analysis in the Playground to retrieve and persist evidence chunks.
            </p>
          </div>
        ) : (
          <EvidenceViewer chunks={evidence} />
        )}
      </div>
    </AppLayout>
  )
}
