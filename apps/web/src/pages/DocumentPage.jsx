import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  Check,
  AlertTriangle,
  Copy,
  Loader2,
} from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/ui/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import { kbService } from '@/services/api'
import { copyToClipboard } from '@/lib/clipboard'

/**
 * DocumentPage — one indexed document, in full.
 *
 * The corpus page shows a document as a row: a name, a size, a state. This
 * page answers the three questions an operator actually has about a
 * document that is already in the index:
 *
 *   1. What exactly is indexed? The full content hash, the size, the
 *      format, the identifier. The hash is what makes the row verifiable.
 *   2. Did it ingest? The state, and the backend's own error message when
 *      it did not.
 *   3. When does it apply? The effective window — the interval during
 *      which retrieval is allowed to treat this document as authoritative.
 *
 * The third question is the reason this page exists. Every other surface
 * in the product can show a document or a chunk; none of them can show the
 * validity window of a document, because none of them asks.
 *
 * The frame is rendered before the record arrives and the values fill in.
 * Every value in it is exactly one line tall whether it is loaded or not,
 * so the panels below never move when the record lands. A skeleton that
 * is a different shape from the content it stands in for is a layout
 * shift waiting to happen; a frame with holes in it is not.
 */
const DESCRIPTION =
  'One indexed document in the corpus — what it contains, how it ingested, and the window in which retrieval may treat it as authoritative.'

export default function DocumentPage() {
  const { id } = useParams()
  const [copied, setCopied] = useState(false)

  const {
    data: doc,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['document', id],
    queryFn: () => kbService.getDocument(id),
    enabled: !!id,
  })

  const {
    data: collection,
  } = useQuery({
    queryKey: ['knowledge-base', doc?.knowledge_base_id],
    queryFn: () => kbService.get(doc.knowledge_base_id),
    enabled: !!doc?.knowledge_base_id,
  })

  const handleCopy = async () => {
    const ok = await copyToClipboard(doc?.content_hash)
    if (!ok) return
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <Link
          to="/knowledge-bases"
          className="lx-inline-action w-fit text-[var(--size-body-sm)]"
        >
          <ArrowLeft size={13} strokeWidth={1.75} aria-hidden="true" />
          <span>All collections</span>
        </Link>

        <PageHeader
          className="lx-doc-header"
          title={doc?.filename ?? 'Document'}
          description={DESCRIPTION}
        />

        <AsyncState
          status={isError ? 'error' : 'ready'}
          errorTitle="Failed to load the document"
          errorMessage={error?.message}
          onRetry={refetch}
        />

        {!isError && (
          <>
            {/* ── Content ─────────────────────────────────────────────── */}
            <section className="lx-panel-block">
              <div className="lx-panel-block__head">
                <h2 className="lx-panel-block__title">Content</h2>
              </div>
              <div className="lx-panel-block__body">
                <dl className="lx-deflist lx-deflist--measured">
                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Size</dt>
                    <dd className="lx-deflist__value">
                      {doc ? formatBytes(doc.file_size) : '—'}
                    </dd>
                  </div>

                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Format</dt>
                    <dd className="lx-deflist__value">
                      {doc ? formatLabel(doc.filename) : '—'}
                    </dd>
                  </div>

                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Content hash</dt>
                    <dd className="lx-deflist__value lx-deflist__value--grow">
                      {/* The copy button is taller than a line of text, so
                          the row keeps its height either way: a placeholder
                          the size of the button stands in until the hash
                          arrives. */}
                      <span className="flex items-center justify-end gap-2">
                        <span className="lx-value-line">
                          {doc ? doc.content_hash : '—'}
                        </span>
                        {doc ? (
                          <button
                            type="button"
                            onClick={handleCopy}
                            className="lx-icon-btn h-7 w-7 shrink-0"
                            title="Copy the content hash"
                            aria-label="Copy the content hash"
                          >
                            {copied ? (
                              <Check
                                size={13}
                                strokeWidth={2}
                                aria-hidden="true"
                              />
                            ) : (
                              <Copy
                                size={13}
                                strokeWidth={1.75}
                                aria-hidden="true"
                              />
                            )}
                          </button>
                        ) : (
                          <span
                            className="lx-icon-btn h-7 w-7 shrink-0"
                            aria-hidden="true"
                          />
                        )}
                      </span>
                    </dd>
                  </div>

                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Document id</dt>
                    <dd className="lx-deflist__value lx-deflist__value--grow">
                      <span className="lx-value-line">{doc?.id ?? '—'}</span>
                    </dd>
                  </div>
                </dl>
              </div>
            </section>

            {/* ── Ingestion ───────────────────────────────────────────── */}
            <section className="lx-panel-block">
              <div className="lx-panel-block__head">
                <h2 className="lx-panel-block__title">Ingestion</h2>
              </div>
              <div className="lx-panel-block__body space-y-4">
                {doc ? (
                  <StateChip status={doc.ingestion_status} />
                ) : (
                  <span className="lx-chip" aria-hidden="true">
                    <span className="lx-skeleton block h-5 w-12" />
                  </span>
                )}

                {doc?.error_message && (
                  <div className="lx-message lx-message--alarm" role="alert">
                    <AlertTriangle
                      size={14}
                      strokeWidth={1.75}
                      className="lx-message__icon"
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <span className="lx-message__title">Ingestion failed</span>
                      <span className="lx-message__body">{doc.error_message}</span>
                    </div>
                  </div>
                )}

                <dl className="lx-deflist lx-deflist--measured">
                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Uploaded</dt>
                    <dd className="lx-deflist__value">
                      {doc?.created_at ? formatTimestamp(doc.created_at) : '—'}
                    </dd>
                  </div>

                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Vector space</dt>
                    <dd className="lx-deflist__value lx-deflist__value--grow">
                      <span className="lx-value-line">
                        {collection
                          ? (collection.embedding_model ?? 'Not pinned')
                          : '—'}
                      </span>
                    </dd>
                  </div>

                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Collection</dt>
                    <dd className="lx-deflist__value">
                      {collection?.name ?? '—'}
                    </dd>
                  </div>
                </dl>
              </div>
            </section>

            {/* ── Applicability ───────────────────────────────────────── */}
            <section className="lx-panel-block">
              <div className="lx-panel-block__head">
                <h2 className="lx-panel-block__title">Applicability</h2>
              </div>
              <div className="lx-panel-block__body space-y-4">
                <dl className="lx-deflist lx-deflist--measured">
                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Effective from</dt>
                    <dd className="lx-deflist__value">
                      {formatDate(doc?.effective_from)}
                    </dd>
                  </div>

                  <div className="lx-deflist__row">
                    <dt className="lx-deflist__key">Effective until</dt>
                    <dd className="lx-deflist__value">
                      {formatDate(doc?.effective_until)}
                    </dd>
                  </div>
                </dl>

                <p className="lx-micro">
                  Retrieval treats a document as authoritative only inside this
                  window. A document with no window is always in force.
                </p>
              </div>
            </section>
          </>
        )}
      </div>
    </AppLayout>
  )
}

