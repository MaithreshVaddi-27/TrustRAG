import { useMemo } from 'react'
import { Activity } from 'lucide-react'
import ReliabilityAreaChart from '@/components/charts/ReliabilityAreaChart'
import { format } from 'date-fns'

/**
 * ReliabilityChart — the reliability trajectory against the safety threshold.
 *
 * One accent: the reliability line is Chrome Silver. The threshold is a
 * hairline, not a coloured band. A point that fell below the threshold is
 * the only thing on the chart that carries crimson, because that is the one
 * event on this chart that mattered.
 *
 * The series is the reliability of answers that were actually delivered. A
 * run that abstained scores zero because there was no answer, and plotting
 * it here would say the system produced a bad answer when it produced no
 * answer at all.
 */
const WINDOWS = [
  { id: '10', label: 'Last 10' },
  { id: '20', label: 'Last 20' },
  { id: 'all', label: 'All' },
]

export function ReliabilityChart({ analyses, historyWindow, setHistoryWindow }) {
  const answered = useMemo(
    () =>
      (analyses || []).filter(
        (analysis) =>
          analysis.status === 'completed' &&
          analysis.reliability?.score !== undefined &&
          analysis.reliability?.score !== null,
      ),
    [analyses],
  )

  const timelineData = useMemo(() => {
    if (!answered.length) return []

    const limit = historyWindow === 'all' ? answered.length : Number(historyWindow)
    const chronologicalSlice = [...answered].slice(0, limit).reverse()

    return chronologicalSlice.map((analysis, index) => {
      const scoreValue = Math.round(analysis.reliability.score * 100)
      const createdDate = analysis.created_at
        ? new Date(analysis.created_at)
        : new Date()

      return {
        id: analysis.id,
        runLabel: `#${index + 1}`,
        time: format(createdDate, 'HH:mm'),
        fullTime: format(createdDate, 'MMM dd, HH:mm:ss'),
        score: scoreValue,
        threshold: 75,
        status:
          analysis.reliability.status ||
          (scoreValue >= 75 ? 'TRUSTED' : scoreValue > 0 ? 'UNCERTAIN' : 'FAILED'),
        query: analysis.query || 'Untitled analysis',
      }
    })
  }, [answered, historyWindow])

  const excluded = (analyses?.length ?? 0) - answered.length

  return (
    <section className="lx-panel-block" aria-labelledby="reliability-heading">
      <div className="lx-panel-block__head">
        <div>
          <h2 id="reliability-heading" className="lx-panel-block__title">
            Reliability progression
          </h2>
          <p className="lx-micro mt-1">
            Delivered answers against the 75% safety threshold
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
              {window.id === 'all' && answered.length ? ` (${answered.length})` : ''}
            </button>
          ))}
        </div>
      </div>

      <div className="lx-panel-block__body">
        {timelineData.length ? (
          <ReliabilityAreaChart data={timelineData} threshold={75} />
        ) : (
          <div className="lx-empty">
            <Activity size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            <p className="lx-empty__title">No delivered answers yet</p>
            <p className="lx-empty__body">
              {excluded > 0
                ? `${excluded} ${excluded === 1 ? 'run' : 'runs'} produced no verified answer, so there is nothing to plot. The curve starts when the pipeline returns an answer.`
                : 'Run an analysis in the playground to start the reliability progression curve.'}
            </p>
          </div>
        )}
      </div>

      {excluded > 0 && timelineData.length > 0 && (
        <div className="lx-panel-block__foot">
          <p className="lx-micro">
            {excluded} {excluded === 1 ? 'run' : 'runs'} produced no verified answer
            and are not plotted.
          </p>
        </div>
      )}
    </section>
  )
}
