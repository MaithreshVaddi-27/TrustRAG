import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Loader2, Check, AlertTriangle, FileText } from 'lucide-react'
import ConfirmDialog from '@/components/kb/ConfirmDialog'
import DocumentRow from './DocumentRow'
import { kbService } from '@/services/api'

/**
 * DocumentTable — the documents indexed into one collection.
 *
 * Upload lives here, not on every collection row. One collection is open
 * at a time, so there is exactly one upload control on the screen and one
 * place where ingestion state is reported.
 *
 * The document list is fetched only when the collection is opened, so a
 * workspace with forty collections does not issue forty document queries
 * on load.
 */
const ACCEPT = '.pdf,.txt,.md,.docx,.csv,.json,.html,.htm'
const FORMATS = ['PDF', 'DOCX', 'MD', 'TXT', 'CSV', 'JSON', 'HTML']

export default function DocumentTable({ kb }) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef(null)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)

  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents', kb.id],
    queryFn: () => kbService.listDocuments(kb.id),
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
    },
    onError: (err) => {
      setUploadStatus('error')
      setUploadError(err.message || 'Upload failed')
    },
  })

  const handleFileChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    event.target.value = ''
    uploadDocMutation.mutate(file)
  }

  return (
    <div className="px-5 py-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
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
            accept={ACCEPT}
            onChange={handleFileChange}
            aria-label={`Upload a document to ${kb.name}`}
          />

          <span className="lx-micro">{FORMATS.join(' · ')}</span>
        </div>

        <span className="lx-micro">
          {documents.length} {documents.length === 1 ? 'document' : 'documents'}
        </span>
      </div>

      <div aria-live="polite">
        {uploadStatus === 'uploading' && (
          <p className="lx-micro mb-3 flex items-center gap-2">
            <Loader2 size={12} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
            Uploading and queuing the document for indexing…
          </p>
        )}

        {uploadStatus === 'success' && (
          <p className="lx-micro mb-3 flex items-center gap-2">
            <Check size={12} strokeWidth={2} className="text-silver-300" aria-hidden="true" />
            Document uploaded — chunking and embedding it now
          </p>
        )}

        {uploadStatus === 'error' && (
          <p className="lx-micro mb-3 flex items-center gap-2">
            <AlertTriangle size={12} strokeWidth={2} className="text-crimson-400" aria-hidden="true" />
            <span style={{ color: 'var(--color-crimson-300)' }}>{uploadError}</span>
          </p>
        )}
      </div>

      {docsLoading ? (
        <div className="flex items-center justify-center gap-2 px-4 py-8">
          <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
          <span className="lx-micro">Querying the document registry…</span>
        </div>
      ) : documents.length === 0 ? (
        <div className="lx-empty">
          <FileText size={20} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
          <p className="lx-empty__title">No documents indexed yet</p>
          <p className="lx-empty__body">
            Upload a file and the pipeline will chunk it, embed it, and make it
            queryable.
          </p>
        </div>
      ) : (
        <ul className="lx-list">
          {documents.map((doc) => (
            <DocumentRow key={doc.id} doc={doc} onDelete={setPendingDelete} />
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Remove document?"
        message={
          pendingDelete
            ? `"${pendingDelete.filename}" will be removed from ${kb.name} and will no longer be retrievable.`
            : ''
        }
        confirmLabel="Remove"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) deleteDocMutation.mutate(pendingDelete.id)
          setPendingDelete(null)
        }}
      />
    </div>
  )
}