/**
 * The ingestion state, as a quiet chip. A failed ingestion is the only
 * alarm — it is the one state that means the document is not retrievable.
 */
function StateChip({ status }) {
  if (status === 'completed') {
    return (
      <span className="lx-chip">
        <Check size={11} strokeWidth={2} aria-hidden="true" />
        Indexed
      </span>
    )
  }

  if (status === 'failed') {
    return (
      <span className="lx-chip lx-chip--alarm">
        <AlertTriangle size={11} strokeWidth={2} aria-hidden="true" />
        Failed
      </span>
    )
  }

  return (
    <span className="lx-chip">
      <Loader2 size={11} strokeWidth={2} className="animate-spin" aria-hidden="true" />
      {status === 'pending' ? 'Queued' : 'Processing'}
    </span>
  )
}

/** The file extension as a readable label, not a bare suffix. */
function formatLabel(filename) {
  const ext = (filename || '').split('.').pop()?.toUpperCase()
  if (!ext || ext === filename.toUpperCase()) return 'Plain text'
  if (ext === 'TXT' || ext === 'MD') return 'Plain text'
  if (ext === 'PDF') return 'PDF'
  if (ext === 'DOCX') return 'Word document'
  if (ext === 'CSV') return 'CSV'
  if (ext === 'JSON') return 'JSON'
  if (ext === 'HTML' || ext === 'HTM') return 'HTML'
  return ext
}

/** Bytes, with the exact count underneath it when it is worth the precision. */
function formatBytes(bytes) {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(2)} MB`
}

/** A timestamp, compact and unambiguous: 2026-11-11 20:38. */
function formatTimestamp(value) {
  const date = new Date(value)
  const pad = (n) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    ` ${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

/** A date, or a dash when the document sets no such bound. */
function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString()
}
