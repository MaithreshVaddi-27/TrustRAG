import { forwardRef } from 'react'
import { clsx } from 'clsx'
import { motion } from 'motion/react'

/**
 * Badge — Semantic trust/claim badges with animated variants (Ledger v3).
 * Variants: supported | contradicted | neutral | unsupported | unknown | processing | verified
 * Props:
 *   - dot: show status dot (default true)
 *   - pulse: animate status dot for live/processing states
 *   - animated: enable entrance stagger and hover lift
 *   - size: 'sm' | 'md' | 'lg'
 */
const VARIANTS = {
  supported: {
    base: 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50 shadow-sm shadow-emerald-950/50',
    dot: 'bg-emerald-400',
    glow: 'shadow-emerald-950/30',
  },
  contradicted: {
    base: 'bg-red-950/60 text-red-300 border-red-700/50 shadow-sm shadow-red-950/50',
    dot: 'bg-red-400',
    glow: 'shadow-red-950/30',
  },
  neutral: {
    base: 'bg-amber-950/60 text-amber-300 border-amber-700/50 shadow-sm shadow-amber-950/50',
    dot: 'bg-amber-400',
    glow: 'shadow-amber-950/30',
  },
  unsupported: {
    base: 'bg-amber-950/60 text-amber-300 border-amber-700/50 shadow-sm shadow-amber-950/50',
    dot: 'bg-amber-400',
    glow: 'shadow-amber-950/30',
  },
  unknown: {
    base: 'bg-slate-800/80 text-slate-400 border-slate-700/60',
    dot: 'bg-slate-500',
    glow: 'none',
  },
  processing: {
    base: 'bg-cyan-950/60 text-cyan-300 border-cyan-700/50 shadow-sm shadow-cyan-950/50',
    dot: 'bg-cyan-400 animate-pulse',
    glow: 'shadow-cyan-950/30',
  },
  verified: {
    base: 'bg-gradient-to-r from-emerald-950/60 to-cyan-950/60 text-emerald-100 border-emerald-500/40 shadow-lg shadow-emerald-950/60',
    dot: 'bg-emerald-400',
    glow: 'shadow-emerald-950/40',
  },
}

const SIZE_CLASSES = {
  sm: 'px-2 py-0.5 text-[10px] gap-1',
  md: 'px-2.5 py-0.5 text-xs gap-1.5',
  lg: 'px-3 py-1 text-sm gap-2',
}

export const Badge = forwardRef(function Badge({
  variant = 'unknown',
  children,
  dot = true,
  pulse = false,
  animated = false,
  size = 'md',
  className = '',
  ...props
}, ref) {
  const v = VARIANTS[variant] || VARIANTS.unknown

  const baseClasses = clsx(
    'inline-flex items-center font-medium rounded-full border',
    'transition-all duration-300 ease-out-expo',
    SIZE_CLASSES[size],
    v.base,
    className
  )

  const dotEl = dot && (
    <motion.span
      aria-hidden="true"
      className={clsx('w-1.5 h-1.5 rounded-full shrink-0', v.dot, pulse && 'animate-pulse')}
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25, delay: animated ? 0.1 : 0 }}
    />
  )

  const content = (
    <span className="relative z-10 whitespace-nowrap">{children}</span>
  )

  if (animated) {
    return (
      <motion.span
        ref={ref}
        className={baseClasses}
        initial={{ opacity: 0, y: 8, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        whileHover={{ y: -1, boxShadow: v.glow !== 'none' ? v.glow : undefined }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        {...props}
      >
        {dotEl}
        {content}
      </motion.span>
    )
  }

  return (
    <span ref={ref} className={baseClasses} {...props}>
      {dotEl}
      {content}
    </span>
  )
})

Badge.displayName = 'Badge'

// Convenience sub-components for semantic clarity
export function SupportedBadge({ children = 'Supported', ...props }) {
  return <Badge variant="supported" {...props}>{children}</Badge>
}

export function ContradictedBadge({ children = 'Contradicted', ...props }) {
  return <Badge variant="contradicted" {...props}>{children}</Badge>
}

export function NeutralBadge({ children = 'Neutral', ...props }) {
  return <Badge variant="neutral" {...props}>{children}</Badge>
}

export function VerifiedBadge({ children = 'Verified', ...props }) {
  return <Badge variant="verified" animated={true} {...props}>{children}</Badge>
}

export function ProcessingBadge({ children = 'Processing…', ...props }) {
  return <Badge variant="processing" pulse animated {...props}>{children}</Badge>
}
