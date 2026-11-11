import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { Clock, Zap, ArrowRight } from 'lucide-react'
import { useReducedMotion } from 'motion/react'
import { formatDistanceToNow } from 'date-fns'
import { SkeletonRows } from '@/components/workbench/Skeleton'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

/**
 * RecentAnalysesFeed - Recent execution history list
 * Called by: DashboardPage.jsx (line 208)
 * Public function: RecentAnalysesFeed
 * Reads: analyses array, isInitialLoad boolean
 * User instruction: "continue with ultra-premium polish of dashboard page applying same patterns as HeroBanner, ObservabilityBar, MetricsGrid, ReliabilityChart"
 */
function cleanSnippet(text) {
  if (!text) return ''
  return text
    .replace(/[*_#`~[\]]/g, '')
    .replace(/-\s+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export function RecentAnalysesFeed({ analyses, isInitialLoad }) {
  const reduced = useReducedMotion()
  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="space-y-4"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Clock size={18} className="text-cyan-400" aria-hidden="true" />
            Recent Live Analysis Traces
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Execution history, grounded answers, and verification logs</p>
        </div>
        <motion.button
          as={Link}
          to="/playground"
          whileHover={{ scale: 1.02, transition: springTransition }}
          whileTap={{ scale: 0.97, transition: pressTransition }}
          className="text-xs font-semibold text-primary-400 hover:text-primary-300 transition-colors flex items-center gap-1"
          style={{ minHeight: '44px', minWidth: '44px' }}
        >
          Open Playground <ArrowRight size={13} aria-hidden="true" />
        </motion.button>
      </div>

      {isInitialLoad ? (
        <div className="glass-card p-5" aria-busy="true">
          <SkeletonRows rows={4} className="h-16 rounded-2xl" gap="gap-3" />
        </div>
      ) : analyses.length === 0 ? (
        <div className="glass-card p-10 text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-surface-800 border border-slate-700 mx-auto flex items-center justify-center text-slate-500">
            <Zap size={22} aria-hidden="true" />
          </div>
          <p className="text-sm font-semibold text-slate-200">No analysis runs yet</p>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Head over to the Playground to ask questions against your indexed documents.
          </p>
          <motion.button
            as={Link}
            to="/playground"
            whileHover={{ scale: 1.02, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: pressTransition }}
            className="btn-primary inline-flex mt-2"
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            Start First Analysis
          </motion.button>
        </div>
      ) : (
        <div className="glass-card divide-y divide-slate-800/80 overflow-hidden">
          {analyses.slice(0, 5).map((a, idx) => (
            <motion.div
              key={a.id}
              initial={reduced ? { opacity: 1 } : { opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ ...springTransition, delay: idx * 0.04 }}
              className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-surface-800/30 transition-colors group"
            >
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex items-center gap-2.5">
                  <span className="text-xs font-mono text-cyan-400 bg-cyan-950/50 border border-cyan-800/50 px-2 py-0.5 rounded">
                    Query
                  </span>
                  <h4 className="text-sm font-semibold text-slate-200 truncate group-hover:text-primary-300 transition-colors">
                    {a.query}
                  </h4>
                </div>

                <p className="text-xs text-slate-300 line-clamp-1 pl-1 font-normal">
                  {cleanSnippet(a.answer) || (a.status === 'abstained' ? 'System abstained due to insufficient verified evidence.' : 'Analysis in progress...')}
                </p>

                <div className="flex items-center gap-4 text-[11px] font-mono text-slate-500 pt-1 pl-1">
                  <span className="flex items-center gap-1">
                    <Clock size={11} aria-hidden="true" /> {formatDistanceToNow(new Date(a.created_at))} ago
                  </span>
                  {a.reliability?.claims_count !== undefined && (
                    <span>{a.reliability.claims_count} claims verified</span>
                  )}
                </div>
              </div>

              <div className="shrink-0 flex items-center gap-3">
                <ReliabilityBadge
                  score={a.reliability?.score}
                  status={a.reliability?.status}
                  size="sm"
                />
                <motion.button
                  as={Link}
                  to="/playground"
                  whileHover={{ scale: 1.05, transition: springTransition }}
                  whileTap={{ scale: 0.95, transition: pressTransition }}
                  className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-800 border border-slate-800 transition-colors"
                  title="Inspect in Playground"
                  style={{ minHeight: '44px', minWidth: '44px' }}
                >
                  <ArrowRight size={15} aria-hidden="true" />
                </motion.button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  )
}