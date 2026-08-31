import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import { ChevronRight, Loader2 } from 'lucide-react'
import { EVENT_META } from './traceEvents'

/**
 * ExecutionTrace — clean, compact live SSE trace event feed as before,
 * with smooth auto-scroll and resilient word-wrapping.
 *
 * Props:
 *   events: [{ event, timestamp, data }]
 *   isLive: boolean  (show animated spinner & auto-scroll)
 */
export function ExecutionTrace({ events = [], isLive = false }) {
  const bottomRef = useRef(null)

  // Auto-scroll to newest event during live processing
  useEffect(() => {
    if (isLive && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [events.length, isLive])

  return (
    <div className="space-y-1 font-mono text-xs">
      {isLive && (
        <div className="flex items-center gap-2 text-primary-400 py-1.5 px-2 animate-pulse">
          <Loader2 size={12} className="animate-spin text-cyan-400" />
          <span className="text-cyan-300 font-sans text-xs font-medium">Pipeline running…</span>
        </div>
      )}

      {events.length === 0 && !isLive && (
        <p className="text-slate-500 text-sm font-sans py-4 text-center">No trace events yet.</p>
      )}

      {events.map((evt, i) => (
        <TraceEvent key={i} evt={evt} />
      ))}

      <div ref={bottomRef} className="h-1" />
    </div>
  )
}

function TraceEvent({ evt }) {
  const meta = EVENT_META[evt.event] ?? {
    icon: ChevronRight,
    color: 'text-slate-400',
    label: evt.event,
  }
  const Icon = meta.icon

  return (
    <div className="trace-event group">
      <Icon size={13} className={clsx('shrink-0 mt-0.5', meta.color)} />
      <div className="flex-1 min-w-0">
        <span className={clsx('font-semibold', meta.color)}>{meta.label}</span>
        {evt.data?.message && (
          <span className="text-slate-300 ml-2 font-sans break-words leading-relaxed">
            {evt.data.message}
          </span>
        )}
        {evt.data?.rewritten_query && (
          <span className="text-cyan-300 ml-2 font-mono text-[11px] block mt-0.5">
            ↳ Expanded: {evt.data.rewritten_query}
          </span>
        )}
        {evt.data?.latency_ms && (
          <span className="text-slate-500 ml-2 font-mono">({evt.data.latency_ms}ms)</span>
        )}
      </div>
      <span className="text-slate-500 shrink-0 text-[10px] opacity-0 group-hover:opacity-100 transition-opacity ml-2">
        {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ''}
      </span>
    </div>
  )
}

/**
 * RecoveryTimeline — shows recovery attempts in sequence.
 */
export function RecoveryTimeline({ recoveryRuns = [] }) {
  if (recoveryRuns.length === 0) return null

  return (
    <div className="space-y-3">
      <p className="section-heading">Recovery Timeline</p>
      {recoveryRuns.map((run, i) => (
        <div key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div
              className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border',
                run.success
                  ? 'border-green-600 bg-green-900/40 text-green-400'
                  : 'border-red-600 bg-red-900/40 text-red-400'
              )}
            >
              {i + 1}
            </div>
            {i < recoveryRuns.length - 1 && <div className="w-px h-full bg-slate-700 my-1" />}
          </div>
          <div className="pb-4 flex-1">
            <p className="text-sm font-medium text-slate-200">{run.strategy}</p>
            <p className="text-xs text-slate-400 mt-0.5 break-words">{run.reason}</p>
            {run.result && (
              <p className={clsx('text-xs mt-1 break-words', run.success ? 'text-green-400' : 'text-red-400')}>
                {run.result}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
