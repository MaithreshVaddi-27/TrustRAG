import { forwardRef } from 'react'
import { clsx } from 'clsx'
import { motion } from 'motion/react'

/**
 * Button — the one control in the product.
 *
 * Chrome Silver is the accent: the primary action is an off-white plate
 * with obsidian text, which reads more deliberate than a coloured button on
 * a dark theme and keeps Laser Crimson free to mean "something needs
 * attention". Every variant meets the 44×44px minimum target.
 */

const VARIANTS = {
  primary: 'lx-btn--primary',
  secondary: 'lx-btn--secondary',
  quiet: 'lx-btn--quiet',
}

const SIZES = {
  sm: 'min-h-[36px] px-3 text-caption',
  md: '',
  lg: 'lx-btn--large',
  block: 'lx-btn--block',
}

const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    className = '',
    children,
    disabled = false,
    loading = false,
    icon,
    iconPosition = 'right',
    fullWidth = false,
    type = 'button',
    ...props
  },
  ref,
) {
  const press = { duration: 0.08, ease: 'easeOut' }

  return (
    <motion.button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      className={clsx(
        'lx-btn',
        VARIANTS[variant] ?? VARIANTS.primary,
        SIZES[size] ?? '',
        fullWidth && 'lx-btn--block',
        className,
      )}
      whileTap={disabled || loading ? undefined : { scale: 0.985, transition: press }}
      {...props}
    >
      {loading ? (
        <span className="flex items-center gap-2" role="status" aria-label="Loading">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span className="sr-only">Loading</span>
        </span>
      ) : (
        <>
          {icon && iconPosition === 'left' && (
            <span className="lx-btn__icon" aria-hidden="true">
              {icon}
            </span>
          )}
          <span className="relative z-10">{children}</span>
          {icon && iconPosition === 'right' && (
            <span className="lx-btn__icon" aria-hidden="true">
              {icon}
            </span>
          )}
        </>
      )}
    </motion.button>
  )
})

Button.displayName = 'Button'

export default Button
