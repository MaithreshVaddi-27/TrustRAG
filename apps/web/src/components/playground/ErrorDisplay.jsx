import { AlertTriangle } from 'lucide-react'

export function ErrorDisplay({ errorMsg, setErrorMsg }) {
  if (!errorMsg) return null

  return (
    <div role="alert" className="p-3 bg-red-950/70 border border-red-800/80 rounded-xl text-xs text-red-300 flex items-start justify-between gap-2 shadow-glow-crimson animate-fade-in">
      <div className="flex items-start gap-2">
        <AlertTriangle size={14} className="shrink-0 mt-0.5 text-red-400" />
        <span>{errorMsg}</span>
      </div>
      <button
        type="button"
        onClick={() => setErrorMsg('')}
        aria-label="Dismiss error"
        className="text-red-400 hover:text-red-200 text-sm font-bold leading-none shrink-0"
      >
        &times;
      </button>
    </div>
  )
}