import { AlertTriangle, X } from 'lucide-react'
import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }

export function ErrorDisplay({ errorMsg, setErrorMsg }) {
  const reduced = useReducedMotion()

  if (!errorMsg) return null

  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY

  return (
    <motion.div
      role="alert"
      initial={reduced ? { opacity: 1, height: 'auto' } : { opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
      transition={reduced ? { duration: 0.01 } : { duration: 0.25, ease: 'easeOut' }}
      className="p-3 bg-red-950/70 border border-red-800/80 rounded-xl text-xs text-red-300 flex items-start justify-between gap-2 shadow-glow-crimson animate-fade-in"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle size={14} className="shrink-0 mt-0.5 text-red-400" aria-hidden="true" />
        <span>{errorMsg}</span>
      </div>
      <motion.button
        type="button"
        onClick={() => setErrorMsg('')}
        aria-label="Dismiss error"
        whileHover={{ scale: 1.1, transition: springTransition }}
        whileTap={{ scale: 0.9, transition: { duration: 0.08, ease: 'easeOut' } }}
        className="text-red-400 hover:text-red-200 text-sm font-bold leading-none shrink-0 p-1 rounded transition-colors"
      >
        <X size={14} aria-hidden="true" />
      </motion.button>
    </motion.div>
  )
}