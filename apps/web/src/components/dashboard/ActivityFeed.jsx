import { Link } from 'react-router-dom'
import { Clock, ArrowRight, Check, CircleSlash, CircleDashed } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'

/**
 * ActivityFeed — the execution history.
 *
 * A ruled list of records, not a stack of cards. Each row carries the
 * query, what the pipeline concluded, the collection it ran against, and
 * when it ran.
 *
 * Two badges, because they answer two different questions: the verdict
 * badge says how reliable the answer was, and the status says whether there
 * was an answer at all. An abstention scores zero, and without the status
 * badge that reads as "an unreliable answer" rather than "no answer".
 */

const STATUS = {
  completed: { label: 'Answered', Icon: Check, tone: 'text-silver-300' },
  abstained: { label: 'Abstained', Icon: CircleSlash, tone: 'text-crimson-300' },
  failed: { label: 'Failed', Icon: CircleSlash, tone: 'text-crimson-300' },
  outage: { label: 'Outage', Icon: CircleSlash, tone: 'text-crimson-300' },
  pending: { label: 'Queued', Icon: CircleDashed, tone: 'text-silver-400' },
  processing: { label: 'Running', Icon: CircleDashed, tone: 'text-silver-400' },
}

function cleanSnippet(text) {
  if (!text) return ''
  return text
    .replace(/[*_#`~[\]]/g, '')
    .replace(/-\s+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export function ActivityFeed({ analyses = [], kbNames = {} }) {
  return (
    <section aria-labelledby="activity-heading">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="activity-heading" className="lx-h2">
            Activity
          </h2>
          <p className="lx-body mt-2">
            Every analysis run, and what the verifier concluded.
          </p>
        </div>

        <Link to="/playground" className="lx-btn lx-btn--quiet">
          Open playground
          <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      </div>

      {analyses.length === 0 ? (
        <div className="lx-panel-block">
          <div className="lx-empty">
            <Clock size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            <p className="lx-empty__title">No analysis runs yet</p>
            <p className="lx-empty__body">
              Ask a question against an indexed collection and the pipeline
              will verify it against the evidence.
            </p>
            <Link to="/playground" className="lx-btn lx-btn--secondary">
              Start the first analysis
            </Link>
          </div>
        </div>
      ) : (
        <div className="lx-panel-block">
          <div className="lx-list">
            {analyses.slice(0, 8).map((analysis) => {
              const status = STATUS[analysis.status] ?? {
                label: analysis.status || 'Unknown',
                Icon: CircleDashed,
                tone: 'text-silver-400',
              }
              const StatusIcon = status.Icon

              return (
                <article key={analysis.id} className="lx-list__item">
                  <div className="lx-list__head">
                    <h3 className="lx-list__title truncate">{analysis.query}</h3>
                    <div className="flex shrink-0 items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1.5 text-[var(--size-micro)] ${status.tone}`}
                      >
                        <StatusIcon size={12} strokeWidth={1.75} aria-hidden="true" />
                        {status.label}
                      </span>
                      {/* A run that produced no answer scores zero because
                          there was no answer, not because the verifier
                          failed. The verdict badge only appears when there
                          is a verdict to report. */}
                      {analysis.status === 'completed' && (
                        <ReliabilityBadge
                          score={analysis.reliability?.score}
                          status={analysis.reliability?.status}
                          size="sm"
                        />
                      )}
                    </div>
                  </div>

                  <p className="lx-body-sm mt-1 line-clamp-1">
                    {cleanSnippet(analysis.answer) ||
                      (analysis.status === 'abstained'
                        ? 'The pipeline abstained: the retrieved segments did not support a verified answer.'
                        : 'No answer was emitted.')}
                  </p>

                  <div className="lx-list__meta">
                    <span className="inline-flex items-center gap-1">
                      <Clock size={11} strokeWidth={1.5} aria-hidden="true" />
                      {formatDistanceToNow(new Date(analysis.created_at))} ago
                    </span>

                    {kbNames[analysis.knowledge_base_id] && (
                      <span>{kbNames[analysis.knowledge_base_id]}</span>
                    )}

                    {analysis.reliability?.claims_count !== undefined && (
                      <span>{analysis.reliability.claims_count} claims verified</span>
                    )}

                    <Link to={`/traces/${analysis.id}`} className="lx-inline-action">
                      View trace
                      <ArrowRight size={11} strokeWidth={1.5} aria-hidden="true" />
                    </Link>
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}
