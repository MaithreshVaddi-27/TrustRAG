import { useMemo } from 'react'
import { Activity } from 'lucide-react'
import ReliabilityAreaChart from '@/components/charts/ReliabilityAreaChart'
import { CHART } from '@/lib/chartTheme'
import { format } from 'date-fns'

/**
 * ReliabilityChart — the reliability trajectory against the safety threshold.
 *
 * One accent: the reliability line is Chrome Silver. The threshold is a
 * hairline, not a coloured band. A point that fell below the threshold is
 * marked in crimson, because that is the one event on this chart that
 * mattered.
 */
const WINDOWS = [
  { id: '10', label: 'Last 10' },
  { id: '20', label: 'Last 20' },
  { id: 'all', label: 'All' },
]

export function ReliabilityChart({ analyses, historyWindow, setHistoryWindow }) {
  const timelineData = useMemo(() => {
    if (!analyses?.length) return []

    const limit = historyWindow === 'all' ? analyses.length : Number(historyWindow)
    const chronologicalSlice = [...analyses].slice(0, limit).reverse()

    return chronologicalSlice.map((analysis, index) => {
      const scoreValue =
        analysis.reliability?.score != null
          ? Math.round(analysis.reliability.score * 100)
          : analysis.status === 'completed'
            ? 100
            : 0

      const createdDate = analysis.created_at ? new Date(analysis.created_at) : new Date()

      return {
        id: analysis.id,
        runLabel: `#${index + 1}`,
        time: format(createdDate, 'HH:mm'),
        fullTime: format(createdDate, 'MMM dd, HH:mm:ss'),
        score: scoreValue,
        threshold: 75,
        status:
          analysis.reliability?.status ||
          (scoreValue >= 75 ? 'TRUSTED' : scoreValue > 0 ? 'UNCERTAIN' : 'FAILED'),
        query: analysis.query || 'Untitled analysis',
      }
    })
  }, [analyses, historyWindow])

  const hasData = timelineData.length > 0

  return (
    <section className="lx-panel-block" aria-labelledby="reliability-heading">
      <div className="lx-panel-block__head">
        <div>
          <h2 id="reliability-heading" className="lx-panel-block__title">
            Reliability progression
          </h2>
          <p className="lx-micro mt-1">
            Execution history against the {CHART.threshold ?? 75}% safety threshold
          </p>
        </div>

        <div className="lx-tabs" role="group" aria-label="History window">
          {WINDOWS.map((window) => (
            <button
              key={window.id}
              type="button"
              className="lx-tab"
              aria-pressed={historyWindow === window.id}
              onClick={() => setHistoryWindow(window.id)}
            >
              {window.label}
              {window.id === 'all' && analyses?.length ? ` (${analyses.length})` : ''}
            </button>
          ))}
        </div>
      </div>

      <div className="lx-panel-block__body">
        {hasData ? (
          <ReliabilityAreaChart data={timelineData} threshold={75} />
        ) : (
          <div className="lx-empty">
            <Activity size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            <p className="lx-empty__title">No reliability analyses recorded yet</p>
            <p className="lx-empty__body">
              Run an analysis in the playground to start the reliability
              progression curve.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
