import { clsx } from 'clsx'
import { Check, X, CircleDashed, CircleSlash, HelpCircle } from 'lucide-react'
import { normalizeScore } from '@/lib/claimState'

/**
 * The bands, keyed by the verdict the reliability engine returned.
 *
 * An abstention is not a failure: the run produced no answer, so it does
 * not get the alarm colour. The CircleSlash icon carries that meaning.
 */
const BAND_BY_STATUS = {
  TRUSTED: 'high',
  UNCERTAIN: 'medium',
  FAILED: 'low',
  ABSTAINED: 'unknown',
}

/**
 * ReliabilityBadge — the numeric reliability score, with its band.
 *
 * The band is a step in the silver ramp, except the failing band, which is
 * Laser Crimson. A failed claim is the only thing on screen that carries
 * colour.
 *
 * The band comes from the verdict the backend computed, not from the
 * score: TRUSTED is a claim-coverage and contradiction-rate judgement, and
 * a score alone cannot make it. When no verdict is available the score
 * still says whether the run was above the abstention floor or below it.
 */
export function ReliabilityBadge({ score, status, size = 'md' }) {
  const norm = normalizeScore(score)
  const pct = norm != null ? Math.round(norm * 100) : null

  const band = BAND_BY_STATUS[status] ?? (pct == null ? 'unknown' : pct >= 50 ? 'medium' : 'low')

  const bandColors = {
    high: 'text-silver-200 border-[color:var(--rule)] bg-surface-inset',
    medium: 'text-silver-400 border-[color:var(--rule)] bg-surface-inset',
    low: 'text-crimson-300 border-[color:rgba(212,21,20,0.45)] bg-[rgba(212,21,20,0.09)]',
    unknown: 'text-silver-500 border-[color:var(--rule-faint)] bg-surface-inset',
  }

  // Icons, not glyphs. Every verdict gets its own shape so it survives a
  // monochrome display.
  const statusIcon = {
    TRUSTED: Check,
    UNCERTAIN: CircleDashed,
    ABSTAINED: CircleSlash,
    FAILED: X,
  }

  const sizes = {
    sm: 'text-xs px-2 py-0.5 gap-1.5',
    md: 'text-sm px-3 py-1 gap-1.5',
    lg: 'text-base px-4 py-1.5 gap-2',
  }

  const Icon = statusIcon[status] ?? HelpCircle

  return (
    <span
      aria-live="polite"
      className={clsx(
        'inline-flex items-center font-mono font-medium rounded-full border',
        bandColors[band],
        sizes[size],
      )}
    >
      <Icon size={13} strokeWidth={2} className="opacity-80" aria-hidden="true" />
      <span className="tabular-nums">{pct != null ? `${pct}%` : '—'}</span>
      {status && (
        <span className="text-xs font-sans opacity-70 ml-1 font-normal">{status}</span>
      )}
    </span>
  )
}

/**
 * VerdictBadge — SUPPORTED | CONTRADICTED | NEUTRAL | UNCHECKED
 * (UNCHECKED = the claim was never NLI-verified, so it is not support)
 */
export function VerdictBadge({ state }) {
  const norm = state ? String(state).toUpperCase() : ''

  const map = {
    SUPPORTED: { status: 'supported', label: 'Supported', Icon: Check },
    CONTRADICTED: { status: 'contradicted', label: 'Contradicted', Icon: X },
    NEUTRAL: { status: 'unsupported', label: 'Neutral', Icon: CircleDashed },
    UNCHECKED: { status: 'unknown', label: 'Unverified', Icon: HelpCircle },
  }

  const { status, label, Icon } = map[norm] ?? {
    status: 'unknown',
    label: state ?? 'Unknown',
    Icon: HelpCircle,
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border bg-surface-inset px-2.5 py-0.5 text-xs font-medium',
        status === 'contradicted'
          ? 'border-[color:rgba(212,21,20,0.45)] text-crimson-300'
          : status === 'supported'
            ? 'border-[color:var(--rule)] text-silver-200'
            : 'border-[color:var(--rule-faint)] text-silver-500',
      )}
    >
      <Icon
        size={12}
        strokeWidth={2}
        className={
          status === 'contradicted'
            ? 'text-crimson-400'
            : status === 'supported'
              ? 'text-silver-300'
              : 'text-silver-500'
        }
        aria-hidden="true"
      />
      <span>{label}</span>
    </span>
  )
}
