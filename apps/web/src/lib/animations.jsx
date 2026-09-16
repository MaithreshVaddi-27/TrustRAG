// ── Reusable Animation Wrappers ──────────────────────────────────────────────
// Apple Design: springs animate from the current value by default,
// which is exactly what interruption needs.
/* eslint-disable react-refresh/only-export-components */
import { motion } from 'motion/react'
import { SPRING_SNAPPY, SPRING_GENTLE } from './motionConfig'

/**
 * Staggered container — wraps children and staggers their entrance.
 * Children must be motion.* components with `initial` + `animate`.
 */
export function Stagger({ children, className, delay = 0, ...props }) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: 0.06,
            delayChildren: delay,
          },
        },
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

/**
 * Child variant for Stagger — wraps each direct child with entrance.
 * Apply to motion.* children of <Stagger>.
 */
export const staggerChild = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: SPRING_GENTLE,
  },
}

/**
 * Fade in from below — single element entrance.
 */
export function FadeInUp({ children, className, delay = 0, ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...SPRING_GENTLE, delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

/**
 * Scale in — for modals, popovers, tooltips.
 */
export function ScaleIn({ children, className, delay = 0, ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ ...SPRING_SNAPPY, delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

/**
 * Slide in from the side — for panels, drawers.
 */
export function SlideIn({ children, className, direction = 'left', delay = 0, ...props }) {
  const axis = direction === 'left' || direction === 'right' ? 'x' : 'y'
  const from = direction === 'left' || direction === 'up' ? -16 : 16

  return (
    <motion.div
      initial={{ opacity: 0, [axis]: from }}
      animate={{ opacity: 1, [axis]: 0 }}
      exit={{ opacity: 0, [axis]: from }}
      transition={{ ...SPRING_SNAPPY, delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}
