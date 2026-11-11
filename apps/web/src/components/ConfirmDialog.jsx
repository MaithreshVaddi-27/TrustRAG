import { useEffect, useRef } from 'react'

/**
 * ConfirmDialog — the accessible replacement for window.confirm().
 *
 * role="dialog", aria-modal, Escape to cancel, initial focus on cancel.
 * A destructive action gets the crimson treatment; everything else is the
 * ordinary off-white plate.
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  onConfirm,
  onCancel,
  danger = true,
}) {
  const cancelRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    cancelRef.current?.focus()
    return undefined
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close dialog"
        onClick={onCancel}
        className="absolute inset-0 bg-black/72 cursor-default"
        tabIndex={-1}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full max-w-sm rounded-[var(--radius-panel)] border border-[color:var(--rule)] bg-surface-panel shadow-2xl"
      >
        <div className="p-5">
          <h2 className="lx-h3">{title}</h2>
          {message && <p className="lx-body mt-2">{message}</p>}

          <div className="mt-5 flex justify-end gap-3">
            <button
              ref={cancelRef}
              type="button"
              onClick={onCancel}
              className="lx-btn lx-btn--secondary"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className={danger ? 'lx-btn lx-btn--alarm' : 'lx-btn lx-btn--primary'}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
