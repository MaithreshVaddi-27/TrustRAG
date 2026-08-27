import { useParams } from 'react-router-dom'
import AppLayout from '@/layouts/AppLayout'
import { ExecutionTrace } from '@/components/workbench/ExecutionTrace'
import { Terminal } from 'lucide-react'

export default function TracePage() {
  const { id } = useParams()
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
          <ExecutionTrace events={[]} isLive={false} />
          <p className="text-slate-600 text-xs mt-4">
            Full trace persisted in MongoDB. SSE stream recovered from trace API if disconnected.
          </p>
        </div>
      </div>
    </AppLayout>
  )
}
