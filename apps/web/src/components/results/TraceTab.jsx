import { ExecutionTrace } from '@/components/workbench/ExecutionTrace'

export function TraceTab({ currentTraceEvents }) {
  return <ExecutionTrace events={currentTraceEvents} isLive={false} />
}
