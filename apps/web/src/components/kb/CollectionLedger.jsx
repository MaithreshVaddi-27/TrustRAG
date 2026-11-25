import { Fragment, useState } from 'react'
import { ChevronDown, ChevronRight, Trash2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import DocumentTable from './DocumentTable'
import ConfirmDialog from '@/components/kb/ConfirmDialog'
import { shortModelId } from '@/lib/modelLabels'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { kbService } from '@/services/api'

/**
 * CollectionLedger — every collection, as a specification.
 *
 * A table, not a stack of identical panels. The information in a corpus
 * manager is tabular — how many documents, which vector space, when it was
 * created — and a table is the honest shape for it. Twenty collections in
 * twenty stacked cards is a wall, not a list.
 *
 * One collection opens at a time. Opening it reveals its documents and the
 * upload control, which keeps exactly one primary action on screen.
 */
export default function CollectionLedger({ collections }) {
  const queryClient = useQueryClient()
  const [expandedId, setExpandedId] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)

  const deleteMutation = useMutation({
    mutationFn: kbService.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] }),
  })

  return (
    <>
      <div className="lx-panel-block">
        <div className="overflow-x-auto">
          <table className="lx-table lx-table--stack">
            <thead>
              <tr>
                <th scope="col">Collection</th>
                <th scope="col" className="lx-table__num">
                  Documents
                </th>
                <th scope="col">Vector space</th>
                <th scope="col">Created</th>
                <th scope="col">
                  <span className="lx-sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {collections.map((kb) => {
                const isOpen = expandedId === kb.id
                return (
                  <CollectionRows
                    key={kb.id}
                    kb={kb}
                    isOpen={isOpen}
                    onToggle={() => setExpandedId(isOpen ? null : kb.id)}
                    onDelete={() => setPendingDelete(kb)}
                  />
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete collection?"
        message={
          pendingDelete
            ? `"${pendingDelete.name}" and every document indexed into it will be removed permanently.`
            : ''
        }
        confirmLabel="Delete"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) deleteMutation.mutate(pendingDelete.id)
          setPendingDelete(null)
        }}
      />
    </>
  )
}

/**
 * A collection occupies one header row and, when open, one body row. A
 * fragment keeps them inside the same table body without wrapping them in
 * an element the HTML spec does not allow there.
 */
function CollectionRows({ kb, isOpen, onToggle, onDelete }) {
  const bodyId = `collection-documents-${kb.id}`

  return (
    <Fragment>
      <tr>
        <td data-label="">
          <span className="flex items-center gap-2">
            <button
              type="button"
              onClick={onToggle}
              aria-expanded={isOpen}
              aria-controls={bodyId}
              className="lx-icon-btn h-10 w-10 shrink-0"
              title={isOpen ? 'Hide documents' : 'Show documents'}
              aria-label={
                isOpen
                  ? `Hide the documents in ${kb.name}`
                  : `Show the documents in ${kb.name}`
              }
            >
              {isOpen ? (
                <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" />
              ) : (
                <ChevronRight size={14} strokeWidth={1.75} aria-hidden="true" />
              )}
            </button>
            <span className="min-w-0">
              <span className="block truncate text-silver-100">{kb.name}</span>
              {kb.description && (
                <span className="mt-0.5 block text-[var(--size-micro)] text-silver-500">
                  {kb.description}
                </span>
              )}
            </span>
          </span>
        </td>
        <td className="lx-table__num" data-label="Documents">
          {kb.document_count ?? 0}
        </td>
        <td className="lx-table__id" data-label="Vector space">
          {kb.embedding_model ? shortModelId(kb.embedding_model) : 'Not pinned'}
        </td>
        <td className="lx-table__id" data-label="Created">
          {kb.created_at
            ? `${formatDistanceToNow(new Date(kb.created_at))} ago`
            : '—'}
        </td>
        <td className="lx-table__num" data-label="">
          <button
            type="button"
            onClick={onDelete}
            className="lx-icon-btn lx-icon-btn--alarm h-10 w-10"
            title="Delete collection"
            aria-label={`Delete collection ${kb.name}`}
          >
            <Trash2 size={14} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </td>
      </tr>
      {isOpen && (
        <tr>
          <td colSpan={5} className="lx-table__expanded" data-label="">
            <div id={bodyId}>
              <DocumentTable kb={kb} />
            </div>
          </td>
        </tr>
      )}
    </Fragment>
  )
}
