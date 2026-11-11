import { ShieldCheck } from 'lucide-react'
import VerdictBarChart from '@/components/charts/VerdictBarChart'
import { VERDICT_COLORS } from '@/lib/chartTheme'

/**
 * ClaimDistributionChart — how the audited claims broke down.
 *
 * A ranked bar, not a pie and not a card with three coloured boxes. One
 * accent: supported is Chrome Silver, neutral is a quiet step, and only
 * contradicted carries crimson.
 */
export function ClaimDistributionChart({ stats }) {
  const series = [
    { name: 'Supported', count: stats.supportedClaims, color: VERDICT_COLORS.supported },
    { name: 'Neutral', count: stats.neutralClaims, color: VERDICT_COLORS.neutral },
    { name: 'Contradicted', count: stats.contradictedClaims, color: VERDICT_COLORS.contradicted },
  ]

  const hasClaims = stats.totalClaimsCount > 0

  return (
    <section className="lx-panel-block" aria-labelledby="claim-audit-heading">
      <div className="lx-panel-block__head">
        <h2 id="claim-audit-heading" className="lx-panel-block__title">
          Claim verification audit
        </h2>
        <span className="lx-micro">{stats.totalClaimsCount} claims evaluated</span>
      </div>

      <div className="lx-panel-block__body">
        {hasClaims ? (
          <VerdictBarChart data={series} />
        ) : (
          <div className="lx-empty">
            <ShieldCheck size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            <p className="lx-empty__title">No claims decomposed yet</p>
            <p className="lx-empty__body">
              Run a query in the playground to extract and verify atomic assertions.
            </p>
          </div>
        )}
      </div>

      {hasClaims && (
        <div className="lx-panel-block__foot">
          <dl className="lx-deflist">
            <div className="lx-deflist__row">
              <dt className="lx-deflist__key">Supported</dt>
              <dd className="lx-deflist__value">
                {stats.supportedClaims} · {stats.supportedRate}%
              </dd>
            </div>
            <div className="lx-deflist__row">
              <dt className="lx-deflist__key">Neutral</dt>
              <dd className="lx-deflist__value">{stats.neutralClaims}</dd>
            </div>
            <div className="lx-deflist__row">
              <dt className="lx-deflist__key">Contradicted</dt>
              <dd
                className="lx-deflist__value"
                style={{ color: 'var(--color-crimson-300)' }}
              >
                {stats.contradictedClaims}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </section>
  )
}
