import { useRef } from 'react'
import { FolderPlus, Loader2, AlertTriangle } from 'lucide-react'
import Dialog from '@/components/app/Dialog'

/**
 * CreateKnowledgeBaseDialog — the form for a new knowledge base.
 *
 * Focus lands on the name field, Escape closes, and the error sits next to
 * the form rather than only at the top.
 */
export default function CreateKnowledgeBaseDialog({
  open,
  onClose,
  onSubmit,
  error,
  isPending,
  name = '',
  description = '',
  onNameChange = () => {},
  onDescriptionChange = () => {},
}) {
  const nameRef = useRef(null)

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Create knowledge base"
      icon={FolderPlus}
      initialFocusRef={nameRef}
      footer={
        <>
          <button type="button" onClick={onClose} className="lx-btn lx-btn--secondary">
            Cancel
          </button>
          <button
            type="submit"
            form="create-kb-form"
            disabled={isPending || !name.trim()}
            className="lx-btn lx-btn--primary"
          >
            {isPending && (
              <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
            )}
            {isPending ? 'Creating…' : 'Create knowledge base'}
          </button>
        </>
      }
    >
      <form id="create-kb-form" onSubmit={onSubmit} className="space-y-5">
        {error && (
          <div className="lx-message lx-message--alarm" role="alert">
            <AlertTriangle size={14} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        <div className="lx-field">
          <label className="lx-field__label" htmlFor="create-kb-name">
            Name
          </label>
          <input
            id="create-kb-name"
            name="kbName"
            ref={nameRef}
            type="text"
            required
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            className="lx-control"
            placeholder="Service API v3, Retention Policy 2026…"
          />
        </div>

        <div className="lx-field">
          <label className="lx-field__label" htmlFor="create-kb-desc">
            Description
          </label>
          <textarea
            id="create-kb-desc"
            name="kbDesc"
            rows={3}
            value={description}
            onChange={(e) => onDescriptionChange(e.target.value)}
            className="lx-control"
            placeholder="Purpose, domain context, and expected document types…"
          />
        </div>
      </form>
    </Dialog>
  )
}
