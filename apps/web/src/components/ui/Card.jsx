import { clsx } from 'clsx'

/**
 * Card — the one container in the product.
 *
 * A hairline and a surface step. On a dark theme, depth comes from the
 * surface ramp, not from a shadow, and elevation is declared once: a rule
 * OR a shadow, never both.
 */

const ELEVATION = {
  flat: '',
  raised: 'bg-surface-card',
  panel: 'bg-surface-panel',
  inset: 'bg-surface-inset',
}

export default function Card({
  className = '',
  hover = false,
  dashed = false,
  elevation = 'raised',
  interactive = false,
  as: Tag = 'div',
  children,
  ...rest
}) {
  return (
    <Tag
      className={clsx(
        'rounded-[var(--radius-card)] border border-[color:var(--rule)]',
        ELEVATION[elevation] ?? ELEVATION.raised,
        hover &&
          'transition-colors duration-200 hover:border-[color:var(--rule-strong)] hover:bg-surface-card',
        dashed && 'border-dashed bg-surface-inset',
        interactive && 'cursor-pointer touch-manipulation select-none',
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  )
}
