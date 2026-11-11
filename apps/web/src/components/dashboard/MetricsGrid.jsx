import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'

/**
 * MetricsGrid — the dashboard's figures.
 *
 * Not four cards. Four figures in one ruled strip, because they are peers:
 * the same size, the same weight, the same rhythm, separated by hairlines
 * rather than boxes. A row of equal cards is the template default, and it
 * makes the reader hunt for the number that matters.
 *
 * Each cell links through to the surface that owns the figure, so the
 * number is a way in rather than a decoration.
 */
const FIGURES = [
  { id: 'knowledge-bases', label: 'Knowledge bases', to: '/knowledge-bases' },
  { id: 'analyses', label: 'Analyses executed', to: '/playground' },
  { id: 'reliability', label: 'Mean reliability', to: null },
  { id: 'claims', label: 'Claims decomposed', to: '/claims' },
]

export function MetricsGrid({ stats, kbs, analyses, claims, conflicts }) {
  const values = {
    'knowledge-bases': {
      value: kbs.length,
      meta: `${stats.totalDocs} documents`,
    },
    analyses: {
      value: analyses.length,
      meta: 'Evidence-linked',
    },
    reliability: {
      value: stats.avgReliabilityDisplay,
      meta: 'Threshold 75%',
      // A mean below the threshold is the one figure on this screen that is
      // an alarm, so it is the one figure that carries crimson.
      alarm: stats.avgReliabilityDisplay !== '--' && Number(stats.avgReliability) < 75,
    },
    claims: {
      value: stats.totalClaimsCount || claims.length,
      meta: conflicts?.length
        ? `${stats.supportedClaims} verified · ${conflicts.length} flagged`
        : `${stats.supportedClaims} verified`,
      alarm: Boolean(conflicts?.length),
    },
  }

  return (
    <div className="lx-statstrip">
      {FIGURES.map(({ id, label, to }) => {
        const { value, meta, alarm } = values[id]

        const body = (
          <>
            <span className="lx-stat__label">{label}</span>
            <span className={`lx-stat__value${alarm ? ' lx-stat__value--alarm' : ''}`}>
              {value}
            </span>
            <span className="lx-stat__meta">{meta}</span>
          </>
        )

        if (!to) {
          return (
            <div key={id} className="lx-stat">
              {body}
            </div>
          )
        }

        return (
          <Link key={id} to={to} className="lx-stat group relative block">
            {body}
            <ArrowUpRight
              size={13}
              strokeWidth={1.5}
              aria-hidden="true"
              className="absolute right-4 top-4 text-silver-700 transition-colors group-hover:text-silver-300"
            />
          </Link>
        )
      })}
    </div>
  )
}
