import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

/**
 * Dialog — the one modal in the product.
 *
 * Handles the backdrop, the panel, Escape to close, focus on open and
 * focus restoration on close. The content is a child, so a confirmation
 * and a form share the same shell.
 */
export default function Dialog({
  open,
  onClose,
  title,
  description = null,
  icon: Icon = null,
  size = 'md',
  initialFocusRef = null,
  children,
  footer = null,
}) {
  const panelRef = useRef(null)
  const restoreRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined

    restoreRef.current = document.activeElement
    const target = initialFocusRef?.current ?? panelRef.current
    target?.focus?.()

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose?.()
        return
      }

      // Keep focus inside the dialog.
      if (event.key === 'Tab' && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll(
          'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
        )
        if (!focusable.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      if (restoreRef.current instanceof HTMLElement) restoreRef.current.focus()
    }
  }, [open, onClose, initialFocusRef])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close dialog"
        onClick={onClose}
        className="absolute inset-0 bg-black/72 cursor-default"
        tabIndex={-1}
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`relative w-full ${
          size === 'lg' ? 'max-w-2xl' : size === 'sm' ? 'max-w-sm' : 'max-w-md'
        } max-h-[90dvh] overflow-y-auto rounded-[var(--radius-panel)] border border-[color:var(--rule)] bg-surface-panel shadow-2xl`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-[color:var(--rule-faint)] px-5 py-4">
          <div className="min-w-0">
            <h2 className="lx-h3 flex items-center gap-2">
              {Icon && <Icon size={16} strokeWidth={1.5} aria-hidden="true" />}
              {title}
            </h2>
            {description && <p className="lx-body-sm mt-1.5">{description}</p>}
          </div>

          <button
            type="button"
            onClick={onClose}
            className="lx-icon-btn shrink-0"
            aria-label="Close dialog"
          >
            <X size={16} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>

        <div className="px-5 py-5">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-3 border-t border-[color:var(--rule-faint)] px-5 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
