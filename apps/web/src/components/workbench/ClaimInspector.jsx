import { memo, useMemo, useState } from 'react'
import { FileText, Search, Check, ChevronDown, ChevronUp } from 'lucide-react'
import ClaimRow from './ClaimRow'
import { copyToClipboard } from '@/lib/clipboard'

/**
 * ClaimInspector — the proposition ledger.
 *
 * A toolbar that reports the entailment rate and filters the ledger, then
 * the ledger itself: one row per atomic proposition, expandable to its
 * decomposition and citations.
 *
 * Memoized (FE-M3): this subtree re-renders only when the claims array
 * reference changes — not on every parent tick such as an SSE trace update.
 */
const FILTERS = [
  { id: 'ALL', label: 'All' },
  { id: 'SUPPORTED', label: 'Supported' },
  { id: 'CONTRADICTED', label: 'Contradicted' },
  { id: 'NEUTRAL', label: 'Neutral' },
]

export const ClaimInspector = memo(function ClaimInspector({ claims = [] }) {
  const [filter, setFilter] = useState('ALL')
  const [searchTerm, setSearchTerm] = useState('')
  const [allExpanded, setAllExpanded] = useState(false)
  const [copiedId, setCopiedId] = useState(null)

  const stateOf = (claim) =>
    (claim.state || claim.status || claim.verification_status || '').toUpperCase()

  const counts = useMemo(() => {
    let supported = 0
    let contradicted = 0
    let neutral = 0
    claims.forEach((claim) => {
      const state = stateOf(claim)
      if (state === 'SUPPORTED') supported += 1
      else if (state === 'CONTRADICTED') contradicted += 1
      else neutral += 1
    })
    return { all: claims.length, supported, contradicted, neutral }
  }, [claims])

  const filteredClaims = useMemo(
    () =>
      claims.filter((claim) => {
        const state = stateOf(claim)
        if (filter !== 'ALL' && state !== filter) return false
        if (!searchTerm.trim()) return true
        const term = searchTerm.toLowerCase()
        return (
          (claim.text || '').toLowerCase().includes(term) ||
          (claim.explanation || '').toLowerCase().includes(term) ||
          (claim.subject || '').toLowerCase().includes(term)
        )
      }),
    [claims, filter, searchTerm],
  )

  const handleCopy = async (claimText, id) => {
    const ok = await copyToClipboard(claimText)
    if (!ok) return
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1800)
  }

  if (claims.length === 0) {
    return (
      <div className="lx-panel-block">
        <div className="lx-empty">
          <FileText size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
          <p className="lx-empty__title">No atomic claims extracted</p>
          <p className="lx-empty__body">
            The generator may have abstained, or produced an answer without
            discrete, verifiable assertions.
          </p>
        </div>
      </div>
    )
  }

  const entailmentPercent =
    counts.all > 0 ? Math.round((counts.supported / counts.all) * 100) : 0

  return (
    <div className="space-y-4">
      <div className="lx-toolbar">
        <div className="lx-toolbar__group">
          <span className="lx-telemetry__item">
            <strong>Claim entailment faithfulness</strong>
          </span>
          <span
            className={`lx-chip${
              entailmentPercent >= 80 ? '' : entailmentPercent >= 50 ? '' : ' lx-chip--alarm'
            }`}
          >
            {entailmentPercent}%
          </span>
          <span className="lx-micro">
            {counts.supported} of {counts.all} propositions verified against citations
          </span>
        </div>

        <div className="lx-toolbar__group">
          <button
            type="button"
            onClick={() => setAllExpanded((previous) => !previous)}
            className="lx-btn lx-btn--quiet"
            aria-pressed={allExpanded}
          >
            {allExpanded ? (
              <ChevronUp size={13} strokeWidth={1.75} aria-hidden="true" />
            ) : (
              <ChevronDown size={13} strokeWidth={1.75} aria-hidden="true" />
            )}
            <span>{allExpanded ? 'Collapse all' : 'Expand all'}</span>
          </button>
        </div>
      </div>

      <div className="lx-toolbar">
        <div className="lx-tabs" role="group" aria-label="Filter claims by verdict">
          {FILTERS.map((entry) => {
            const count = counts[entry.id.toLowerCase()] ?? 0
            return (
              <button
                key={entry.id}
                type="button"
                onClick={() => setFilter(entry.id)}
                aria-pressed={filter === entry.id}
                className="lx-tab"
              >
                {entry.label}
                <span className="ml-1 font-mono text-[var(--size-micro)] text-silver-500">{count}</span>
              </button>
            )
          })}
        </div>

        <div className="relative w-full max-w-xs">
          <Search
            size={14}
            strokeWidth={1.75}
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-silver-500"
          />
          <input
            id="claims-search-input"
            name="claims-search"
            type="search"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Filter claims or explanations"
            aria-label="Filter claims or explanations"
            className="lx-control pl-9"
          />
        </div>
      </div>

      {filteredClaims.length === 0 ? (
        <div className="lx-panel-block">
          <div className="lx-empty">
            {filter === 'CONTRADICTED' ? (
              <Check size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            ) : (
              <FileText size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            )}
            <p className="lx-empty__title">
              {filter === 'CONTRADICTED'
                ? 'Zero contradicted claims'
                : 'No claims match this filter'}
            </p>
            <p className="lx-empty__body">
              {filter === 'CONTRADICTED'
                ? 'No assertion in this view conflicts with the retrieved evidence. When the entailment model flags one, it appears here with its refuting citations and triggers closed-loop healing.'
                : 'Adjust the search term, or choose a different verdict filter.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-2.5">
          {filteredClaims.map((claim, index) => {
            const key = claim.id ?? index
            return (
              <ClaimRow
                key={key}
                claim={claim}
                index={index + 1}
                isForceExpanded={allExpanded}
                onCopy={() => handleCopy(claim.text, key)}
                isCopied={copiedId === key}
              />
            )
          })}
        </div>
      )}
    </div>
  )
})
