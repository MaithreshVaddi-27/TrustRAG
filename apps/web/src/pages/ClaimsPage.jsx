import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { claimService } from '@/services/api'
import { Brain, Loader2, Search } from 'lucide-react'

export default function ClaimsPage() {
  const [search, setSearch] = useState('')
  const [selectedState, setSelectedState] = useState('ALL')

  const { data: claims = [], isLoading, error } = useQuery({
    queryKey: ['all-claims'],
    queryFn: claimService.list,
  })

  const states = ['ALL', 'SUPPORTED', 'CONTRADICTED', 'NEUTRAL']

  const stateCounts = claims.reduce((acc, c) => {
    acc[c.state] = (acc[c.state] || 0) + 1
    return acc
  }, {})

  const filteredClaims = claims.filter((claim) => {
    const matchesSearch =
      !search.trim() ||
      claim.text?.toLowerCase().includes(search.toLowerCase()) ||
      claim.explanation?.toLowerCase().includes(search.toLowerCase())
    const matchesState = selectedState === 'ALL' || claim.state === selectedState
    return matchesSearch && matchesState
  })

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">Claims</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary-950/80 text-primary-400 border border-primary-800/60">
                {claims.length} {claims.length === 1 ? 'Claim' : 'Claims'}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Atomic assertions decomposed from model answers with Natural Language Inference (NLI) verification.
            </p>
          </div>
        </div>

        {/* State tabs */}
        <div className="glass-card p-2 flex flex-wrap gap-2 items-center">
          {states.map((st) => {
            const count = st === 'ALL' ? claims.length : stateCounts[st] || 0
            const active = selectedState === st
            return (
              <button
                key={st}
                onClick={() => setSelectedState(st)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
                  active
                    ? 'bg-primary-600 text-white shadow-sm shadow-primary-900/50'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800'
                }`}
              >
                <span>{st}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    active ? 'bg-primary-700/80 text-white' : 'bg-surface-800 text-slate-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            )
          })}
        </div>

        {/* Search bar */}
        <div className="glass-card p-3 flex items-center gap-3">
          <Search size={16} className="text-slate-500 shrink-0 ml-1" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search claims or verification explanations..."
            className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors mr-1"
            >
              Clear
            </button>
          )}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-3">
            <Loader2 size={24} className="animate-spin text-primary-400" />
            <span className="text-sm text-slate-400">Loading verified claim records...</span>
          </div>
        ) : error ? (
          <div className="glass-card p-6 text-center text-red-400 border border-red-800/40">
            Failed to load claims: {error.message || 'An unexpected error occurred'}
          </div>
        ) : filteredClaims.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-500 space-y-2">
            <Brain size={32} className="mx-auto text-slate-600 mb-2" />
            <p className="font-medium text-slate-300">No claims matching filters</p>
            <p className="text-xs text-slate-500">
              {claims.length === 0
                ? 'Run an analysis in the Playground to generate and verify assertions.'
                : 'Try adjusting your search or state filter.'}
            </p>
          </div>
        ) : (
          <div className="glass-card p-4 space-y-3">
            <ClaimInspector claims={filteredClaims} />
          </div>
        )}
      </div>
    </AppLayout>
  )
}
