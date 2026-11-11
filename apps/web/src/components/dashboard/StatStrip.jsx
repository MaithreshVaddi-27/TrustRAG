import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'

/**
 * StatStrip — the dashboard's figures.
 *
 * Not four cards. Four figures in one ruled strip, because they are peers:
 * the same size, the same weight, the same rhythm, separated by hairlines
 * rather than boxes. A row of equal cards is the template default, and it
 * makes the reader hunt for the number that matters.
 *
 * Every figure carries a second line that is a real measurement. A label
 * that restates the label above it — "Evidence-linked" under "Analyses
 * executed" — is decoration, and decoration in a metrics strip is noise.
 */
const FIGURES = [
  { id: 'knowledge-bases', label: 'Knowledge bases', to: '/knowledge-bases' },
  { id: 'analyses', label: 'Analyses executed', to: '/playground' },
  { id: 'reliability', label: 'Mean reliability', to: null },
  { id: 'claims', label: 'Claims decomposed', to: '/claims' },
]

export function StatStrip({ stats }) {
  const { figures } = stats

  return (
    <div className="lx-statstrip">
      {FIGURES.map(({ id, label, to }) => {
        const figure = figures[id]
        const body = (
          <>
            <span className="lx-stat__label">{label}</span>
            <span
              className={`lx-stat__value${figure.alarm ? ' lx-stat__value--alarm' : ''}`}
            >
              {figure.value}
            </span>
            <span className="lx-stat__meta">{figure.meta}</span>
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
