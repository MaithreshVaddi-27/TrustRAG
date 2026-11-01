import { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import { clsx } from 'clsx'
import { RefreshCw, Activity, ShieldCheck } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { SPRING_SNAPPY } from '@/lib/motionConfig'

/**
 * ObservabilityBar - Live observability control bar
 * Called by: DashboardPage.jsx (line 268-320)
 * No existing file serves this purpose - extracted from DashboardPage
 * Reads/writes: localStorage not used, receives props from parent
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function ObservabilityBar({
  autoRefresh,
  setAutoRefresh,
  lastSync,
  setLastSync,
  isFetchingAnalyses,
  handleManualSync,
  analyses,
  claims,
}) {
  useEffect(() => {
    setLastSync(new Date())
  }, [analyses, claims, setLastSync])

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 rounded-2xl border border-cyan-500/30 bg-surface-900/80 backdrop-blur-xl shadow-lg shadow-cyan-950/20"
    >
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center">
          {autoRefresh ? (
            <>
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="absolute w-2 h-2 rounded-full bg-emerald-400" />
            </>
          ) : (
            <span className="w-2 h-2 rounded-full bg-slate-500" />
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold tracking-wider uppercase text-cyan-300">
            Live Observability Stream
          </span>
          <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
            autoRefresh
              ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60'
              : 'bg-surface-950 text-slate-400 border-slate-800'
          }`}>
            {autoRefresh ? 'Active Polling (5s)' : 'Paused'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
        <span>Synced {formatDistanceToNow(lastSync, { addSuffix: true })}</span>
        <button
          type="button"
          onClick={handleManualSync}
          disabled={isFetchingAnalyses}
          className="px-2.5 py-1.5 rounded-xl bg-surface-800 hover:bg-surface-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-sm"
          title="Force sync live state"
          aria-label="Force sync live state"
        >
          <RefreshCw size={12} className={isFetchingAnalyses ? 'animate-spin text-cyan-400' : 'text-slate-400'} />
          <span>Sync Now</span>
        </button>
        <button
          type="button"
          onClick={() => setAutoRefresh(prev => !prev)}
          className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all shadow-sm ${
            autoRefresh
              ? 'bg-emerald-950/50 border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/50'
              : 'bg-surface-800 border-slate-700 text-slate-300 hover:text-white'
          }`}
        >
          {autoRefresh ? 'Pause Stream' : 'Go Live'}
        </button>
      </div>
    </motion.div>
  )
}