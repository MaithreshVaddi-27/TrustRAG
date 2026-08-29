import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { ExecutionTrace } from '@/components/workbench/ExecutionTrace'
import { analysisService } from '@/services/api'
import { Terminal } from 'lucide-react'

export default function TracePage() {
  const { id } = useParams()

  const { data: events, isLoading, isError } = useQuery({
    queryKey: ['analysis-trace', id],
    queryFn: () => analysisService.trace(id),
    enabled: !!id,
  })

  return (
    <AppLayout>
      <div className="p-6 max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Terminal size={20} className="text-primary-400" />
            Execution Trace
          </h1>
          <p className="text-slate-400 text-sm mt-1 font-mono">Analysis {id}</p>
        </div>
        <div className="glass-card p-5">
          {isLoading && (
            <p className="text-slate-500 text-sm">Loading trace…</p>
          )}
          {isError && (
            <p className="text-red-400 text-sm">Failed to load trace history.</p>
          )}
          {!isLoading && !isError && (
            <ExecutionTrace events={events ?? []} isLive={false} />
          )}
          <p className="text-slate-600 text-xs mt-4">
            Full trace persisted in MongoDB. SSE stream recovered from trace API if disconnected.
          </p>
        </div>
      </div>
    </AppLayout>
  )
}
