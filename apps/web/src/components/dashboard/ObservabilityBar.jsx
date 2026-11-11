import { RefreshCw, Radio, Circle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

/**
 * ObservabilityBar — the dashboard's control row.
 *
 * A toolbar: what is live, when it last synced, and the two controls that
 * change that. The status is a crimson dot because the stream is genuinely
 * live; the label is quiet mono text rather than a coloured pill.
 */
export function ObservabilityBar({
  autoRefresh,
  setAutoRefresh,
  lastSync,
  isFetchingAnalyses,
  handleManualSync,
}) {
  return (
    <div className="lx-toolbar">
      <div className="lx-toolbar__group">
        <span className="lx-telemetry__item">
          {autoRefresh ? (
            <>
              <span className="lx-dot lx-dot--live" aria-hidden="true" />
              <Radio size={12} strokeWidth={1.5} aria-hidden="true" />
            </>
          ) : (
            <Circle size={10} strokeWidth={1.5} className="text-silver-500" aria-hidden="true" />
          )}
          <strong>Observability stream</strong>
        </span>

        <span className={`lx-chip${autoRefresh ? '' : ' lx-chip--quiet'}`}>
          {autoRefresh ? 'Active polling, 5s' : 'Paused'}
        </span>

        <span className="lx-micro">Synced {formatDistanceToNow(lastSync, { addSuffix: true })}</span>
      </div>

      <div className="lx-toolbar__group">
        <button
          type="button"
          onClick={handleManualSync}
          disabled={isFetchingAnalyses}
          className="lx-btn lx-btn--secondary"
          title="Force sync live state"
        >
          <RefreshCw
            size={13}
            strokeWidth={1.5}
            aria-hidden="true"
            className={isFetchingAnalyses ? 'animate-spin' : ''}
          />
          <span>Sync now</span>
        </button>

        <button
          type="button"
          onClick={() => setAutoRefresh((prev) => !prev)}
          className="lx-btn lx-btn--primary"
        >
          {autoRefresh ? 'Pause stream' : 'Go live'}
        </button>
      </div>
    </div>
  )
}
