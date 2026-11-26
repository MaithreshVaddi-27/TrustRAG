import { Zap, CornerDownLeft } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

/**
 * RunButton — the execution control.
 *
 * One button, two states. While the pipeline runs it reports the elapsed
 * time, because a verification run that takes thirty seconds should feel
 * like a process rather than a freeze.
 */
export function RunButton({ loading, elapsedSec, disabled, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading || !onClick}
      id="run-analysis"
      className="lx-btn lx-btn--primary w-full justify-center"
      aria-busy={loading}
      aria-label={
        loading ? `Executing the pipeline, ${elapsedSec} seconds elapsed` : 'Run analysis'
      }
    >
      {loading ? (
        <>
          <ThinkingOrbs size="sm" elapsedSec={elapsedSec} />
          <span>Executing pipeline</span>
          <span className="font-mono text-[var(--size-micro)] tabular-nums opacity-80">
            {elapsedSec}s
          </span>
        </>
      ) : (
        <>
          <Zap size={14} strokeWidth={1.75} aria-hidden="true" />
          <span>Run analysis</span>
          <span className="ml-1 inline-flex items-center gap-0.5 font-mono text-[var(--size-micro)] opacity-70">
            <CornerDownLeft size={10} aria-hidden="true" />
            ⌘↵
          </span>
        </>
      )}
    </button>
  )
}
