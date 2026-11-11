import { clsx } from 'clsx'
import { Check, X, CircleDashed, Circle } from 'lucide-react'

/**
 * Badge — the verdict marker.
 *
 * The verdict family is a monochrome ramp plus one alarm. Supported is the
 * brightest silver, unsupported steps down, unknown is dim, and
 * contradicted is Laser Crimson. The icon shape differs per verdict, so the
 * badge survives a monochrome display and never relies on colour alone.
 */

const VERDICTS = {
  supported: {
    label: 'Supported',
    Icon: Check,
    className: 'border-[color:var(--rule)] text-silver-200',
    iconClassName: 'text-silver-300',
  },
  contradicted: {
    label: 'Contradicted',
    Icon: X,
    className: 'border-[color:rgba(212,21,20,0.45)] text-crimson-300',
    iconClassName: 'text-crimson-400',
  },
  unsupported: {
    label: 'Unsupported',
    Icon: CircleDashed,
    className: 'border-[color:var(--rule)] text-silver-500',
    iconClassName: 'text-silver-500',
  },
  unknown: {
    label: 'Unknown',
    Icon: Circle,
    className: 'border-[color:var(--rule-faint)] text-silver-600',
    iconClassName: 'text-silver-600',
  },
}

export default function Badge({
  status = 'unknown',
  label,
  size = 'md',
  className = '',
  ...rest
}) {
  const meta = VERDICTS[status] ?? VERDICTS.unknown
  const Icon = meta.Icon

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border bg-surface-inset font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-0.5 text-xs',
        meta.className,
        className,
      )}
      {...rest}
    >
      <Icon size={size === 'sm' ? 11 : 12} strokeWidth={2} className={meta.iconClassName} aria-hidden="true" />
      <span>{label ?? meta.label}</span>
    </span>
  )
}

export { VERDICTS }
