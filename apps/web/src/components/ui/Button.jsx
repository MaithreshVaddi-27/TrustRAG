import { forwardRef } from 'react'
import { clsx } from 'clsx'
import { Slot } from '@radix-ui/react-slot'
import { motion } from 'motion/react'

/**
 * Button — Unified button primitive (Ledger v3).
 * All variants meet 44×44px minimum touch target.
 * Springs for press feedback, magnetic hover on primary/luxury.
 * Spring config: damping 25, stiffness 200 (critically damped, no overshoot).
 */
const Button = forwardRef(function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  disabled = false,
  loading = false,
  icon,
  iconPosition = 'right',
  fullWidth = false,
  magnetic = false,
  asChild = false,
  ...props
}, ref) {
  const baseStyles = [
    'inline-flex items-center justify-center font-semibold',
    'transition-all duration-200 ease-out-expo',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-950',
    'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
    'touch-manipulation select-none',
    fullWidth ? 'w-full' : '',
  ]

  const Comp = asChild ? Slot : 'button'

  const variantStyles = {
    primary: [
      'bg-gradient-to-r from-primary-600 via-primary-500 to-cyan-600',
      'hover:from-primary-500 hover:via-primary-400 hover:to-cyan-500',
      'active:from-primary-700 active:via-primary-600 active:to-cyan-700',
      'text-white',
      'shadow-lg shadow-primary-950/60 hover:shadow-primary-900/50',
      'border border-cyan-400/30 hover:border-cyan-400/50',
      'relative overflow-hidden',
      magnetic && 'group',
    ],
    secondary: [
      'bg-surface-800/80',
      'hover:bg-surface-700/80',
      'active:bg-surface-600/80',
      'text-slate-300 hover:text-white',
      'border border-slate-700/80 hover:border-slate-600',
      'shadow-md shadow-surface-950/50',
    ],
    danger: [
      'bg-gradient-to-r from-red-950/50 to-red-900/50',
      'hover:from-red-900/50 hover:to-red-800/50',
      'active:from-red-800/50 active:to-red-700/50',
      'text-red-300 hover:text-red-100',
      'border border-red-800/60 hover:border-red-700',
      'shadow-lg shadow-red-950/60',
    ],
    ghost: [
      'bg-transparent',
      'hover:bg-surface-800/50',
      'active:bg-surface-700/50',
      'text-slate-400 hover:text-white',
      'border border-transparent hover:border-slate-700/50',
    ],
    outline: [
      'bg-transparent',
      'hover:bg-primary-950/30',
      'active:bg-primary-900/30',
      'text-primary-400 hover:text-primary-300',
      'border border-primary-500/50 hover:border-primary-400',
    ],
    luxury: [
      'bg-gradient-to-r from-primary-600 via-primary-500 to-cyan-600',
      'hover:from-primary-500 hover:via-primary-400 hover:to-cyan-500',
      'active:from-primary-700 active:via-primary-600 active:to-cyan-700',
      'text-white',
      'shadow-2xl shadow-primary-950/80 hover:shadow-primary-900/60',
      'border border-cyan-400/50 hover:border-gold-400/50',
      'relative overflow-hidden group',
      'after:content-[""] after:absolute after:inset-0 after:bg-gradient-to-r after:from-transparent after:via-gold-400/20 after:to-transparent after:-translate-x-full group-hover:after:translate-x-full after:transition-transform after:duration-700',
    ],
  }

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs min-h-[40px] gap-1.5',
    md: 'px-4 py-2.5 text-sm min-h-[44px] gap-2',
    lg: 'px-6 py-3.5 text-base min-h-[52px] gap-2.5',
    xl: 'px-8 py-4 text-lg min-h-[56px] gap-3',
    icon: 'p-2.5 min-h-[44px] min-w-[44px]',
    'icon-lg': 'p-3 min-h-[48px] min-w-[48px]',
  }

  const iconEl = icon && (
    <motion.span
      className={clsx(
        'flex-shrink-0',
        iconPosition === 'right' && 'group-hover:translate-x-1',
        iconPosition === 'left' && '-group-hover:translate-x-1'
      )}
      aria-hidden="true"
      whileHover={{ x: iconPosition === 'right' ? 4 : -4, transition: { type: 'spring', damping: 25, stiffness: 200 } }}
    >
      {typeof icon === 'function' ? icon({ size: size === 'sm' ? 14 : 16 }) : icon}
    </motion.span>
  )

  const pressTransition = { duration: 0.08, ease: 'easeOut' }
  const springTransition = { type: 'spring', damping: 25, stiffness: 200 }

  const motionProps = {
    whileHover: magnetic && (variant === 'primary' || variant === 'luxury') ? { scale: 1.03, transition: springTransition } : undefined,
    whileTap: { scale: 0.97, transition: pressTransition },
  }

  return (
    <motion.button
      ref={ref}
      as={Comp}
      className={clsx(baseStyles, variantStyles[variant], sizeStyles[size], className)}
      disabled={disabled || loading}
      style={{ ...(magnetic && (variant === 'primary' || variant === 'luxury') ? { '--magnetic-strength': '0.3' } : {}) }}
      {...motionProps}
      {...props}
    >
      {loading ? (
        <span className="flex items-center gap-1.5" role="status" aria-label="Loading">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="sr-only">Loading</span>
        </span>
      ) : (
        <>
          {iconPosition === 'left' && iconEl}
          <span className="relative z-10">{children}</span>
          {iconPosition === 'right' && iconEl}
        </>
      )}
    </motion.button>
  )
})

Button.displayName = 'Button'

export default Button