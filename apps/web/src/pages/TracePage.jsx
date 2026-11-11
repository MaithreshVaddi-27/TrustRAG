import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/ui/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import { ExecutionTrace } from '@/components/workbench/ExecutionTrace'
import { SkeletonRows } from '@/components/workbench/Skeleton'
import { analysisService } from '@/services/api'

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
  })

  const status = isLoading ? 'loading' : isError ? 'error' : 'ready'

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <PageHeader
          title="Execution trace"
          countLabel={id}
          description="The full event history for this analysis, recovered from the trace API when the stream is disconnected."
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
          <section className="lx-panel-block">
            <div className="lx-panel-block__body">
              <ExecutionTrace events={events ?? []} isLive={false} />
            </div>
            <div className="lx-panel-block__foot">
              <p className="lx-micro">
                Persisted in MongoDB. The SSE stream is recovered from the trace
                API if it disconnected.
              </p>
            </div>
          </section>
        )}
      </div>
    </AppLayout>
  )
}
