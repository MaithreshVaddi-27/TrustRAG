import { useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { PIPELINE_STAGES, PIPELINE_OUTPUT } from './data/pipeline'

/**
 * PipelineDiagram — the signature technical visualisation.
 *
 * Six stages of the closed loop drawn as linework: a hairline runs the
 * chain, each stage is a node on it, and a single bright segment travels the
 * chain with the reader's scroll. Each stage activates as the segment
 * reaches it. The motion explains the pipeline instead of decorating it: it
 * is finite, tied to input, and holds its final state beyond the band.
 */
export default function PipelineDiagram() {
  const containerRef = useRef(null)
  const frameRef = useRef(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const node = containerRef.current
    if (!node) return undefined

    // Reduced motion gets the finished diagram, not a moving one.
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduce || typeof requestAnimationFrame === 'undefined') {
      setProgress(1)
      return undefined
    }

    const measure = () => {
      const rect = node.getBoundingClientRect()
      const span = window.innerHeight + rect.height
      if (!span) return
      const next = (window.innerHeight - rect.top) / span
      setProgress(Math.min(1, Math.max(0, next)))
    }

    const onScroll = () => {
      if (frameRef.current) return
      frameRef.current = requestAnimationFrame(() => {
        frameRef.current = 0
        measure()
      })
    }

    measure()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  return (
    <div
      className="lx-pipeline"
      ref={containerRef}
      data-linked={progress > 0}
      style={{ '--pipeline-progress': progress }}
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
                className={clsx(
                  'lx-stage',
                  isOutput && 'lx-stage--output',
                  progress >= (index + 1) / PIPELINE_STAGES.length && 'lx-stage--active',
                )}
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
