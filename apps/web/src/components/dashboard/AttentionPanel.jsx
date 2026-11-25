import { Link } from 'react-router-dom'
import { ShieldCheck, ShieldAlert, CircleSlash, ArrowRight } from 'lucide-react'
import VerificationSeal from '@/components/landing/VerificationSeal'

/**
 * AttentionPanel — what the reliability instrument is reporting.
 *
 * A reliability dashboard's first job is to say what went wrong. This
 * panel lists the three things that can go wrong — a contradicted claim, a
 * source conflict, and a run that could not produce a verified answer —
 * and says so plainly when there are none.
 *
 * When there is nothing to report it says so in one line. Silence would be
 * ambiguous; a green tick would be decoration.
 */
export function AttentionPanel({ conflicts = [], contradictedClaims = 0, failedRuns = 0 }) {
  const total = conflicts.length + contradictedClaims + failedRuns

  if (total === 0) {
    return (
      <section className="lx-panel-block" aria-labelledby="attention-heading">
        <div className="lx-panel-block__head">
          <h2 id="attention-heading" className="lx-panel-block__title flex items-center gap-2">
            <ShieldCheck size={15} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
            Needs attention
          </h2>
          <VerificationSeal tone="silver" size={14} />
        </div>
        <div className="lx-panel-block__body">
          <p className="lx-body-sm">
            No contradicted claims, no source conflicts, and every run produced
            a verified answer.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="lx-panel-block" aria-labelledby="attention-heading">
      <div className="lx-panel-block__head">
        <h2 id="attention-heading" className="lx-panel-block__title flex items-center gap-2">
          <ShieldAlert size={15} strokeWidth={1.5} aria-hidden="true" className="text-crimson-400" />
          Needs attention
        </h2>
        <div className="flex items-center gap-2">
          <VerificationSeal tone="crimson" size={14} />
          <span className="lx-chip lx-chip--alarm">
            {total} {total === 1 ? 'item' : 'items'}
          </span>
        </div>
      </div>

      <div className="lx-list">
        {conflicts.map((conflict) => (
          <article key={conflict.id} className="lx-list__item">
            <div className="lx-list__head">
              <h3 className="lx-list__title flex items-center gap-2">
                <ShieldAlert
                  size={14}
                  strokeWidth={1.75}
                  className="shrink-0 text-crimson-400"
                  aria-hidden="true"
                />
                {conflict.title || conflict.type || 'Source conflict'}
              </h3>
              <span className="lx-chip lx-chip--alarm">{conflict.type || 'conflict'}</span>
            </div>

            {conflict.claim && (
              <blockquote className="lx-body mt-3 max-w-[70ch] border-l border-[color:var(--rule-strong)] pl-3">
                {conflict.claim}
              </blockquote>
            )}

            {conflict.explanation && (
              <p className="lx-body-sm mt-3 max-w-[70ch]">{conflict.explanation}</p>
            )}

            <div className="lx-list__meta">
              <Link to="/conflicts" className="lx-inline-action">
                Inspect conflict
                <ArrowRight size={11} strokeWidth={1.5} aria-hidden="true" />
              </Link>
            </div>
          </article>
        ))}

        {contradictedClaims > 0 && (
          <article className="lx-list__item">
            <div className="lx-list__head">
              <h3 className="lx-list__title flex items-center gap-2">
                <ShieldAlert
                  size={14}
                  strokeWidth={1.75}
                  className="shrink-0 text-crimson-400"
                  aria-hidden="true"
                />
                {contradictedClaims} contradicted{' '}
                {contradictedClaims === 1 ? 'claim' : 'claims'}
              </h3>
            </div>

            <p className="lx-body-sm mt-2 max-w-[70ch]">
              The entailment model found assertions that conflict with the
              evidence they cite. Each one triggered a recovery attempt.
            </p>

            <div className="lx-list__meta">
              <Link to="/claims" className="lx-inline-action">
                Inspect the claims
                <ArrowRight size={11} strokeWidth={1.5} aria-hidden="true" />
              </Link>
            </div>
          </article>
        )}

        {failedRuns > 0 && (
          <article className="lx-list__item">
            <div className="lx-list__head">
              <h3 className="lx-list__title flex items-center gap-2">
                <CircleSlash
                  size={14}
                  strokeWidth={1.75}
                  className="shrink-0 text-crimson-400"
                  aria-hidden="true"
                />
                {failedRuns} {failedRuns === 1 ? 'run' : 'runs'} produced no verified answer
              </h3>
            </div>

            <p className="lx-body-sm mt-2 max-w-[70ch]">
              The pipeline abstained or failed. No ungrounded text was emitted,
              but no verified answer was returned either.
            </p>

            <div className="lx-list__meta">
              <Link to="/playground" className="lx-inline-action">
                Run another query
                <ArrowRight size={11} strokeWidth={1.5} aria-hidden="true" />
              </Link>
            </div>
          </article>
        )}
      </div>
    </section>
  )
}
