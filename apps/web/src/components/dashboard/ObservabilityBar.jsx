import { motion } from 'motion/react'
import { RefreshCw, Radio, Circle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useReducedMotion } from 'motion/react'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

/**
 * ObservabilityBar - Live observability control bar
 * Called by: DashboardPage.jsx (line 146-154)
 * Reads: lastSync from DashboardPage state (updated via 30s tick + manual sync)
 */
export function ObservabilityBar({
  autoRefresh,
  setAutoRefresh,
  lastSync,
  isFetchingAnalyses,
  handleManualSync,
}) {
  const reduced = useReducedMotion()
  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 rounded-2xl border border-cyan-500/30 bg-surface-900/80 backdrop-blur-xl shadow-lg shadow-cyan-950/20"
    >
      <div className="flex items-center gap-3">
        <motion.span
          className="flex items-center justify-center"
          whileHover={{ scale: 1.1, transition: springTransition }}
          whileTap={{ scale: 0.95, transition: pressTransition }}
        >
          {autoRefresh ? (
            <>
              <motion.span
                className="w-2.5 h-2.5 rounded-full bg-emerald-400"
                animate={{ scale: [1, 1.3, 1], opacity: [1, 0, 1] }}
                transition={{ duration: 1.5, ease: 'easeOut', repeat: Infinity }}
                aria-hidden="true"
              />
              <Radio size={10} className="text-emerald-400" aria-hidden="true" />
            </>
          ) : (
            <Circle size={10} className="text-slate-500" aria-hidden="true" />
          )}
        </motion.span>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold tracking-wider uppercase text-cyan-300">
            Live Observability Stream
          </span>
          <motion.span
            className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
              autoRefresh
                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60'
                : 'bg-surface-950 text-slate-400 border-slate-800'
            }`}
            initial={reduced ? { opacity: 1 } : { opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={springTransition}
          >
            {autoRefresh ? 'Active Polling (5s)' : 'Paused'}
          </motion.span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
        <span>Synced {formatDistanceToNow(lastSync, { addSuffix: true })}</span>
        <motion.button
          type="button"
          onClick={handleManualSync}
          disabled={isFetchingAnalyses}
          whileHover={{ scale: 1.02, transition: springTransition }}
          whileTap={{ scale: 0.97, transition: pressTransition }}
          className="px-2.5 py-1.5 rounded-xl bg-surface-800 hover:bg-surface-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-sm"
          style={{ minHeight: '44px', minWidth: '44px' }}
          title="Force sync live state"
          aria-label="Force sync live state"
        >
          <motion.span
            className={isFetchingAnalyses ? 'text-cyan-400' : 'text-slate-400'}
            animate={isFetchingAnalyses && !reduced ? { rotate: 360 } : false}
            transition={{ duration: 1, ease: 'linear', repeat: Infinity }}
          >
            <RefreshCw size={12} aria-hidden="true" />
          </motion.span>
          <span>Sync Now</span>
        </motion.button>
        <motion.button
          type="button"
          onClick={() => setAutoRefresh(prev => !prev)}
          whileHover={{ scale: 1.02, transition: springTransition }}
          whileTap={{ scale: 0.97, transition: pressTransition }}
          className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all shadow-sm ${
            autoRefresh
              ? 'bg-emerald-950/50 border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/50'
              : 'bg-surface-800 border-slate-700 text-slate-300 hover:text-white'
          }`}
          style={{ minHeight: '44px', minWidth: '44px' }}
        >
          {autoRefresh ? 'Pause Stream' : 'Go Live'}
        </motion.button>
      </div>
    </motion.div>
  )
}