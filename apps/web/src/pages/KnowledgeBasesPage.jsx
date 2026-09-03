import { useState, useRef } from 'react'
import {
  Database, FolderPlus, Plus, Upload, Trash2, FileText, Loader2,
  File, CheckCircle2, AlertCircle, Search, ChevronDown, ChevronUp,
  HardDrive, ShieldCheck, Sparkles, AlertTriangle
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { kbService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'

export default function KnowledgeBasesPage() {
  const queryClient = useQueryClient()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newKbName, setNewKbName] = useState('')
  const [newKbDesc, setNewKbDesc] = useState('')
  const [searchTerm, setSearchTerm] = useState('')

  // Fetch KBs
  const { data: knowledgeBases = [], isLoading } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list
  })

  const [createErrorMsg, setCreateErrorMsg] = useState(null)

  // Create KB Mutation
  const createKbMutation = useMutation({
    mutationFn: kbService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
      setIsCreateModalOpen(false)
      setNewKbName('')
      setNewKbDesc('')
      setCreateErrorMsg(null)
    },
    onError: (error) => {
      setCreateErrorMsg(error.message || 'Failed to create knowledge base')
    }
  })

  const handleCreateSubmit = (e) => {
    e.preventDefault()
    if (!newKbName.trim()) return
    createKbMutation.mutate({ name: newKbName, description: newKbDesc })
  }

  const filteredKbs = knowledgeBases.filter(kb =>
    !searchTerm ||
    kb.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (kb.description && kb.description.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  return (
    <AppLayout>
      <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-8 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-xs font-mono text-cyan-300 mb-2">
              <HardDrive size={12} />
              <span>Multi-Tenant Vector Index</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Knowledge <span className="text-gradient">Bases</span>
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Document repositories partitioned with multi-dimensional dense (384d / 768d) & sparse BM25 indexing.
            </p>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="btn-primary shrink-0 self-start sm:self-auto"
          >
            <Plus size={16} />
            <span>New Knowledge Base</span>
          </button>
        </div>

        {/* Search & Filter Bar */}
        {!isLoading && knowledgeBases.length > 0 && (
          <div className="glass-card p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="relative flex-1 max-w-md">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter knowledge bases by name or topic..."
                className="w-full bg-surface-800/80 border border-slate-700/80 rounded-xl pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/40 transition-colors"
              />
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
              <span>{filteredKbs.length} of {knowledgeBases.length} collections</span>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="p-16 flex flex-col items-center justify-center space-y-3">
            <Loader2 size={32} className="animate-spin text-primary-400" />
            <p className="text-sm font-mono text-slate-400">Querying cluster collections...</p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && knowledgeBases.length === 0 && (
          <div className="glass-card p-12 text-center space-y-4 border-dashed border-slate-800">
            <div className="w-14 h-14 rounded-2xl bg-surface-800 border border-slate-700 mx-auto flex items-center justify-center text-slate-500">
              <Database size={28} />
            </div>
            <div className="space-y-1 max-w-md mx-auto">
              <h3 className="text-base font-bold text-white">No knowledge bases yet</h3>
              <p className="text-xs text-slate-400">
                Create your first knowledge base to upload documents, generate dense embeddings, and run grounded queries.
              </p>
            </div>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="btn-primary inline-flex"
            >
              <Plus size={16} /> Create Collection
            </button>
          </div>
        )}

        {/* Knowledge Base Cards Grid */}
        <div className="grid grid-cols-1 gap-6">
          {filteredKbs.map((kb) => (
            <KnowledgeBaseCard key={kb.id} kb={kb} />
          ))}
        </div>

        {/* Supported formats reference */}
        <div className="glass-card p-6 border-l-4 border-l-primary-500/80">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={16} className="text-primary-400" />
            <p className="font-bold text-slate-200 text-sm">Supported Document Formats & Ingestion Pipeline</p>
          </div>
          <div className="flex gap-2.5 flex-wrap">
            {['PDF (.pdf)', 'Word (.docx)', 'Markdown (.md)', 'Text (.txt)', 'CSV (.csv)', 'JSON (.json)', 'HTML (.html)'].map(fmt => (
              <div key={fmt} className="flex items-center gap-2 px-3 py-1.5 bg-surface-800/80 rounded-xl border border-slate-700/80 text-xs font-mono text-slate-300">
                <File size={13} className="text-cyan-400" /> {fmt}
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-4 leading-relaxed flex items-center gap-2">
            <ShieldCheck size={14} className="text-emerald-400 shrink-0" />
            Documents undergo automated Porter stemming, zone-weighting (Title: 3.0x, Abstract: 2.0x), and are indexed with Google Gemini 384d Matryoshka dense embeddings.
          </p>
        </div>
      </div>

      {/* Create KB Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-surface-900 border border-slate-700/80 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-slide-up">
            <div className="p-5 border-b border-slate-800 flex justify-between items-center bg-surface-800/40">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <FolderPlus size={18} className="text-primary-400" />
                Create Knowledge Base
              </h2>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-500 hover:text-white transition-colors text-sm font-mono"
              >
                esc
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-6 space-y-5">
              {createErrorMsg && (
                <div role="alert" className="p-3 bg-red-950/60 border border-red-800 rounded-xl text-xs text-red-300 flex items-start gap-2">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{createErrorMsg}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Knowledge Base Name *
                </label>
                <input
                  type="text"
                  required
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  placeholder="e.g. Legal Contracts 2026, Clinical Notes"
                  className="w-full bg-surface-800/90 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/40 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Description
                </label>
                <textarea
                  value={newKbDesc}
                  onChange={(e) => setNewKbDesc(e.target.value)}
                  placeholder="Purpose, domain context, and expected document types..."
                  rows={3}
                  className="w-full bg-surface-800/90 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/40 transition-colors resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createKbMutation.isPending || !newKbName.trim()}
                  className="btn-primary text-xs"
                >
                  {createKbMutation.isPending ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create Collection'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

function KnowledgeBaseCard({ kb }) {
  const queryClient = useQueryClient()
  const [isExpanded, setIsExpanded] = useState(true)
  const fileInputRef = useRef(null)

  // Query documents inside this KB
  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents', kb.id],
    queryFn: () => kbService.listDocuments(kb.id),
    enabled: isExpanded,
  })

  // Delete KB Mutation
  const deleteKbMutation = useMutation({
    mutationFn: kbService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
    }
  })

  // Delete Document Mutation
  const deleteDocMutation = useMutation({
    mutationFn: (docId) => kbService.deleteDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', kb.id] })
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
    }
  })

  // Upload Document Mutation
  const [uploadStatus, setUploadStatus] = useState(null)
  const [uploadError, setUploadError] = useState(null)

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
    }
  })

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    uploadDocMutation.mutate(file)
  }

  return (
    <div className="glass-card overflow-hidden border-slate-800 hover:border-slate-700/80 transition-all">
      {/* Top Header of the KB */}
      <div className="p-5 sm:p-6 bg-surface-900/60 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
              <Database size={18} />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-lg tracking-tight truncate">{kb.name}</h3>
              <p className="text-xs text-slate-400 line-clamp-1">{kb.description || 'No description provided.'}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadDocMutation.isPending}
            className="btn-primary text-xs py-2 px-3.5"
          >
            {uploadDocMutation.isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>Indexing...</span>
              </>
            ) : (
              <>
                <Upload size={14} />
                <span>Upload Document</span>
              </>
            )}
          </button>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".pdf,.txt,.md,.docx,.csv,.json,.html,.htm"
            onChange={handleFileChange}
          />

          <button
            onClick={() => {
              if (confirm(`Are you sure you want to delete "${kb.name}"? All points in Qdrant will be purged.`)) {
                deleteKbMutation.mutate(kb.id)
              }
            }}
            className="p-2 rounded-xl text-slate-500 hover:text-red-400 hover:bg-surface-800 transition-colors border border-slate-800"
            title="Delete Knowledge Base"
          >
            <Trash2 size={16} />
          </button>

          <button
            onClick={() => setIsExpanded(prev => !prev)}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-800 transition-colors border border-slate-800"
            title={isExpanded ? 'Collapse documents' : 'Expand documents'}
          >
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Upload status banner */}
      {uploadStatus && (
        <div className="px-6 py-2.5 bg-surface-800/80 border-b border-slate-800 flex items-center justify-between text-xs animate-fade-in">
          {uploadStatus === 'uploading' && (
            <span className="text-cyan-400 flex items-center gap-2 font-mono">
              <Loader2 size={13} className="animate-spin" />
              Ingesting, parsing chunks, and generating 384d Gemini embeddings...
            </span>
          )}
          {uploadStatus === 'success' && (
            <span className="text-emerald-400 flex items-center gap-2 font-mono">
              <CheckCircle2 size={14} />
              Document successfully indexed into Qdrant Cloud!
            </span>
          )}
          {uploadStatus === 'error' && (
            <span className="text-red-400 flex items-center gap-2 font-mono">
              <AlertCircle size={14} />
              {uploadError}
            </span>
          )}
        </div>
      )}

      {/* Expandable Document Indexing Drawer */}
      {isExpanded && (
        <div className="p-5 sm:p-6 space-y-4 animate-fade-in">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1.5">
              <FileText size={13} className="text-cyan-400" />
              Indexed Documents ({documents.length})
            </span>
            <span>Created {formatDistanceToNow(new Date(kb.created_at))} ago</span>
          </div>

          {docsLoading && (
            <div className="p-8 text-center text-xs font-mono text-slate-500 flex items-center justify-center gap-2">
              <Loader2 size={15} className="animate-spin text-primary-400" />
              Querying document registry...
            </div>
          )}

          {!docsLoading && documents.length === 0 && (
            <div className="p-8 rounded-xl bg-surface-800/30 border border-slate-800 text-center space-y-2">
              <p className="text-xs font-medium text-slate-300">No documents indexed in this knowledge base</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                Click &quot;Upload Document&quot; to index your first PDF, DOCX, or text file into the vector cluster.
              </p>
            </div>
          )}

          {!docsLoading && documents.length > 0 && (
            <div className="divide-y divide-slate-800/60 rounded-xl border border-slate-800/80 bg-surface-800/20 overflow-hidden">
              {documents.map((doc) => {
                const isCompleted = doc.status === 'completed' || doc.ingestion_status === 'completed' || !doc.status
                const isFailed = doc.status === 'failed' || doc.ingestion_status === 'failed'

                return (
                  <div
                    key={doc.id}
                    className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-800/40 transition-colors"
                  >
                    <div className="flex items-start sm:items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-surface-800 border border-slate-700 flex items-center justify-center text-primary-400 shrink-0">
                        <FileText size={16} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-200 truncate">{doc.filename}</p>
                        <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500 pt-0.5">
                          <span>{doc.chunk_count !== undefined ? `${doc.chunk_count} chunks` : 'Indexed chunks'}</span>
                          <span>•</span>
                          <span>{doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'PDF'}</span>
                          <span>•</span>
                          <span>{formatDistanceToNow(new Date(doc.created_at))} ago</span>
                        </div>
                      </div>
                    </div>

                    {/* Right side: Indexing Status Badge & Delete */}
                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      {isCompleted ? (
                        <span className="badge-supported text-[11px] font-mono">
                          <CheckCircle2 size={13} />
                          Indexed & Ready
                        </span>
                      ) : isFailed ? (
                        <span className="badge-contradicted text-[11px] font-mono" title={doc.error_message || 'Ingestion failed'}>
                          <AlertTriangle size={13} />
                          Failed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/60">
                          <Loader2 size={12} className="animate-spin" />
                          Indexing...
                        </span>
                      )}

                      <button
                        onClick={() => {
                          if (confirm(`Remove "${doc.filename}" from this knowledge base?`)) {
                            deleteDocMutation.mutate(doc.id)
                          }
                        }}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-surface-800 transition-colors"
                        title="Delete Document"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
