import { Zap, CornerDownLeft } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

export function RunButton({ loading, elapsedSec, disabled, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading || !onClick}
      id="run-analysis"
      className="btn-primary w-full flex items-center justify-center gap-2 shadow-lg shadow-primary-950/60 transition-all relative overflow-hidden"
    >
      {loading ? (
        <>
          <ThinkingOrbs size="sm" />
          <span>Executing Pipeline ({elapsedSec}s)…</span>
        </>
      ) : (
        <>
          <Zap size={14} className="text-cyan-300" />
          <span>Run Analysis</span>
          <span className="text-[10px] opacity-75 font-mono ml-1 flex items-center gap-0.5">
            <CornerDownLeft size={10} /> ⌘Enter
          </span>
        </>
      )}
    </button>
  )
}