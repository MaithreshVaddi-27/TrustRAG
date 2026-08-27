import { clsx } from 'clsx'

/**
 * ReliabilityBadge — shows the numeric reliability score with color-coded band.
 * score: 0.0–1.0
 * status: 'TRUSTED' | 'UNCERTAIN' | 'ABSTAINED' | 'FAILED'
 */
export function ReliabilityBadge({ score, status, size = 'md' }) {
  const pct = score != null ? Math.round(score * 100) : null

  const band =
    pct == null     ? 'unknown'
    : pct >= 75     ? 'high'
    : pct >= 50     ? 'medium'
    :                 'low'

  const bandColors = {
    high:    'text-green-400 border-green-700/50 bg-green-900/30',
    medium:  'text-amber-400 border-amber-700/50 bg-amber-900/30',
    low:     'text-red-400   border-red-700/50   bg-red-900/30',
    unknown: 'text-slate-400 border-slate-600/50 bg-slate-800/30',
  }

  const statusIcon = {
    TRUSTED:   '✓',
    UNCERTAIN: '~',
    ABSTAINED: '⊘',
    FAILED:    '✗',
    undefined:  '?',
  }

  const sizes = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-sm px-3 py-1   gap-1.5',
    lg: 'text-base px-4 py-1.5 gap-2',
  }

  return (
    <span className={clsx(
      'inline-flex items-center font-mono font-semibold rounded-full border',
      bandColors[band],
      sizes[size],
    )}>
      <span className="opacity-70">{statusIcon[status] ?? '?'}</span>
      {pct != null ? `${pct}%` : '—'}
      {status && <span className="text-xs font-sans opacity-60 ml-1 font-normal">{status}</span>}
    </span>
  )
}

/**
 * ClaimStateBadge — SUPPORTED | CONTRADICTED | UNSUPPORTED | UNKNOWN
 */
export function ClaimStateBadge({ state }) {
  const map = {
    SUPPORTED:    { cls: 'badge-supported',    label: 'Supported',    icon: '✓' },
    CONTRADICTED: { cls: 'badge-contradicted',  label: 'Contradicted', icon: '✗' },
    UNSUPPORTED:  { cls: 'badge-unsupported',   label: 'Unsupported',  icon: '?' },
    UNKNOWN:      { cls: 'badge-unknown',       label: 'Unknown',      icon: '~' },
  }
  const { cls, label, icon } = map[state] ?? map.UNKNOWN
  return (
    <span className={cls}>
      <span>{icon}</span>
      {label}
    </span>
  )
}

/**
 * StatusDot — animated dot for live/running states.
 */
export function StatusDot({ status }) {
  const map = {
    running:   'bg-primary-400 animate-pulse',
    completed: 'bg-green-400',
    failed:    'bg-red-400',
    abstained: 'bg-amber-400',
    pending:   'bg-slate-500',
  }
  return (
    <span className={clsx('inline-block w-2 h-2 rounded-full', map[status] ?? map.pending)} />
  )
}
