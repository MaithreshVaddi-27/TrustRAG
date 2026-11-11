import { useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { PIPELINE_STAGES, PIPELINE_OUTPUT } from './landingData'

/**
 * PipelineDiagram — the signature technical visualisation.
 *
 * Six stages of the closed loop drawn as linework: a hairline runs the
 * chain, each stage is a node on it, and a single sweep travels the chain
 * once when the diagram enters the viewport. That sweep is the one authored
 * motion on the page — it explains what the pipeline does instead of
 * decorating it.
 */
export default function PipelineDiagram() {
  const containerRef = useRef(null)
  const [swept, setSwept] = useState(false)

  useEffect(() => {
    const node = containerRef.current
    if (!node || swept) return undefined
    if (typeof IntersectionObserver === 'undefined') {
      setSwept(true)
      return undefined
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return
        setSwept(true)
        observer.disconnect()
      },
      { threshold: 0.4 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [swept])

  return (
    <div
      className="lx-pipeline"
      ref={containerRef}
      data-swept={swept}
      aria-label="The six stages of the TrustRAG verification loop"
    >
      <div className="lx-pipeline__head">
        <h3 className="lx-h3">The closed loop</h3>
        <span className="lx-micro">6 stages · 1 verdict</span>
      </div>

      <div className="lx-pipeline__body">
        <div className="lx-chain">
          {PIPELINE_STAGES.map((stage, index) => {
            const Icon = stage.icon
            const isOutput = stage.id === 'ground'

            return (
              <div
                key={stage.id}
                className={clsx('lx-stage', isOutput && 'lx-stage--output')}
              >
                <span className="lx-stage__node">
                  <Icon strokeWidth={1.5} aria-hidden="true" />
                </span>
                <div className="lx-stage__body">
                  <p className="lx-stage__name">
                    {index + 1}. {stage.name}
                  </p>
                  <p className="lx-stage__desc">{stage.desc}</p>
                </div>
              </div>
            )
          })}

          <span className="lx-pipeline__sweep" aria-hidden="true" />
        </div>

        <div className="lx-pipeline__output">
          <span className="lx-micro">Outcomes</span>
          <div className="lx-pipeline__outcomes">
            {PIPELINE_OUTPUT.map((outcome) => (
              <span
                key={outcome.label}
                className={clsx('lx-micro', outcome.tone === 'alarm' && 'lx-signal')}
              >
                {outcome.label} — {outcome.value}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
