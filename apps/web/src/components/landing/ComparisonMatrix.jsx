import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { COMPARISON_FILTERS, COMPARISON_ROWS } from './data/comparison'

/**
 * ComparisonMatrix — a specification table.
 *
 * Three columns separated by hairlines. On narrow screens each row stacks
 * and every column carries its own label, so the comparison survives 320px
 * without turning into a different design.
 */
export default function ComparisonMatrix() {
  const [filter, setFilter] = useState('all')

  const rows =
    filter === 'all'
      ? COMPARISON_ROWS
      : COMPARISON_ROWS.filter((row) => row.category === filter)

  return (
    <>
      <div className="lx-matrix__filter" role="group" aria-label="Filter comparisons">
        {COMPARISON_FILTERS.map((option) => (
          <button
            key={option.id}
            type="button"
            className="lx-tab"
            aria-pressed={option.id === filter}
            onClick={() => setFilter(option.id)}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="lx-matrix">
        <div className="lx-matrix__head" aria-hidden="true">
          <span className="lx-micro">Capability</span>
          <span className="lx-micro">Standard single-pass RAG</span>
          <span className="lx-micro">TrustRAG</span>
        </div>

        {rows.map((row) => (
          <div key={row.title} className="lx-matrix__row">
            <div>
              <h3 className="lx-matrix__name">{row.title}</h3>
              <p className="lx-matrix__subtitle">{row.subtitle}</p>
            </div>

            <div>
              <span className="lx-matrix__col-label">Standard single-pass RAG</span>
              <p className="lx-matrix__cell">{row.naive}</p>
            </div>

            <div className="lx-matrix__ours">
              <span className="lx-matrix__col-label">TrustRAG</span>
              <p className="lx-matrix__cell lx-matrix__cell--ours">{row.ours}</p>
              <p className="lx-matrix__impact">
                <ArrowRight size={12} strokeWidth={1.5} aria-hidden="true" />
                <span>{row.impact}</span>
              </p>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
