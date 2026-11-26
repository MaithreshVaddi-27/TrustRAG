import { useMemo } from 'react'
import { Activity, Cpu, Globe, Layers } from 'lucide-react'
import { compactTraceEvents, displayMessage } from './traceEvents'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'

/**
 * PipelineTelemetryHUD — where the run is right now.
 *
 * A live status line and a four-step sequence. The steps are a sequence,
 * not four cards: the reader needs to know which stage is running and which
 * have passed, and a stepper says that without four competing boxes.
 */
export function PipelineTelemetryHUD({
  events = [],
  query = '',
  enableWebSearch = false,
  provider = '',
  model = '',
  embeddingModel = '',
  analysisStatus,
}) {
  const status = useMemo(() => {
    const compacted = compactTraceEvents(events)
    const eventNames = new Set(compacted.map((event) => event.event))
    const lastEvent = compacted[compacted.length - 1]

    const retrievalDone = eventNames.has('retrieval.completed')
    const generationStarted = eventNames.has('generation.started')
    const generationDone =
      eventNames.has('generation.completed') || eventNames.has('claims.started')
    const verificationStarted = eventNames.has('claims.started')
    const verificationDone = eventNames.has('claims.verified')

    const isCompleted =
      ['completed', 'abstained', 'failed', 'outage'].includes(analysisStatus) ||
      eventNames.has('analysis.completed') ||
      eventNames.has('analysis.abstained') ||
      eventNames.has('analysis.failed') ||
      eventNames.has('analysis.outage')

    const isRecovering =
      eventNames.has('recovery.rewrite') ||
      eventNames.has('recovery.re_retrieve') ||
      eventNames.has('recovery.regenerate') ||
      eventNames.has('recovery.started')

    // Live message: prefer the richest detail, never a bare tautology.
    let liveMessage = 'Initialising the verification pipeline…'
    if (lastEvent) {
      liveMessage =
        displayMessage(lastEvent.event, lastEvent.data?.message) ||
        lastEvent.event.replace(/[._]/g, ' ')
    }
    if (analysisStatus && !['pending', 'processing'].includes(analysisStatus)) {
      liveMessage = analysisStatus === 'failed' ? 'Analysis failed' : 'Analysis finished'
    }

    return {
      retrievalDone,
      generationStarted,
      generationDone,
      verificationStarted,
      verificationDone,
      isCompleted,
      isRecovering,
      liveMessage,
      eventCount: compacted.length,
    }
  }, [events, analysisStatus])

  const modelShort = shortModelId(model)
  const providerLabel = providerShortLabel(provider)
  const embeddingShort = shortModelId(embeddingModel)

  // The stages run in order, and exactly one of them is running at a time.
  const steps = [
    {
      index: '01',
      title: 'Hybrid retrieval',
      meta: enableWebSearch ? 'Vector + BM25 + web' : 'Vector + BM25',
      state: status.retrievalDone ? 'done' : 'active',
    },
    {
      index: '02',
      title: 'Rank fusion',
      meta: 'RRF and rerank',
      state: status.retrievalDone ? 'done' : 'pending',
    },
    {
      index: '03',
      title: 'Grounded synthesis',
      meta:
        providerLabel && modelShort
          ? `${providerLabel} · ${modelShort}`
          : 'Engine default',
      state: status.generationDone
        ? 'done'
        : status.retrievalDone || status.generationStarted
          ? 'active'
          : 'pending',
    },
    {
      index: '04',
      title: 'Claim entailment',
      meta: 'Atomic NLI verifier',
      state:
        status.verificationDone || status.isCompleted
          ? 'done'
          : status.verificationStarted
            ? 'active'
            : 'pending',
    },
  ]

  return (
    <section className="lx-panel-block" aria-labelledby="telemetry-heading">
      <div className="lx-panel-block__head">
        <div className="min-w-0">
          <h2
            id="telemetry-heading"
            className="lx-panel-block__title flex items-center gap-2"
          >
            <span
              className={`lx-dot${status.isCompleted ? '' : ' lx-dot--live'}`}
              aria-hidden="true"
            />
            Autonomous verification engine
          </h2>
          <p className="lx-body-sm mt-1 truncate">{status.liveMessage}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {query && (
            <span className="lx-chip max-w-[220px] truncate" title={query}>
              {query}
            </span>
          )}
          <span
            className="lx-chip"
            title={model ? `${providerLabel}: ${model}` : providerLabel || 'Engine'}
          >
            <Cpu size={11} strokeWidth={1.75} aria-hidden="true" />
            {providerLabel || 'Engine'}: {modelShort || 'default'}
          </span>
          {embeddingModel && (
            <span className="lx-chip" title={embeddingModel}>
              <Layers size={11} strokeWidth={1.75} aria-hidden="true" />
              {embeddingShort}
            </span>
          )}
          <span className="lx-chip">
            Events <strong className="text-silver-200">{status.eventCount}</strong>
          </span>
          {enableWebSearch && (
            <span className="lx-chip">
              <Globe size={11} strokeWidth={1.75} aria-hidden="true" />
              MCP Tavily
            </span>
          )}
          {status.isRecovering && (
            <span className="lx-chip lx-chip--alarm">
              <Activity size={11} strokeWidth={1.75} aria-hidden="true" />
              Self-healing active
            </span>
          )}
        </div>
      </div>

      <div className="lx-steps">
        {steps.map((step) => (
          <div
            key={step.index}
            className={`lx-step${step.state === 'active' ? ' lx-step--active' : ''}${
              step.state === 'done' ? ' lx-step--done' : ''
            }`}
          >
            <div className="lx-step__head">
              <span className="lx-step__label">{step.index}</span>
              {step.state === 'done' ? (
                <span className="lx-micro text-silver-400">Done</span>
              ) : step.state === 'active' ? (
                <span className="lx-micro text-crimson-300">Running</span>
              ) : (
                <span className="lx-micro">Pending</span>
              )}
            </div>
            <p className="lx-step__title">{step.title}</p>
            <p className="lx-step__meta">{step.meta}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
