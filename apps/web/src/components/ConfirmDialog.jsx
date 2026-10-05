import { useEffect, useRef } from 'react'

/**
 * ConfirmDialog — accessible replacement for window.confirm().
 * role=dialog, aria-modal, Escape to cancel, initial focus on cancel.
 */
export default function ConfirmDialog({ open, title, message, confirmLabel = 'Delete', onConfirm, onCancel, danger = true }) {
  const cancelRef = useRef(null)

  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()
    const onKey = e => {
      if (e.key === 'Escape') onCancel?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="bg-surface-900 border border-slate-700/80 rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden animate-slide-up"
      >
        <div className="p-5 space-y-3">
          <h2 className="text-base font-bold text-white">{title}</h2>
          {message && <p className="text-sm text-slate-400">{message}</p>}
          <div className="flex justify-end gap-3 pt-2">
            <button
              ref={cancelRef}
              type="button"
              onClick={onCancel}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className={danger ? 'btn-danger text-xs' : 'btn-primary text-xs'}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
