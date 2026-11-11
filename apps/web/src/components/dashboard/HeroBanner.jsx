import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { Database, Zap, Activity } from 'lucide-react'
import { useReducedMotion } from 'motion/react'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

export function HeroBanner() {
  const reduced = useReducedMotion()
  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="glass-card relative overflow-hidden p-6 sm:p-8 border-primary-500/20 bg-gradient-to-br from-surface-900/90 via-surface-900/60 to-primary-950/20"
    >
      {/* Subtle glowing ambient orb */}
      {!reduced && (
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-primary-500/10 blur-3xl pointer-events-none" />
      )}

      <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 border border-primary-500/30 text-xs font-mono text-primary-300">
            <motion.span
              className="w-1.5 h-1.5 rounded-full bg-cyan-400"
              animate={!reduced ? { scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] } : false}
              transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
              aria-hidden="true"
            />
            <Activity size={12} className="text-cyan-400" aria-hidden="true" />
            <span>Production Observability Engine Active</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            AI Reliability <span className="text-gradient">Workbench</span>
          </h1>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl leading-relaxed">
            Autonomous hallucination detection, atomic claim verification, and self-healing closed-loop RAG recovery powered by LangGraph.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <motion.button
            as={Link}
            to="/knowledge-bases"
            whileHover={{ scale: 1.02, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: pressTransition }}
            className="btn-secondary text-xs sm:text-sm px-4 py-2.5 flex items-center gap-2"
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            <Database size={15} aria-hidden="true" />
            <span>Knowledge Bases</span>
          </motion.button>
          <motion.button
            as={Link}
            to="/playground"
            whileHover={{ scale: 1.02, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: pressTransition }}
            className="btn-primary text-xs sm:text-sm px-5 py-2.5 shadow-lg shadow-primary-900/40 flex items-center gap-2"
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            <Zap size={15} aria-hidden="true" />
            <span>Run Interactive Analysis</span>
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}