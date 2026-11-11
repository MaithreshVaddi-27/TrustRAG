import { Zap, CornerDownLeft } from 'lucide-react'
import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

export function RunButton({ loading, elapsedSec, disabled, onClick }) {
  const reduced = useReducedMotion()

  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled || loading || !onClick}
      id="run-analysis"
      whileHover={{ scale: 1.02, transition: springTransition }}
      whileTap={{ scale: 0.97, transition: pressTransition }}
      className="btn-primary w-full flex items-center justify-center gap-2.5 shadow-lg shadow-primary-950/60 transition-all relative overflow-hidden"
      style={{
        background: 'linear-gradient(to right, var(--color-primary-600), var(--color-cyber-600))',
        minHeight: '44px',
        minWidth: '44px',
      }}
      aria-busy={loading}
      aria-label={loading ? `Executing pipeline (${elapsedSec}s elapsed)` : 'Run analysis'}
    >
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 pointer-events-none"
        aria-hidden="true"
      />

      {loading ? (
        <motion.div
          className="flex items-center justify-center gap-2.5"
          initial={reduced ? { opacity: 1 } : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={springTransition}
        >
          <ThinkingOrbs size="sm" elapsedSec={elapsedSec} />
          <span className="font-medium">Executing Pipeline</span>
          <span className="text-[10px] font-mono tabular-nums text-cyan-300">
            {elapsedSec}s
          </span>
        </motion.div>
      ) : (
        <motion.div
          className="flex items-center justify-center gap-2.5"
          initial={reduced ? { opacity: 1 } : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={springTransition}
        >
          <motion.span
            className="text-cyan-300"
            whileHover={{ rotate: 180, transition: { duration: 0.7, ease: 'easeOut' } }}
            aria-hidden="true"
          >
            <Zap size={14} />
          </motion.span>
          <span className="font-medium">Run Analysis</span>
          <span className="text-[10px] opacity-75 font-mono ml-1 flex items-center gap-0.5 text-slate-300">
            <CornerDownLeft size={10} aria-hidden="true" />
            ⌘Enter
          </span>
        </motion.div>
      )}
    </motion.button>
  )
}