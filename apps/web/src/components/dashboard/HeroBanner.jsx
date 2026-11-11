import { Link } from 'react-router-dom'
import { Database, Zap, Activity } from 'lucide-react'

/**
 * HeroBanner — the dashboard masthead.
 *
 * The engine readout is a live signal, so it carries the Laser Crimson dot.
 * The heading is the display face; the two actions are the only colour on
 * the panel and they are plain surfaces, not gradients.
 */
export function HeroBanner() {
  return (
    <section className="rounded-[var(--radius-panel)] border border-[color:var(--rule)] bg-surface-900 p-6 sm:p-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-3">
          <p className="lx-telemetry__item">
            <span className="lx-dot lx-dot--live" aria-hidden="true" />
            <Activity size={12} strokeWidth={1.5} aria-hidden="true" />
            <strong>Observability engine active</strong>
          </p>

          <h1 className="lx-h1">
            AI Reliability <span className="text-silver-500">Workbench</span>
          </h1>

          <p className="lx-body mt-3 max-w-2xl">
            Autonomous hallucination detection, atomic claim verification, and
            self-healing closed-loop RAG recovery powered by LangGraph.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <Link to="/knowledge-bases" className="lx-btn lx-btn--secondary">
            <Database size={15} strokeWidth={1.5} aria-hidden="true" />
            <span>Knowledge bases</span>
          </Link>

          <Link to="/playground" className="lx-btn lx-btn--primary">
            <Zap size={15} strokeWidth={1.5} aria-hidden="true" />
            <span>Run interactive analysis</span>
          </Link>
        </div>
      </div>
    </section>
  )
}
