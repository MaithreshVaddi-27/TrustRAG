import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Database,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  Trash2,
  Upload,
  Check,
  AlertTriangle,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import ConfirmDialog from '@/components/ConfirmDialog'
import DocumentRow from './DocumentRow'
import { kbService } from '@/services/api'

/**
 * KnowledgeBaseCard — one collection, and the documents indexed into it.
 *
 * The document list is collapsed by default and fetched only when it is
 * opened, so a workspace with forty collections does not issue forty
 * document queries on load.
 */
export default function KnowledgeBaseCard({ kb }) {
  const queryClient = useQueryClient()
  const [isExpanded, setIsExpanded] = useState(false)
  const [confirmKb, setConfirmKb] = useState(false)
  const [confirmDoc, setConfirmDoc] = useState(null)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const fileInputRef = useRef(null)

  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents', kb.id],
    queryFn: () => kbService.listDocuments(kb.id),
    enabled: isExpanded,
  })

  const deleteKbMutation = useMutation({
    mutationFn: kbService.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] }),
  })

  const deleteDocMutation = useMutation({
    mutationFn: (docId) => kbService.deleteDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', kb.id] })
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
    },
  })

  const uploadDocMutation = useMutation({
    mutationFn: (file) => kbService.uploadDocument(kb.id, file),
    onMutate: () => {
      setUploadStatus('uploading')
      setUploadError(null)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', kb.id] })
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
      setUploadStatus('success')
      setTimeout(() => setUploadStatus(null), 3500)
    },
    onError: (err) => {
      setUploadStatus('error')
      setUploadError(err.message || 'Upload failed')
      setTimeout(() => {
        setUploadStatus(null)
        setUploadError(null)
      }, 5000)
    },
  })

  const handleFileChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    event.target.value = ''
    uploadDocMutation.mutate(file)
  }

  return (
    <article className="lx-panel-block">
      <div className="lx-panel-block__head">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="grid h-9 w-9 shrink-0 place-items-center rounded-[var(--radius-control)] border border-[color:var(--rule)] bg-surface-inset text-silver-400"
            aria-hidden="true"
          >
            <Database size={17} strokeWidth={1.5} />
          </span>

          <div className="min-w-0">
            <h2 className="truncate text-[var(--size-h3)] text-silver-050">{kb.name}</h2>
            <p className="lx-body-sm mt-0.5 line-clamp-1">
              {kb.description || 'No description provided.'}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadDocMutation.isPending}
            className="lx-btn lx-btn--primary"
          >
            {uploadDocMutation.isPending ? (
              <>
                <Loader2 size={13} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
                <span>Indexing</span>
              </>
            ) : (
              <>
                <Upload size={13} strokeWidth={1.75} aria-hidden="true" />
                <span>Upload document</span>
              </>
            )}
          </button>

          <input
            id={`file-upload-${kb.id}`}
            name="document-file"
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".pdf,.txt,.md,.docx,.csv,.json,.html,.htm"
            onChange={handleFileChange}
            aria-label={`Upload document to ${kb.name}`}
          />

          <button
            type="button"
            onClick={() => setConfirmKb(true)}
            className="lx-icon-btn lx-icon-btn--alarm"
            title="Delete knowledge base"
            aria-label={`Delete knowledge base ${kb.name}`}
          >
            <Trash2 size={15} strokeWidth={1.5} aria-hidden="true" />
          </button>

          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="lx-icon-btn"
            aria-expanded={isExpanded}
            aria-controls={`kb-documents-${kb.id}`}
            title={isExpanded ? 'Collapse documents' : 'Expand documents'}
          >
            {isExpanded ? (
              <ChevronUp size={16} strokeWidth={1.5} aria-hidden="true" />
            ) : (
              <ChevronDown size={16} strokeWidth={1.5} aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {uploadStatus && (
        <div className="border-b border-[color:var(--rule-faint)] px-5 py-2.5">
          <p className="lx-micro flex items-center gap-2">
            {uploadStatus === 'uploading' && (
              <>
                <Loader2 size={12} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
                Ingesting, parsing chunks and generating 384d dense embeddings…
              </>
            )}
            {uploadStatus === 'success' && (
              <>
                <Check size={12} strokeWidth={2} className="text-silver-300" aria-hidden="true" />
                Document indexed and ready for queries.
              </>
            )}
            {uploadStatus === 'error' && (
              <>
                <AlertTriangle size={12} strokeWidth={2} className="text-crimson-400" aria-hidden="true" />
                <span className="text-crimson-300">{uploadError}</span>
              </>
            )}
          </p>
        </div>
      )}

      {isExpanded && (
        <div id={`kb-documents-${kb.id}`} className="px-5 py-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <span className="lx-micro flex items-center gap-1.5">
              <FileText size={12} strokeWidth={1.5} aria-hidden="true" />
              Indexed documents ({documents.length})
            </span>
            <span className="lx-micro">
              Created {formatDistanceToNow(new Date(kb.created_at))} ago
            </span>
          </div>

          {docsLoading && (
            <div className="flex items-center justify-center gap-2 px-4 py-8">
              <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
              <span className="lx-micro">Querying the document registry…</span>
            </div>
          )}

          {!docsLoading && documents.length === 0 && (
            <div className="lx-empty">
              <FileText size={20} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
              <p className="lx-empty__title">No documents indexed yet</p>
              <p className="lx-empty__body">
                Upload a PDF, DOCX or text file to index it into this collection.
              </p>
            </div>
          )}

          {!docsLoading && documents.length > 0 && (
            <ul className="lx-list">
              {documents.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} onDelete={setConfirmDoc} />
              ))}
            </ul>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmKb}
        title="Delete knowledge base?"
        message={`"${kb.name}" and every document indexed into it will be removed permanently.`}
        confirmLabel="Delete"
        onCancel={() => setConfirmKb(false)}
        onConfirm={() => {
          setConfirmKb(false)
          deleteKbMutation.mutate(kb.id)
        }}
      />

      <ConfirmDialog
        open={!!confirmDoc}
        title="Remove document?"
        message={confirmDoc ? `"${confirmDoc.filename}" will be removed from this knowledge base.` : ''}
        confirmLabel="Remove"
        onCancel={() => setConfirmDoc(null)}
        onConfirm={() => {
          if (confirmDoc) deleteDocMutation.mutate(confirmDoc.id)
          setConfirmDoc(null)
        }}
      />
    </article>
  )
}
