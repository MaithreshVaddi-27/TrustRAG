import { memo } from 'react'
import { FileText, Check, AlertTriangle, Loader2, Trash2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

/**
 * DocumentRow — one indexed document inside a knowledge base.
 *
 * A row in a ruled list: the file, its measurements in mono, its ingestion
 * state, and the action. The state is a quiet chip; only a failed ingestion
 * is an alarm.
 */
const DocumentRow = memo(function DocumentRow({ doc, onDelete }) {
  const isCompleted =
    doc.status === 'completed' || doc.ingestion_status === 'completed' || !doc.status
  const isFailed = doc.status === 'failed' || doc.ingestion_status === 'failed'

  return (
    <li className="lx-list__item">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className="grid h-8 w-8 shrink-0 place-items-center rounded-[var(--radius-control)] border border-[color:var(--rule)] bg-surface-inset text-silver-400"
            aria-hidden="true"
          >
            <FileText size={15} strokeWidth={1.5} />
          </span>

          <div className="min-w-0">
            <p className="truncate text-[var(--size-body)] text-silver-100">{doc.filename}</p>
            <div className="lx-list__meta">
              <span>
                {doc.chunk_count !== undefined ? `${doc.chunk_count} chunks` : 'Indexed chunks'}
              </span>
              <span>·</span>
              <span>{doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'Document'}</span>
              <span>·</span>
              <span>{formatDistanceToNow(new Date(doc.created_at))} ago</span>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3 self-end sm:self-center">
          {isCompleted ? (
            <span className="lx-chip">
              <Check size={11} strokeWidth={2} aria-hidden="true" />
              Indexed
            </span>
          ) : isFailed ? (
            <span
              className="lx-chip lx-chip--alarm"
              title={doc.error_message || 'Ingestion failed'}
            >
              <AlertTriangle size={11} strokeWidth={2} aria-hidden="true" />
              Failed
            </span>
          ) : (
            <span className="lx-chip">
              <Loader2 size={11} strokeWidth={2} className="animate-spin" aria-hidden="true" />
              Indexing
            </span>
          )}

          <button
            type="button"
            onClick={() => onDelete(doc)}
            className="lx-icon-btn lx-icon-btn--alarm h-8 w-8"
            title="Delete document"
            aria-label={`Remove document ${doc.filename}`}
          >
            <Trash2 size={14} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>
      </div>
    </li>
  )
})

export default DocumentRow
