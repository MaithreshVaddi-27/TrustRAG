import { clsx } from 'clsx'
import {
  AlertTriangle, CheckCircle2, ChevronRight,
  Circle, Loader2, RefreshCw, XCircle,
} from 'lucide-react'

/**
 * ExecutionTrace — live SSE trace event feed.
 * Props:
 *   events: [{ event, timestamp, data }]
 *   isLive: boolean  (show animated spinner)
 */
export function ExecutionTrace({ events = [], isLive = false }) {
  return (
    <div className="space-y-1 font-mono text-xs">
      {isLive && (
        <div className="flex items-center gap-2 text-primary-400 py-2 animate-pulse">
          <Loader2 size={12} className="animate-spin" />
          <span>Analysis running…</span>
        </div>
      )}

      {events.length === 0 && !isLive && (
        <p className="text-slate-500 text-sm font-sans py-4 text-center">No trace events yet.</p>
      )}

      {events.map((evt, i) => (
        <TraceEvent key={i} evt={evt} />
      ))}
    </div>
  )
}

const EVENT_META = {
  'analysis.started':      { icon: Circle,        color: 'text-primary-400', label: 'Analysis started' },
  'retrieval.completed':   { icon: CheckCircle2,  color: 'text-blue-400',    label: 'Retrieval completed' },
  'integrity.failed':      { icon: AlertTriangle, color: 'text-amber-400',   label: 'Integrity check failed' },
  'generation.started':    { icon: Circle,        color: 'text-primary-400', label: 'Generation started' },
  'claims.started':        { icon: Circle,        color: 'text-indigo-400',  label: 'Claim verification started' },
  'claims.verified':       { icon: CheckCircle2,  color: 'text-indigo-400',  label: 'Claims verified' },
  'recovery.rewrite':      { icon: RefreshCw,     color: 'text-amber-400',   label: 'Recovery: query rewrite' },
  'recovery.re_retrieve':  { icon: RefreshCw,     color: 'text-amber-400',   label: 'Recovery: expanded retrieval' },
  'analysis.completed':    { icon: CheckCircle2,  color: 'text-green-400',   label: 'Analysis complete' },
  'analysis.abstained':    { icon: AlertTriangle, color: 'text-amber-400',   label: 'Abstained' },
  'analysis.failed':       { icon: XCircle,       color: 'text-red-400',     label: 'Analysis failed' },
}

function TraceEvent({ evt }) {
  const meta = EVENT_META[evt.event] ?? {
    icon: ChevronRight, color: 'text-slate-500', label: evt.event,
  }
  const Icon = meta.icon

  return (
    <div className="trace-event group">
      <Icon size={12} className={clsx('shrink-0 mt-0.5', meta.color)} />
      <div className="flex-1 min-w-0">
        <span className={clsx('font-semibold', meta.color)}>{meta.label}</span>
        {evt.data?.message && (
          <span className="text-slate-500 ml-2">{evt.data.message}</span>
        )}
        {evt.data?.latency_ms && (
          <span className="text-slate-600 ml-2">{evt.data.latency_ms}ms</span>
        )}
      </div>
      <span className="text-slate-600 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
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
            <div className={clsx(
              'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border',
              run.success
                ? 'border-green-600 bg-green-900/40 text-green-400'
                : 'border-red-600 bg-red-900/40 text-red-400'
            )}>
              {i + 1}
            </div>
            {i < recoveryRuns.length - 1 && (
              <div className="w-px h-full bg-slate-700 my-1" />
            )}
          </div>
          <div className="pb-4 flex-1">
            <p className="text-sm font-medium text-slate-200">{run.strategy}</p>
            <p className="text-xs text-slate-500 mt-0.5">{run.reason}</p>
            {run.result && (
              <p className={clsx('text-xs mt-1', run.success ? 'text-green-400' : 'text-red-400')}>
                {run.result}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
