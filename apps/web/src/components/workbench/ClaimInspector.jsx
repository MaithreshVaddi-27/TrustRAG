import { clsx } from 'clsx'
import { ChevronDown, ChevronRight, FileText, Quote, Check, Copy, Sparkles } from 'lucide-react'
import { useState, useMemo } from 'react'
import { ClaimStateBadge } from './ReliabilityBadge'

/**
 * ClaimInspector — Ultra-refined expandable claim inspector with filter tabs,
 * triple decomposition chips, citation references, and one-click copy.
 */
export function ClaimInspector({ claims = [] }) {
  const [filter, setFilter] = useState('ALL')
  const [allExpanded, setAllExpanded] = useState(false)
  const [copiedId, setCopiedId] = useState(null)

  const counts = useMemo(() => {
    let supported = 0, contradicted = 0, neutral = 0
    claims.forEach(c => {
      const s = (c.state || c.status || c.verification_status || '').toUpperCase()
      if (s === 'SUPPORTED') supported++
      else if (s === 'CONTRADICTED') contradicted++
      else neutral++
    })
    return { all: claims.length, supported, contradicted, neutral }
  }, [claims])

  const filteredClaims = useMemo(() => {
    if (filter === 'ALL') return claims
    return claims.filter(c => {
      const s = (c.state || c.status || c.verification_status || '').toUpperCase()
      return s === filter
    })
  }, [claims, filter])

  const handleCopy = (claimText, id) => {
    navigator.clipboard.writeText(claimText)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1800)
  }

  if (claims.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500 border border-slate-800 rounded-2xl bg-surface-900/40">
        <FileText size={24} className="text-slate-600 mb-2" />
        <p className="text-sm font-medium text-slate-300">No Atomic Claims Extracted</p>
        <p className="text-xs text-slate-500 mt-1 max-w-sm">
          The generator may have abstained or formulated an answer without discrete verifiable factual assertions.
        </p>
      </div>
    )
  }

  const entailmentPercent = counts.all > 0 ? Math.round((counts.supported / counts.all) * 100) : 0

  return (
    <div className="space-y-4">
      {/* Top Header Summary & Action Bar */}
      <div className="p-3.5 rounded-xl border border-slate-800 bg-surface-900/60 backdrop-blur-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-700/50 text-cyan-400 shrink-0">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200">Claim Entailment Faithfulness</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                entailmentPercent >= 80 ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40' :
                entailmentPercent >= 50 ? 'bg-amber-950/80 text-amber-300 border border-amber-800/40' :
                'bg-red-950/80 text-red-300 border border-red-800/40'
              }`}>
                {entailmentPercent}%
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {counts.supported} of {counts.all} atomic propositions verified against citations
            </p>
          </div>
        </div>

        {/* Filter Pills & Expand Toggle */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`px-2 py-1 rounded-lg text-[11px] font-medium transition-all ${
              filter === 'ALL' ? 'bg-primary-600/40 text-primary-200 border border-primary-500/50 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({counts.all})
          </button>
          <button
            type="button"
            onClick={() => setFilter('SUPPORTED')}
            className={`px-2 py-1 rounded-lg text-[11px] font-medium transition-all ${
              filter === 'SUPPORTED' ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Supported ({counts.supported})
          </button>
          {counts.contradicted > 0 && (
            <button
              type="button"
              onClick={() => setFilter('CONTRADICTED')}
              className={`px-2 py-1 rounded-lg text-[11px] font-medium transition-all ${
                filter === 'CONTRADICTED' ? 'bg-red-950/80 text-red-300 border border-red-700/60 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Contradicted ({counts.contradicted})
            </button>
          )}
          <button
            type="button"
            onClick={() => setFilter('NEUTRAL')}
            className={`px-2 py-1 rounded-lg text-[11px] font-medium transition-all ${
              filter === 'NEUTRAL' ? 'bg-amber-950/80 text-amber-300 border border-amber-700/60 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Neutral ({counts.neutral})
          </button>

          <div className="h-4 w-px bg-slate-800 mx-1 hidden sm:block" />

          <button
            type="button"
            onClick={() => setAllExpanded(v => !v)}
            className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded bg-surface-950/80 border border-slate-800 hover:border-slate-700 transition-colors"
          >
            {allExpanded ? 'Collapse All' : 'Expand All'}
          </button>
        </div>
      </div>

      {/* Claim Rows List */}
      <div className="space-y-2.5">
        {filteredClaims.map((claim, i) => (
          <ClaimRow
            key={claim.id ?? i}
            claim={claim}
            index={i + 1}
            isForceExpanded={allExpanded}
            onCopy={() => handleCopy(claim.text, claim.id ?? i)}
            isCopied={copiedId === (claim.id ?? i)}
          />
        ))}
      </div>
    </div>
  )
}

function ClaimRow({ claim, index, isForceExpanded, onCopy, isCopied }) {
  const [open, setOpen] = useState(false)
  const isExpanded = isForceExpanded || open
  const claimState = (claim.state || claim.status || claim.verification_status || '').toUpperCase()

  return (
    <div className={clsx(
      'rounded-xl border transition-all duration-200 shadow-sm overflow-hidden',
      claimState === 'SUPPORTED'    && 'neon-verdict-supported',
      claimState === 'CONTRADICTED' && 'neon-verdict-contradicted',
      claimState === 'NEUTRAL'      && 'neon-verdict-neutral',
      !claimState                   && 'border-slate-800 bg-surface-900/60',
    )}>
      <div className="w-full flex items-start gap-3 p-3.5 text-left hover:bg-white/[0.02] transition-colors">
        <span className="text-slate-500 text-xs font-mono font-bold mt-0.5 min-w-[1.75rem] text-right shrink-0">
          C{index}
        </span>
        <div className="flex-1 min-w-0 pr-2 cursor-pointer" onClick={() => setOpen(o => !o)}>
          <p className="text-sm text-slate-100 break-words leading-relaxed font-normal">{claim.text}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <ClaimStateBadge state={claimState} />
          <button
            type="button"
            onClick={onCopy}
            className="text-slate-500 hover:text-slate-300 p-1 rounded hover:bg-surface-800 transition-colors"
            title="Copy claim assertion"
          >
            {isCopied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
          </button>
          <button
            type="button"
            onClick={() => setOpen(o => !o)}
            className="text-slate-500 hover:text-slate-300 p-1 rounded hover:bg-surface-800 transition-colors"
            aria-label={isExpanded ? "Collapse claim details" : "Expand claim details"}
          >
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 pb-3.5 pt-1 space-y-2.5 border-t border-slate-800/60 bg-surface-950/30 animate-fade-in">
          {/* Proposition Triple */}
          {(claim.subject || claim.predicate || claim.object) && (
            <div className="flex items-center gap-1.5 text-xs text-slate-300 bg-surface-900/80 border border-slate-800/90 rounded-lg px-3 py-2 font-mono overflow-x-auto shadow-inner">
              <span className="text-slate-400 font-sans text-[11px] font-semibold mr-1 shrink-0">SPO Triple:</span>
              <span className="text-primary-300 bg-primary-950/50 px-1.5 py-0.5 rounded border border-primary-800/40 font-semibold">{claim.subject || '—'}</span>
              <span className="text-slate-500">→</span>
              <span className="text-amber-300 bg-amber-950/50 px-1.5 py-0.5 rounded border border-amber-800/40 font-semibold">{claim.predicate || '—'}</span>
              <span className="text-slate-500">→</span>
              <span className="text-cyan-300 bg-cyan-950/50 px-1.5 py-0.5 rounded border border-cyan-800/40 font-semibold">{claim.object || '—'}</span>
            </div>
          )}

          {/* Explanation */}
          {claim.explanation && (
            <div className="flex gap-2 text-xs text-slate-300 bg-surface-900/60 border border-slate-800/60 rounded-lg p-2.5">
              <Quote size={13} className="shrink-0 mt-0.5 text-cyan-400" />
              <span className="break-words leading-relaxed font-sans">{claim.explanation}</span>
            </div>
          )}

          {/* Evidence Citations Links */}
          {claim.evidence_ids?.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-slate-400 pt-0.5">
              <span className="text-slate-500 font-medium">Supporting Citations:</span>
              <div className="flex flex-wrap gap-1">
                {claim.evidence_ids.map(id => (
                  <span
                    key={id}
                    className="inline-flex items-center px-1.5 py-0.5 rounded bg-surface-850 border border-slate-700/80 text-primary-300 font-mono text-[10px]"
                  >
                    #{String(id).slice(-6)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
