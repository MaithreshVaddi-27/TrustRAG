import { clsx } from 'clsx'
import { useState } from 'react'
import {
  BookOpen,
  ExternalLink,
  Shield,
  ShieldAlert,
  Globe,
  Copy,
  Check,
} from 'lucide-react'
import { isWebSource } from '@/lib/claimState'

/**
 * EvidenceChunk — one retrieved passage and its provenance.
 *
 * The integrity badge is fail-closed: only an explicit VERIFIED earns the
 * shield, and anything else — including a missing status — reads as
 * unverified. A web citation from MCP is labelled as such and is never
 * presented as cryptographically verified.
 */
/**
 * Figure — one measurement in the strip under a passage.
 */
function Figure({ label, value }) {
  return (
    <div className="lx-figure">
      <dt className="lx-figure__label">{label}</dt>
      <dd className="lx-figure__value">{value}</dd>
    </div>
  )
}

export default function EvidenceChunk({ chunk, rank, onCopy, isCopied }) {
  const [expanded, setExpanded] = useState(false)

  const integrityOk = chunk.integrity_status === 'VERIFIED'
  const integrityLabel = chunk.integrity_status || 'UNVERIFIED'
  const isWeb = isWebSource(chunk)
  const isLong = chunk.text && chunk.text.length > 260

  return (
    <article className="lx-panel-block">
      <div className="lx-panel-block__head">
        <div className="flex min-w-0 items-center gap-2">
          <span className="lx-layer__index shrink-0">#{String(rank).padStart(2, '0')}</span>
          {isWeb ? (
            <Globe size={13} strokeWidth={1.75} className="shrink-0 text-silver-500" aria-hidden="true" />
          ) : (
            <BookOpen size={13} strokeWidth={1.75} className="shrink-0 text-silver-500" aria-hidden="true" />
          )}
          <h2 className="truncate text-[var(--size-body)] text-silver-100">
            {chunk.filename ?? chunk.document_id ?? (isWeb ? 'MCP web citation' : 'Unknown source')}
          </h2>
          {isWeb && <span className="lx-chip shrink-0">MCP</span>}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={onCopy}
            className="lx-icon-btn h-8 w-8"
            title="Copy the evidence snippet"
            aria-label="Copy the evidence snippet"
          >
            {isCopied ? (
              <Check size={13} strokeWidth={2} aria-hidden="true" />
            ) : (
              <Copy size={13} strokeWidth={1.75} aria-hidden="true" />
            )}
          </button>

          {integrityOk ? (
            <Shield
              size={13}
              strokeWidth={1.75}
              className="text-silver-400"
              title="Cryptographic provenance verified"
              aria-label="Cryptographic provenance verified"
            />
          ) : (
            <ShieldAlert
              size={13}
              strokeWidth={1.75}
              className="text-silver-500"
              title={integrityLabel}
              aria-label={integrityLabel}
            />
          )}

          {!integrityOk && <span className="lx-micro">{integrityLabel}</span>}
        </div>
      </div>

      <div className="lx-panel-block__body space-y-3">
        <div
          className={clsx(
            'break-words border-l pl-3 text-[var(--size-body-sm)] leading-relaxed',
            isWeb
              ? 'border-[color:var(--rule-strong)] text-silver-300'
              : 'border-[color:var(--rule-strong)] text-silver-300',
          )}
        >
          {chunk.text}
        </div>

        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((previous) => !previous)}
            className="lx-btn lx-btn--quiet"
            aria-expanded={expanded}
          >
            {expanded ? 'Show less' : `Show the full segment (${chunk.text.length} characters)`}
          </button>
        )}

        {/* The measurements sit under the passage as a run of figures, not as
            a list of key/value rows. A passage is the subject of this card;
            the scores are its attributes, and five rows of them would
            outweigh the text they describe. */}
        <dl className="lx-figures">
          {chunk.dense_score != null || chunk.retrieval_score != null ? (
            <Figure label="Dense" value={(chunk.dense_score ?? chunk.retrieval_score).toFixed(3)} />
          ) : null}

          {chunk.rrf_score != null || chunk.fusion_score != null ? (
            <Figure label="Fusion" value={(chunk.rrf_score ?? chunk.fusion_score).toFixed(3)} />
          ) : null}

          {chunk.rerank_score != null && (
            <Figure label="Rerank" value={chunk.rerank_score.toFixed(3)} />
          )}

          {chunk.method && <Figure label="Method" value={chunk.method} />}

          {(chunk.effective_from || chunk.effective_until) && (
            <Figure
              label="Effective"
              value={`${chunk.effective_from ? new Date(chunk.effective_from).toLocaleDateString() : '—'}${
                chunk.effective_until
                  ? ` → ${new Date(chunk.effective_until).toLocaleDateString()}`
                  : ''
              }`}
            />
          )}
        </dl>
      </div>

      {chunk.url && (
        <div className="lx-panel-block__foot">
          <a
            href={chunk.url}
            target="_blank"
            rel="noopener noreferrer"
            className="lx-btn lx-btn--quiet"
          >
            <span>Open the direct citation</span>
            <ExternalLink size={12} strokeWidth={1.75} aria-hidden="true" />
          </a>
        </div>
      )}
    </article>
  )
}
