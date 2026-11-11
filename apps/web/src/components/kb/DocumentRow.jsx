import { memo } from 'react'
import {
  Check,
  AlertTriangle,
  Loader2,
  Trash2,
  FileText,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

/**
 * DocumentRow — one document inside a collection.
 *
 * A ruled record row, not a card and not a nested table. The file, its
 * size, the hash that pins its content, when it was indexed, its ingestion
 * state and the action. The state is a quiet chip; only a failed ingestion
 * is an alarm.
 */
const DocumentRow = memo(function DocumentRow({ doc, onDelete }) {
  const status = doc.ingestion_status || doc.status || 'completed'
  const isCompleted = status === 'completed'
  const isFailed = status === 'failed'

  const extension = (doc.filename || '').split('.').pop()?.toUpperCase() || 'FILE'
  const hash = doc.content_hash || ''

  return (
    <li className="lx-list__item">
      <div className="lx-record">
        <div className="lx-record__name">
          <FileText size={14} strokeWidth={1.5} className="shrink-0 text-silver-500" aria-hidden="true" />
          <span className="truncate text-silver-100">{doc.filename}</span>
          <span className="lx-chip shrink-0">{extension}</span>
        </div>

        <span className="lx-record__value">{doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : '—'}</span>

        <span className="lx-record__value" title={hash || undefined}>
          {hash ? hash.slice(0, 12) : '—'}
        </span>

        <span className="lx-record__value">
          {formatDistanceToNow(new Date(doc.created_at))} ago
        </span>

        <span className="lx-record__value lx-record__value--end">
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
        </span>

        <span className="lx-record__value lx-record__value--end">
          <button
            type="button"
            onClick={() => onDelete(doc)}
            className="lx-icon-btn lx-icon-btn--alarm h-8 w-8"
            title="Delete document"
            aria-label={`Remove document ${doc.filename}`}
          >
            <Trash2 size={14} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </span>
      </div>
    </li>
  )
})

export default DocumentRow
