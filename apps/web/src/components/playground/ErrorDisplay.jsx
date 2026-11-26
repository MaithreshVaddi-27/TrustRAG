import { AlertTriangle, X } from 'lucide-react'

/**
 * ErrorDisplay — the one place a failure is reported in the playground.
 *
 * It states what went wrong and gives the reader a way to dismiss it. It
 * does not apologise or suggest a fix it cannot offer.
 */
export function ErrorDisplay({ errorMsg, setErrorMsg, onRetry = null }) {
  if (!errorMsg) return null

  // The section chrome belongs to the error, not to the layout: a caller
  // wrapping this in `.lx-workbench__section` left 41px of empty padding and
  // a hairline on every successful run.
  return (
    <div className="lx-workbench__section">
      <div className="lx-message lx-message--alarm" role="alert">
        <AlertTriangle size={14} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
        <span className="min-w-0 flex-1">{errorMsg}</span>
        {onRetry && (
          <button type="button" onClick={onRetry} className="lx-btn lx-btn--secondary shrink-0">
            Try again
          </button>
        )}
        <button
          type="button"
          onClick={() => setErrorMsg('')}
          aria-label="Dismiss the error"
          className="lx-icon-btn h-10 w-10 shrink-0"
        >
          <X size={13} strokeWidth={1.75} aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
