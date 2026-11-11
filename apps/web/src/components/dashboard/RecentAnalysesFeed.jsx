import { Link } from 'react-router-dom'
import { Clock, ArrowRight } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { SkeletonRows } from '@/components/workbench/Skeleton'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'

/**
 * RecentAnalysesFeed — the execution history.
 *
 * A ruled list of records, not a stack of cards. Each row carries the
 * query, the answer snippet, when it ran, and its reliability band.
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
  return (
    <section aria-labelledby="recent-analyses-heading">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
        <div>
          <h2 id="recent-analyses-heading" className="lx-h2">
            Recent analysis traces
          </h2>
          <p className="lx-body mt-2">
            Execution history, grounded answers, and verification logs.
          </p>
        </div>

        <Link to="/playground" className="lx-btn lx-btn--quiet">
          Open playground
          <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      </div>

      {isInitialLoad ? (
        <div className="lx-panel-block p-5" aria-busy="true">
          <SkeletonRows rows={4} className="h-16 rounded-xl" gap="gap-3" />
        </div>
      ) : analyses.length === 0 ? (
        <div className="lx-panel-block">
          <div className="lx-empty">
            <Clock size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            <p className="lx-empty__title">No analysis runs yet</p>
            <p className="lx-empty__body">
              Ask a question against your indexed documents in the playground.
            </p>
            <Link to="/playground" className="lx-btn lx-btn--primary">
              Start first analysis
            </Link>
          </div>
        </div>
      ) : (
        <div className="lx-panel-block">
          <div className="lx-list">
            {analyses.slice(0, 5).map((a) => (
              <article key={a.id} className="lx-list__item">
                <div className="lx-list__head">
                  <h3 className="lx-list__title truncate">{a.query}</h3>
                  <ReliabilityBadge
                    score={a.reliability?.score}
                    status={a.reliability?.status}
                    size="sm"
                  />
                </div>

                <p className="lx-body-sm mt-1 line-clamp-1">
                  {cleanSnippet(a.answer) ||
                    (a.status === 'abstained'
                      ? 'System abstained due to insufficient verified evidence.'
                      : 'Analysis in progress…')}
                </p>

                <div className="lx-list__meta">
                  <span className="inline-flex items-center gap-1">
                    <Clock size={11} strokeWidth={1.5} aria-hidden="true" />
                    {formatDistanceToNow(new Date(a.created_at))} ago
                  </span>
                  {a.reliability?.claims_count !== undefined && (
                    <span>{a.reliability.claims_count} claims verified</span>
                  )}
                  <Link
                    to="/playground"
                    className="lx-inline-action"
                  >
                    Inspect
                    <ArrowRight size={11} strokeWidth={1.5} aria-hidden="true" />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
