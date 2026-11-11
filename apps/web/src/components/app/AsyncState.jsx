import { AlertTriangle, Inbox } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

/**
 * AsyncState — one component for the three states a data surface can be in.
 *
 * Every route used to hand-roll its own loading spinner, its own error box
 * and its own empty card, and each one looked slightly different. This is
 * the single version:
 *
 *   loading — a breathing skeleton in the surface's own shape
 *   error   — crimson, names the problem, offers the recovery
 *   empty   — a heading, one sentence, and the action that fills it
 *
 * No illustration. A decorative icon in an empty state tells the user
 * nothing about what to do next.
 */
export default function AsyncState({
  status = 'ready',
  loadingLabel = 'Loading…',
  errorTitle = 'Something went wrong',
  errorMessage = null,
  onRetry = null,
  emptyIcon: EmptyIcon = Inbox,
  emptyTitle = 'Nothing here yet',
  emptyBody = null,
  emptyAction = null,
  skeleton = null,
}) {
  if (status === 'ready') return null

  if (status === 'loading') {
    return (
      <div className="lx-panel-block" aria-busy="true" aria-live="polite">
        {skeleton ?? (
          <div className="flex flex-col items-center justify-center gap-4 px-6 py-16">
            <ThinkingOrbs size="md" />
            <span className="lx-body-sm">{loadingLabel}</span>
          </div>
        )}
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="lx-message lx-message--alarm" role="alert">
        <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <span className="lx-message__title">{errorTitle}</span>
          <span className="lx-message__body">
            {errorMessage || 'An unexpected error occurred.'}
          </span>
        </div>
        {onRetry && (
          <button type="button" onClick={onRetry} className="lx-btn lx-btn--secondary shrink-0">
            Retry
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="lx-panel-block">
      <div className="lx-empty">
        <EmptyIcon size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
        <p className="lx-empty__title">{emptyTitle}</p>
        {emptyBody && <p className="lx-empty__body">{emptyBody}</p>}
        {emptyAction}
      </div>
    </div>
  )
}
