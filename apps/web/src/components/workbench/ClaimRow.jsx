import { clsx } from 'clsx'
import { ChevronDown, ChevronRight, Quote, Check, Copy } from 'lucide-react'
import { useState } from 'react'
import { VerdictBadge } from './ReliabilityBadge'

/**
 * ClaimRow — one atomic proposition and its verdict.
 *
 * The proposition is the subject, the verdict is a badge, and the detail
 * (subject-predicate-object decomposition, the explanation, the citations)
 * is one click away. A contradicted claim is the only row that carries
 * crimson, and it carries it on the rule, not on a badge of colour.
 */
export default function ClaimRow({ claim, index, isForceExpanded, onCopy, isCopied }) {
  const [open, setOpen] = useState(false)
  const isExpanded = isForceExpanded || open
  const claimState = (
    claim.state ||
    claim.status ||
    claim.verification_status ||
    ''
  ).toUpperCase()

  const isContradicted = claimState === 'CONTRADICTED'

  const bodyId = `claim-body-${index}`

  return (
    <article
      style={{ '--claim-index': index }}
      className={clsx(
        'lx-claim-row overflow-hidden rounded-[var(--radius-card)] border bg-surface-card',
        isContradicted
          ? 'border-[color:var(--crimson-rule-40)]'
          : 'border-[color:var(--rule)]',
      )}
    >
      <div className="flex w-full items-start gap-3 p-4">
        <span
          className="lx-layer__index mt-0.5 min-w-[1.75rem] shrink-0 text-right"
          aria-hidden="true"
        >
          {String(index).padStart(2, '0')}
        </span>

        <button
          type="button"
          onClick={() => setOpen((previous) => !previous)}
          aria-expanded={isExpanded}
          aria-controls={bodyId}
          className="min-w-0 flex-1 cursor-pointer bg-transparent p-0 text-left"
        >
          <p className="break-words text-[var(--size-body)] leading-relaxed text-silver-100">
            {claim.text}
          </p>
        </button>

        <div className="flex shrink-0 items-center gap-2">
          <VerdictBadge state={claimState} />

          <button
            type="button"
            onClick={onCopy}
            className="lx-icon-btn h-8 w-8"
            title="Copy the claim"
            aria-label={`Copy claim ${index}`}
          >
            {isCopied ? (
              <Check size={13} strokeWidth={2} aria-hidden="true" />
            ) : (
              <Copy size={13} strokeWidth={1.75} aria-hidden="true" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setOpen((previous) => !previous)}
            className="lx-icon-btn h-8 w-8"
            aria-label={isExpanded ? 'Collapse the claim detail' : 'Expand the claim detail'}
          >
            {isExpanded ? (
              <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" />
            ) : (
              <ChevronRight size={14} strokeWidth={1.75} aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div
          id={bodyId}
          className="space-y-3 border-t border-[color:var(--rule-faint)] px-4 py-4"
        >
          {(claim.subject || claim.predicate || claim.object) && (
            <dl className="lx-deflist">
              <div className="lx-deflist__row">
                <dt className="lx-deflist__key">Subject</dt>
                <dd className="lx-deflist__value">{claim.subject || '—'}</dd>
              </div>
              <div className="lx-deflist__row">
                <dt className="lx-deflist__key">Predicate</dt>
                <dd className="lx-deflist__value">{claim.predicate || '—'}</dd>
              </div>
              <div className="lx-deflist__row">
                <dt className="lx-deflist__key">Object</dt>
                <dd className="lx-deflist__value">{claim.object || '—'}</dd>
              </div>
            </dl>
          )}

          {claim.explanation && (
            <p className="flex gap-2 text-[var(--size-body-sm)] leading-relaxed text-silver-400">
              <Quote
                size={13}
                strokeWidth={1.75}
                className="mt-0.5 shrink-0 text-silver-500"
                aria-hidden="true"
              />
              <span className="break-words">{claim.explanation}</span>
            </p>
          )}

          {claim.evidence_ids?.length > 0 && (
            <div>
              <p className="lx-section-label">Supporting citations</p>
              <div className="flex flex-wrap gap-2">
                {claim.evidence_ids.map((id) => (
                  <span key={id} className="lx-chip">
                    #{String(id).slice(-6)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  )
}
