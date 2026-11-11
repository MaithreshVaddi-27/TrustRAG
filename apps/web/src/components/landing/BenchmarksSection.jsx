import { useState } from 'react'
import { BENCHMARKS, BENCHMARK_TABS } from './landingData'

/**
 * BenchmarksSection — a ranked table with thin bars.
 *
 * One accent leads: the row that matters is Chrome Silver, and every other
 * row sits in a quiet step of the neutral ramp. Each table carries a
 * caption naming where the numbers came from.
 */
export default function BenchmarksSection() {
  const [activeId, setActiveId] = useState(BENCHMARK_TABS[0].id)
  const active = BENCHMARKS[activeId]

  return (
    <>
      <div className="lx-tabs" role="tablist" aria-label="Benchmark sets">
        {BENCHMARK_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`bench-tab-${tab.id}`}
            aria-selected={tab.id === active.id}
            aria-controls={`bench-panel-${tab.id}`}
            tabIndex={tab.id === active.id ? 0 : -1}
            className="lx-tab"
            onClick={() => setActiveId(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        className="lx-bench"
        role="tabpanel"
        id={`bench-panel-${active.id}`}
        aria-labelledby={`bench-tab-${active.id}`}
        tabIndex={0}
      >
        <div className="lx-bench__head">
          <h3 className="lx-h3">{active.title}</h3>
          <p className="lx-body-sm lx-bench__desc">{active.desc}</p>
        </div>

        {active.metrics.map((metric) => (
          <div
            key={metric.label}
            className={`lx-bench__row${metric.lead ? ' lx-bench__row--lead' : ''}`}
          >
            <span className="lx-bench__label">{metric.label}</span>
            <span className="lx-bench__value">
              {metric.value}
              {metric.suffix}
            </span>
            <span className="lx-bench__track" aria-hidden="true">
              <span className="lx-bench__fill" style={{ width: metric.width }} />
            </span>
            <span className="lx-bench__note">{metric.note}</span>
          </div>
        ))}

        <p className="lx-bench__caption">{active.note}</p>
      </div>
    </>
  )
}
