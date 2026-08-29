import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { evidenceService } from '@/services/api'
import { FileSearch, Loader2, Search, Filter } from 'lucide-react'

export default function EvidencePage() {
  const [search, setSearch] = useState('')
  const [filterMethod, setFilterMethod] = useState('all')

  const { data: evidence = [], isLoading, error } = useQuery({
    queryKey: ['all-evidence'],
    queryFn: evidenceService.list,
  })

  const filteredEvidence = evidence.filter((item) => {
    const matchesSearch =
      !search.trim() ||
      item.text?.toLowerCase().includes(search.toLowerCase()) ||
      item.filename?.toLowerCase().includes(search.toLowerCase())
    const matchesMethod =
      filterMethod === 'all' || item.method?.toLowerCase() === filterMethod.toLowerCase()
    return matchesSearch && matchesMethod
  })

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">Evidence</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary-950/80 text-primary-400 border border-primary-800/60">
                {evidence.length} {evidence.length === 1 ? 'Record' : 'Records'}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Retrieved evidence chunks across all analyses, with provenance, score breakdown, and integrity audits.
            </p>
          </div>
        </div>

        {/* Filter bar */}
        <div className="glass-card p-3.5 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="relative w-full sm:w-80">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by snippet or source filename..."
              className="w-full bg-surface-800/80 border border-slate-700/80 rounded-lg pl-9 pr-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/40 transition-colors"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter size={14} className="text-slate-500 shrink-0" />
            <select
              value={filterMethod}
              onChange={(e) => setFilterMethod(e.target.value)}
              className="bg-surface-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="all">All Methods</option>
              <option value="hybrid">Hybrid (Dense + Sparse)</option>
              <option value="dense">Dense Only</option>
              <option value="sparse">Sparse Only</option>
            </select>
          </div>
        </div>

        {/* Body */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <Loader2 size={24} className="animate-spin text-primary-400" />
            <span className="text-sm text-slate-400">Loading retrieved evidence records...</span>
          </div>
        ) : error ? (
          <div className="glass-card p-6 text-center text-red-400 border border-red-800/40">
            Failed to load evidence: {error.message || 'An unexpected error occurred'}
          </div>
        ) : filteredEvidence.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-500 space-y-2">
            <FileSearch size={32} className="mx-auto text-slate-600 mb-2" />
            <p className="font-medium text-slate-300">No evidence matching filters</p>
            <p className="text-xs text-slate-500">
              {evidence.length === 0
                ? 'Run an analysis in the Playground to retrieve and persist evidence chunks.'
                : 'Try adjusting your search query or method filter.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <EvidenceViewer chunks={filteredEvidence} />
          </div>
        )}
      </div>
    </AppLayout>
  )
}
