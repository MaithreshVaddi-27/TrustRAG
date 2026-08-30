import { clsx } from 'clsx'
import { ChevronDown, ChevronRight, FileText, Quote } from 'lucide-react'
import { useState } from 'react'
import { ClaimStateBadge } from './ReliabilityBadge'

/**
 * ClaimInspector — expandable claim list with evidence links.
 * Props:
 *   claims: [{ id, text, state, evidence_ids, explanation }]
 */
export function ClaimInspector({ claims = [] }) {
  if (claims.length === 0) {
    return (
      <div className="flex items-center gap-2 text-slate-500 text-sm py-4">
        <FileText size={16} /> No claims extracted.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {claims.map((claim, i) => (
        <ClaimRow key={claim.id ?? i} claim={claim} index={i + 1} />
      ))}
    </div>
  )
}

function ClaimRow({ claim, index }) {
  const [open, setOpen] = useState(false)
  const claimState = (claim.state || claim.status || claim.verification_status || '').toUpperCase()

  return (
    <div className={clsx(
      'rounded-lg border transition-colors',
      claimState === 'SUPPORTED'    && 'border-green-800/40 bg-green-950/20',
      claimState === 'CONTRADICTED' && 'border-red-800/40   bg-red-950/20',
      claimState === 'NEUTRAL'      && 'border-amber-800/40 bg-amber-950/20',
      !claimState                   && 'border-slate-700/40 bg-slate-800/20',
    )}>
      <button
        className="w-full flex items-start gap-3 p-3 text-left hover:bg-white/5 transition-colors rounded-lg"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <span className="text-slate-500 text-xs font-mono mt-0.5 min-w-[1.5rem]">
          C{index}
        </span>
        <span className="flex-1 text-sm text-slate-200">{claim.text}</span>
        <div className="flex items-center gap-2 shrink-0">
          <ClaimStateBadge state={claimState} />
          {open ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
        </div>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 animate-fade-in">
          {(claim.subject || claim.predicate || claim.object) && (
            <div className="flex items-center gap-1.5 text-xs text-slate-300 bg-surface-900/60 border border-slate-800 rounded px-2.5 py-1.5 font-mono">
              <span className="text-slate-500 font-sans text-[11px] font-medium mr-1">Triple:</span>
              <span className="text-primary-300">({claim.subject || '—'}</span>
              <span className="text-slate-500">→</span>
              <span className="text-amber-300">{claim.predicate || '—'}</span>
              <span className="text-slate-500">→</span>
              <span className="text-cyan-300">{claim.object || '—'})</span>
            </div>
          )}
          {claim.explanation && (
            <div className="flex gap-2 text-xs text-slate-400 bg-surface-800/50 rounded p-2">
              <Quote size={12} className="shrink-0 mt-0.5 text-slate-500" />
              <span>{claim.explanation}</span>
            </div>
          )}
          {claim.evidence_ids?.length > 0 && (
            <div className="text-xs text-slate-500">
              Evidence: {claim.evidence_ids.map(id => (
                <code key={id} className="ml-1 px-1 bg-surface-800 rounded text-primary-400">
                  {String(id).slice(-6)}
                </code>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
