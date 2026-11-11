import { useMemo } from 'react'
import { motion } from 'motion/react'
import { Activity } from 'lucide-react'
import { useReducedMotion } from 'motion/react'
import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, Tooltip, ReferenceLine
} from 'recharts'
import { format } from 'date-fns'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

/**
 * ReliabilityChart - Reliability progression area chart
 * Called by: DashboardPage.jsx
 * No existing file serves this purpose - extracted from DashboardPage
 * Reads/writes: Receives analyses, historyWindow, setHistoryWindow as props
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function ReliabilityChart({ analyses, historyWindow, setHistoryWindow }) {
  const reduced = useReducedMotion()
  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  const timelineData = useMemo(() => {
    if (!analyses || !analyses.length) return []

    const limit = historyWindow === 'all' ? analyses.length : Number(historyWindow)
    const chronologicalSlice = [...analyses].slice(0, limit).reverse()

    return chronologicalSlice.map((a, idx) => {
      const scoreValue = a.reliability?.score != null
        ? Math.round(a.reliability.score * 100)
        : (a.status === 'completed' ? 100 : 0)

      const createdDate = a.created_at ? new Date(a.created_at) : new Date()

      return {
        id: a.id,
        runLabel: `#${idx + 1}`,
        time: format(createdDate, 'HH:mm'),
        fullTime: format(createdDate, 'MMM dd, HH:mm:ss'),
        score: scoreValue,
        threshold: 75,
        status: a.reliability?.status || (scoreValue >= 75 ? 'TRUSTED' : (scoreValue > 0 ? 'UNCERTAIN' : 'FAILED')),
        query: a.query || 'Untitled Analysis',
        shortQuery: (a.query || '').length > 30 ? (a.query || '').slice(0, 30) + '…' : (a.query || 'Untitled Analysis'),
        statusRaw: a.status,
      }
    })
  }, [analyses, historyWindow])

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="lg:col-span-2 glass-card p-6 flex flex-col justify-between"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="font-bold text-white text-base flex items-center gap-2">
            <Activity size={16} className="text-cyan-400" aria-hidden="true" />
            Reliability Progression Curve
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Chronological execution history trajectory vs. safety threshold (75%)</p>
        </div>

        {/* History Window Filter Pills */}
        <div className="flex items-center gap-1.5 bg-surface-950 p-1 rounded-xl border border-slate-800 text-[11px] font-mono shrink-0">
          <motion.button
            type="button"
            onClick={() => setHistoryWindow('10')}
            whileHover={{ scale: 1.02, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: pressTransition }}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              historyWindow === '10'
                ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800/60 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            Last 10
          </motion.button>
          <motion.button
            type="button"
            onClick={() => setHistoryWindow('20')}
            whileHover={{ scale: 1.02, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: pressTransition }}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              historyWindow === '20'
                ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800/60 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            Last 20
          </motion.button>
          <motion.button
            type="button"
            onClick={() => setHistoryWindow('all')}
            whileHover={{ scale: 1.02, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: pressTransition }}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              historyWindow === 'all'
                ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800/60 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            All ({analyses.length})
          </motion.button>
        </div>
      </div>

      {timelineData.length === 0 ? (
        <div className="h-64 w-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl bg-surface-900/40">
          <Activity size={24} className="text-slate-600 mb-2" aria-hidden="true" />
          <p className="text-xs text-slate-300 font-medium">No reliability analyses recorded yet</p>
          <p className="text-[11px] text-slate-500 mt-1 max-w-sm">
            Run an analysis in the Playground to generate telemetry progression and claim audit benchmarks.
          </p>
        </div>
      ) : (
        <div className="h-64 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timelineData} margin={{ top: 15, right: 15, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="runLabel"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
              />
              <YAxis
                stroke="#64748b"
                fontSize={11}
                domain={[0, 100]}
                ticks={[0, 25, 50, 75, 100]}
                tickLine={false}
              />
              <ReferenceLine
                y={75}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                label={{
                  value: 'Safety Threshold (75%)',
                  position: 'insideTopRight',
                  fill: '#f59e0b',
                  fontSize: 10,
                  fontFamily: 'monospace',
                }}
              />
              <Tooltip content={<CustomTimelineTooltip />} />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#06b6d4"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#scoreGradient)"
                dot={{ fill: '#06b6d4', stroke: '#080c16', strokeWidth: 2, r: 4 }}
                activeDot={{ fill: '#38bdf8', stroke: '#ffffff', strokeWidth: 2, r: 6 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  )
}

function CustomTimelineTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const data = payload[0].payload
  const isTrusted = data.score >= 75
  const isFailed = data.score === 0 || data.status === 'FAILED'

  return (
    <div className="rounded-xl border border-slate-700/80 bg-surface-950/95 p-3.5 backdrop-blur-xl shadow-2xl space-y-2 max-w-xs font-sans text-xs">
      <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-2">
        <span className="font-mono text-cyan-300 font-bold text-[11px]">
          {data.runLabel} &bull; {data.time}
        </span>
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
            isTrusted
              ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
              : isFailed
                ? 'bg-red-950/80 text-red-300 border border-red-800/60'
                : 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
          }`}
        >
          {data.status}
        </span>
      </div>

      <div>
        <p className="text-[11px] text-slate-300 font-mono line-clamp-2 leading-relaxed">
          &ldquo;{data.query}&rdquo;
        </p>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px]">
        <span className="text-slate-400">Reliability Score:</span>
        <div className="flex items-baseline gap-1.5">
          <span
            className={`font-mono font-bold text-sm ${
              data.score >= 75 ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            {data.score}%
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            ({data.score >= 75 ? 'Passed' : 'Under 75%'})
          </span>
        </div>
      </div>

      <div className="text-[10px] text-slate-500 font-mono">
        {data.fullTime}
      </div>
    </div>
  )
}