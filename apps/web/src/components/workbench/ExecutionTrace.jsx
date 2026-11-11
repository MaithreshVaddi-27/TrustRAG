import { useEffect, useMemo, useRef } from 'react'
import { clsx } from 'clsx'
import { ChevronRight, Loader2 } from 'lucide-react'
import { EVENT_META, compactTraceEvents, displayMessage } from './traceEvents'

/**
 * ExecutionTrace — the live event feed.
 *
 * A monospace log: one line per pipeline moment, hairline rules between
 * entries, the timestamp on the right. It auto-scrolls while the stream is
 * live and stops the moment the run ends, so a finished trace can be read
 * from the top.
 */
export function ExecutionTrace({ events = [], isLive = false }) {
  const bottomRef = useRef(null)
  // Collapse backend lifecycle duplicates so each pipeline moment reads once.
  const visibleEvents = useMemo(() => compactTraceEvents(events), [events])

  useEffect(() => {
    if (isLive && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [visibleEvents.length, isLive])

  return (
    <div className="lx-trace" aria-live="polite" aria-atomic="false">
      {isLive && (
        <div className="flex items-center gap-2 py-2">
          <Loader2
            size={12}
            strokeWidth={1.75}
            className="animate-spin text-silver-500"
            aria-hidden="true"
          />
          <span className="font-sans text-[var(--size-body-sm)] text-silver-400">
            Pipeline running…
          </span>
        </div>
      )}

      {visibleEvents.length === 0 && !isLive && (
        <p className="py-4 text-center font-sans text-[var(--size-body-sm)] text-silver-500">
          No trace events yet.
        </p>
      )}

      {visibleEvents.map((event, index) => (
        <TraceEvent key={`${event.event}-${event.timestamp ?? index}`} evt={event} />
      ))}

      <div ref={bottomRef} className="h-1" />
    </div>
  )
}

function TraceEvent({ evt }) {
  const meta = EVENT_META[evt.event] ?? {
    icon: ChevronRight,
    color: 'text-silver-400',
    label: evt.event,
  }
  const Icon = meta.icon
  // The backend sometimes restates the label ("retrieval completed
  // successfully") — render the message only when it adds information.
  const message = displayMessage(evt.event, evt.data?.message)

  return (
    <div className="lx-trace__event">
      <Icon size={13} className={clsx('lx-trace__icon', meta.color)} aria-hidden="true" />
      <div className="lx-trace__body">
        <span className={clsx('lx-trace__label', meta.color)}>{meta.label}</span>

        {message && <span className="lx-trace__message">{message}</span>}

        {evt.data?.rewritten_query && (
          <span className="lx-trace__detail">
            Expanded: {evt.data.rewritten_query}
          </span>
        )}

        {evt.data?.latency_ms && (
          <span className="lx-trace__detail">{evt.data.latency_ms}ms</span>
        )}
      </div>

      <span className="lx-trace__time">
        {evt.timestamp
          ? new Date(evt.timestamp).toLocaleTimeString('en-GB', { hour12: false })
          : ''}
      </span>
    </div>
  )
}

/**
 * RecoveryTimeline — the self-healing attempts, in sequence.
 *
 * Each attempt is a row: the strategy, why it fired, and what it changed.
 */
export function RecoveryTimeline({ recoveryRuns = [] }) {
  if (recoveryRuns.length === 0) return null

  return (
    <section className="lx-panel-block">
      <div className="lx-panel-block__head">
        <h3 className="lx-panel-block__title">Recovery timeline</h3>
        <span className="lx-micro">{recoveryRuns.length} attempts</span>
      </div>

      <div className="lx-panel-block__body">
        <dl className="lx-list">
          {recoveryRuns.map((run, index) => (
            <div key={index} className="lx-list__item">
              <div className="lx-list__head">
                <dt className="lx-list__title">
                  <span className="lx-layer__index mr-2">{String(index + 1).padStart(2, '0')}</span>
                  {run.strategy}
                </dt>
              </div>
              <dd className="lx-body-sm mt-1.5 max-w-[68ch]">
                {run.reason}
                {run.result && (
                  <span className="mt-1 block text-silver-500">{run.result}</span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
