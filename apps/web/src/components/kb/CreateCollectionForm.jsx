import { useEffect, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

/**
 * CreateCollectionForm — the form for a new collection.
 *
 * Inline, not a modal. Creating a collection is two fields; a dialog for
 * two fields interrupts the work and hides the list the user is about to
 * change. The form appears above the ledger, takes the name first, and
 * reports its error next to the field that caused it.
 */
export default function CreateCollectionForm({
  onSubmit,
  onCancel,
  error,
  isPending,
  name = '',
  description = '',
  onNameChange = () => {},
  onDescriptionChange = () => {},
}) {
  const nameRef = useRef(null)

  useEffect(() => {
    nameRef.current?.focus()
  }, [])

  return (
    <form
      id="create-collection-form"
      onSubmit={onSubmit}
      className="lx-panel-block"
      aria-label="Create a collection"
    >
      <div className="lx-panel-block__head">
        <h2 className="lx-panel-block__title">New collection</h2>
      </div>

      <div className="lx-panel-block__body space-y-5">
        {error && (
          <div className="lx-message lx-message--alarm" role="alert">
            <AlertTriangle size={14} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        <div className="lx-grid-2">
          <div className="lx-field">
            <label className="lx-field__label" htmlFor="collection-name">
              Name
            </label>
            <input
              id="collection-name"
              name="collectionName"
              ref={nameRef}
              type="text"
              required
              maxLength={100}
              value={name}
              onChange={(event) => onNameChange(event.target.value)}
              className="lx-control"
              placeholder="Service API v3"
            />
          </div>

          <div className="lx-field">
            <label className="lx-field__label" htmlFor="collection-description">
              Description
            </label>
            <input
              id="collection-description"
              name="collectionDescription"
              type="text"
              maxLength={500}
              value={description}
              onChange={(event) => onDescriptionChange(event.target.value)}
              className="lx-control"
              placeholder="Public API contract and rate limits"
            />
          </div>
        </div>
      </div>

      <div className="lx-panel-block__foot flex items-center justify-end gap-3">
        <button type="button" onClick={onCancel} className="lx-btn lx-btn--secondary">
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending || !name.trim()}
          className="lx-btn lx-btn--primary"
        >
          {isPending && (
            <ThinkingOrbs size="sm" />
          )}
          {isPending ? 'Creating…' : 'Create collection'}
        </button>
      </div>
    </form>
  )
}
