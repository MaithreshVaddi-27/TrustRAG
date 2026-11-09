import { clsx } from 'clsx'

/**
 * Card — Enhanced glass surface with elevation variants (Ledger v3).
 * `hover` adds premium lift with spring transition; `dashed` for empty states.
 * `elevation` controls shadow depth: 'flat' | 'raised' | 'lift' | 'premium'
 * `interactive` enables press feedback and magnetic hover zones.
 */
export default function Card({
  className = '',
  hover = false,
  dashed = false,
  elevation = 'flat',
  interactive = false,
  magnetic = false,
  children,
  ...rest
}) {
  const elevationStyles = {
    flat: '',
    raised: 'shadow-card',
    lift: 'shadow-lift',
    premium: 'shadow-2xl shadow-primary-950/40 border-cyan-500/20',
  }

  const hoverStyles = hover
    ? 'glass-card-hover lift-hover transition-all duration-300 ease-out-expo'
    : 'transition-all duration-200 ease-out-expo'

  const interactiveStyles = interactive
    ? 'cursor-pointer touch-manipulation select-none active:scale-[0.99] active:transition-transform active:duration-80'
    : ''

  const magneticStyles = magnetic && interactive ? 'group' : ''

  const classes = clsx(
    'glass-card backdrop-blur-xl',
    elevationStyles[elevation],
    hoverStyles,
    interactiveStyles,
    magneticStyles,
    dashed && 'border-dashed border-slate-700/60 bg-surface-900/40',
    className
  )

  return (
    <div className={classes} {...rest}>
      {children}
      {interactive && magnetic && (
        <div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-gold-400/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 pointer-events-none"
          aria-hidden="true"
        />
      )}
    </div>
  )
}
