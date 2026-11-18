import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock, Cpu, Database } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/common/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import { ExecutionTrace } from '@/components/workbench/ExecutionTrace'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'
import { SkeletonRows } from '@/components/workbench/Skeleton'
import { analysisService, kbService } from '@/services/api'

/**
 * TracePage — the event history of one analysis.
 *
 * A trace is a record of a run, and a record of a run is worthless without
 * the run: which question was asked, which collection answered it, what
 * the verifier concluded and which model produced it. The events say what
 * happened; this page says what happened to what.
 */
export default function TracePage() {
  const { id } = useParams()

  const {
    data: events,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['analysis-trace', id],
    queryFn: () => analysisService.trace(id),
    enabled: !!id,
    // A trace that does not exist will not exist on the third attempt
    // either. Only a transport failure is worth repeating.
    retry: (failureCount, failure) => failure?.status !== 404 && failureCount < 2,
  })

  const {
    data: analysis,
  } = useQuery({
    queryKey: ['analysis', id],
    queryFn: () => analysisService.get(id),
    enabled: !!id,
    retry: (failureCount, failure) => failure?.status !== 404 && failureCount < 2,
  })

  const { data: collections = [] } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list,
    staleTime: 30000,
  })

  const status = isLoading ? 'loading' : isError ? 'error' : 'ready'

  const collectionName = collections.find(
    (kb) => kb.id === analysis?.knowledge_base_id,
  )?.name

  // The time the pipeline itself reported, summed over the stages that
  // reported one. It is the pipeline's own measurement, not a stopwatch
  // around it.
  const measuredMs = (events ?? []).reduce(
    (total, event) => total + (event.data?.latency_ms ?? 0),
    0,
  )

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <Link
          to="/dashboard"
          className="lx-inline-action w-fit text-[var(--size-body-sm)]"
        >
          <ArrowLeft size={13} strokeWidth={1.75} aria-hidden="true" />
          <span>Activity</span>
        </Link>

        <PageHeader
          title="Execution trace"
          countLabel={id}
          description={
            analysis?.query
              ? `The full event history for “${analysis.query}”.`
              : 'The full event history for this analysis, recovered from the trace API when the stream is disconnected.'
          }
        />

        <AsyncState
          status={status}
          errorTitle="Failed to load the trace"
          errorMessage={error?.message}
          onRetry={refetch}
          skeleton={
            <div className="p-5">
              <SkeletonRows rows={5} className="h-11 rounded-lg" />
            </div>
          }
        />

        {status === 'ready' && (
          <>
            {/* ── The run ─────────────────────────────────────────────── */}
            <section className="lx-panel-block">
              <div className="lx-panel-block__head">
                <h2 className="lx-panel-block__title">The run</h2>
                {analysis?.reliability && analysis?.status === 'completed' && (
                  <ReliabilityBadge
                    score={analysis.reliability.score}
                    status={analysis.reliability.status}
                    size="sm"
                  />
                )}
              </div>

              <div className="lx-panel-block__body">
                <dl className="lx-figures">
                  <Figure
                    label="Collection"
                    value={collectionName ?? '—'}
                    icon={Database}
                  />

                  {analysis?.llm_model && (
                    <Figure
                      label="Model"
                      value={`${analysis.llm_provider ?? 'local'} · ${analysis.llm_model}`}
                      icon={Cpu}
                    />
                  )}

                  <Figure
                    label="Events"
                    value={String((events ?? []).length)}
                    icon={Clock}
                  />

                  {measuredMs > 0 && (
                    <Figure
                      label="Stage time"
                      value={`${(measuredMs / 1000).toFixed(2)}s`}
                      icon={Clock}
                    />
                  )}
                </dl>

                {analysis?.status === 'abstained' && (
                  <p className="lx-micro mt-3">
                    The run produced no answer: the retrieved segments did not
                    support a verified one.
                  </p>
                )}
              </div>
            </section>

            {/* ── The events ──────────────────────────────────────────── */}
            <section className="lx-panel-block">
              <div className="lx-panel-block__head">
                <h2 className="lx-panel-block__title">Events</h2>
                <span className="lx-chip">
                  {(events ?? []).length}{' '}
                  {(events ?? []).length === 1 ? 'event' : 'events'}
                </span>
              </div>

              <div className="px-5 py-5">
                <ExecutionTrace events={events ?? []} isLive={false} />
              </div>

              <div className="lx-panel-block__foot">
                <p className="lx-micro">
                  The durations are the ones the pipeline reported for each
                  stage. The stage time is their sum.
                </p>
              </div>
            </section>
          </>
        )}
      </div>
    </AppLayout>
  )
}

/**
 * Figure — one measurement in the strip under the run's heading.
 */
function Figure({ label, value, icon: Icon }) {
  return (
    <div className="lx-figure">
      <dt className="lx-figure__label flex items-center gap-1.5">
        {Icon && (
          <Icon size={11} strokeWidth={1.75} aria-hidden="true" />
        )}
        {label}
      </dt>
      <dd className="lx-figure__value">{value}</dd>
    </div>
  )
}
