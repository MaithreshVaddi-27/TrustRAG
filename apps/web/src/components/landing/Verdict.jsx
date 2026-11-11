import { memo } from 'react'
import { clsx } from 'clsx'
import { Check, X, CircleDashed, Circle } from 'lucide-react'

/**
 * Verdict — the result of a claim audit.
 *
 * The icon carries the verdict colour; the label always uses the readable
 * text role. Colour never travels alone — the word is always there, and the
 * icon shape differs per verdict so it survives a monochrome display.
 */

const VERDICT_META = {
  supported: { label: 'Supported', Icon: Check },
  contradicted: { label: 'Contradicted', Icon: X },
  unsupported: { label: 'Unsupported', Icon: CircleDashed },
  unknown: { label: 'Unknown', Icon: Circle },
}

const Verdict = memo(function Verdict({
  status = 'unknown',
  label,
  className = '',
  size = 14,
}) {
  const meta = VERDICT_META[status] ?? VERDICT_META.unknown
  const Icon = meta.Icon

  return (
    <span className={clsx('lx-verdict', `lx-verdict--${status}`, className)}>
      <Icon className="lx-verdict__mark" size={size} strokeWidth={1.75} aria-hidden="true" />
      <span>{label ?? meta.label}</span>
    </span>
  )
})

export { VERDICT_META }
export default Verdict
