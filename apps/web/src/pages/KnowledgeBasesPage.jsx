import { useState, useRef } from 'react'
import { Database, FolderPlus, Plus, Upload, Trash2, FileText, Loader2, File, CheckCircle, AlertCircle } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { kbService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'

export default function KnowledgeBasesPage() {
  const queryClient = useQueryClient()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newKbName, setNewKbName] = useState('')
  const [newKbDesc, setNewKbDesc] = useState('')
  
  // File upload state per KB
  const fileInputRefs = useRef({})
  const [uploadingKbId, setUploadingKbId] = useState(null)
  const [uploadStatus, setUploadStatus] = useState(null) // null, 'success', 'error'

  // Fetch KBs
  const { data: knowledgeBases, isLoading } = useQuery({
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

  // Delete KB Mutation
  const deleteKbMutation = useMutation({
    mutationFn: kbService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
    }
  })

  const [uploadErrorMsg, setUploadErrorMsg] = useState(null)

  // Upload Document Mutation
  const uploadDocMutation = useMutation({
    mutationFn: ({ kbId, file }) => kbService.uploadDocument(kbId, file),
    onMutate: ({ kbId }) => {
      setUploadingKbId(kbId)
      setUploadStatus(null)
      setUploadErrorMsg(null)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
      setUploadStatus('success')
      // Clear status after 3s
      setTimeout(() => {
        setUploadingKbId(null)
        setUploadStatus(null)
      }, 3000)
    },
    onError: (error) => {
      console.error("Upload failed", error)
      let detail = error.message || 'Upload failed'
      setUploadErrorMsg(String(detail))
      setUploadStatus('error')
      setTimeout(() => {
        setUploadingKbId(null)
        setUploadStatus(null)
        setUploadErrorMsg(null)
      }, 6000)
    }
  })

  const handleCreateSubmit = (e) => {
    e.preventDefault()
    if (!newKbName.trim()) return
    createKbMutation.mutate({ name: newKbName, description: newKbDesc })
  }

  const triggerFileUpload = (kbId) => {
    if (fileInputRefs.current[kbId]) {
      fileInputRefs.current[kbId].click()
    }
  }

  const handleFileChange = (e, kbId) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // Reset the input so the same file can be selected again if needed
    e.target.value = ''
    
    uploadDocMutation.mutate({ kbId, file })
  }

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Knowledge Bases</h1>
            <p className="text-slate-400 text-sm mt-1">Manage your document collections</p>
          </div>
          <button 
            onClick={() => setIsCreateModalOpen(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> New Knowledge Base
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center items-center p-12">
            <Loader2 className="animate-spin text-primary-500" size={32} />
          </div>
        )}

        {/* Empty State */}
        {!isLoading && knowledgeBases?.length === 0 && (
          <div className="glass-card p-12 flex flex-col items-center text-center gap-4 border-dashed border-2 border-slate-700/50">
            <div className="w-16 h-16 rounded-2xl bg-surface-800/80 border border-slate-700 flex items-center justify-center shadow-inner">
              <Database size={28} className="text-slate-400" />
            </div>
            <div>
              <p className="text-lg font-medium text-slate-200">No knowledge bases yet</p>
              <p className="text-sm text-slate-400 mt-1.5 max-w-sm">
                Create a knowledge base and upload PDF, TXT, or Markdown documents to get started.
              </p>
            </div>
            <button 
              onClick={() => setIsCreateModalOpen(true)}
              className="btn-primary flex items-center gap-2 mt-2"
            >
              <FolderPlus size={16} /> Create Knowledge Base
            </button>
          </div>
        )}

        {/* Knowledge Bases Grid */}
        {!isLoading && knowledgeBases?.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {knowledgeBases.map((kb) => (
              <div key={kb.id} className="glass-card flex flex-col hover:border-primary-500/30 transition-all duration-300 group">
                <div className="p-5 flex-1">
                  <div className="flex justify-between items-start mb-3">
                    <div className="w-10 h-10 rounded-xl bg-surface-800 border border-slate-700 flex items-center justify-center text-primary-400">
                      <Database size={18} />
                    </div>
                    <button 
                      onClick={() => {
                        if(confirm('Are you sure you want to delete this knowledge base? All documents inside will be lost forever.')) {
                          deleteKbMutation.mutate(kb.id)
                        }
                      }}
                      className="text-slate-500 hover:text-red-400 transition-colors p-1.5 rounded-lg hover:bg-surface-800 opacity-0 group-hover:opacity-100"
                      title="Delete Knowledge Base"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  
                  <h3 className="font-semibold text-slate-100 text-lg mb-1 line-clamp-1">{kb.name}</h3>
                  <p className="text-sm text-slate-400 line-clamp-2 mb-4 h-10">
                    {kb.description || 'No description provided.'}
                  </p>
                  
                  <div className="flex items-center gap-4 text-xs text-slate-500 font-medium">
                    <div className="flex items-center gap-1.5">
                      <FileText size={14} />
                      {kb.document_count || 0} {(kb.document_count === 1) ? 'doc' : 'docs'}
                    </div>
                    <div className="flex items-center gap-1.5">
                      Created {formatDistanceToNow(new Date(kb.created_at))} ago
                    </div>
                  </div>
                </div>

                <div className="border-t border-slate-700/50 p-3 bg-surface-800/30 flex justify-between items-center rounded-b-xl">
                  {uploadingKbId === kb.id ? (
                    <div className="flex items-center gap-2 text-sm font-medium w-full justify-center py-1.5">
                      {uploadStatus === 'success' ? (
                        <span className="text-green-400 flex items-center gap-1.5"><CheckCircle size={14} /> Uploaded!</span>
                      ) : uploadStatus === 'error' ? (
                        <span className="text-red-400 flex items-center gap-1.5 text-xs text-center line-clamp-1" title={typeof uploadErrorMsg === 'string' ? uploadErrorMsg : 'Failed'}><AlertCircle size={14} className="shrink-0" /> {typeof uploadErrorMsg === 'string' ? uploadErrorMsg : 'Failed'}</span>
                      ) : (
                        <span className="text-primary-400 flex items-center gap-1.5"><Loader2 size={14} className="animate-spin" /> Uploading...</span>
                      )}
                    </div>
                  ) : (
                    <button 
                      onClick={() => triggerFileUpload(kb.id)}
                      className="w-full flex items-center justify-center gap-2 text-sm font-medium text-slate-300 hover:text-white bg-surface-800 hover:bg-surface-700 border border-slate-700 hover:border-slate-600 transition-colors py-2 rounded-lg"
                    >
                      <Upload size={14} /> Upload Document
                    </button>
                  )}
                  {/* Hidden file input bound to this specific KB */}
                  <input 
                    type="file" 
                    ref={el => fileInputRefs.current[kb.id] = el} 
                    className="hidden" 
                    accept=".pdf,.txt,.md"
                    onChange={(e) => handleFileChange(e, kb.id)}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Supported formats reference */}
        <div className="glass-card p-5 mt-8 border-l-4 border-l-primary-500/50">
          <p className="font-semibold text-slate-200 mb-3">Supported Document Formats</p>
          <div className="flex gap-3 flex-wrap">
            {['PDF', 'TXT', 'Markdown (.md)'].map(fmt => (
              <div key={fmt} className="flex items-center gap-2 px-3 py-1.5 bg-surface-800 rounded-lg border border-slate-700 text-sm text-slate-300 shadow-sm">
                <File size={14} className="text-primary-400" /> {fmt}
              </div>
            ))}
          </div>
          <p className="text-sm text-slate-400 mt-3 flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary-500"></span>
            Max file size: 20 MB. Documents are chunked and indexed into Qdrant with 384-dim embeddings.
          </p>
        </div>
      </div>

      {/* Create KB Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-surface-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-slate-800 flex justify-between items-center bg-surface-800/30">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FolderPlus size={18} className="text-primary-400" />
                Create Knowledge Base
              </h2>
            </div>
            
            <form onSubmit={handleCreateSubmit} className="p-5 space-y-5">
              {createErrorMsg && (
                <div role="alert" className="p-3 bg-red-950/60 border border-red-800 rounded-xl text-xs text-red-300 flex items-start justify-between gap-2">
                  <span>{createErrorMsg}</span>
                  <button
                    type="button"
                    onClick={() => setCreateErrorMsg(null)}
                    aria-label="Dismiss error"
                    className="text-red-400 hover:text-red-200 text-sm font-bold leading-none shrink-0"
                  >
                    &times;
                  </button>
                </div>
              )}
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Name</label>
                <input 
                  type="text" 
                  autoFocus
                  required
                  placeholder="e.g. HR Policies 2026"
                  className="w-full bg-surface-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all placeholder:text-slate-600"
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Description (Optional)</label>
                <textarea 
                  placeholder="What kind of documents will this contain?"
                  className="w-full bg-surface-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all placeholder:text-slate-600 resize-none h-24"
                  value={newKbDesc}
                  onChange={(e) => setNewKbDesc(e.target.value)}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button 
                  type="button" 
                  onClick={() => setIsCreateModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl font-medium text-slate-300 hover:text-white bg-surface-800 hover:bg-surface-700 border border-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={createKbMutation.isPending || !newKbName.trim()}
                  className="flex-1 btn-primary py-2.5 rounded-xl font-medium flex justify-center items-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {createKbMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  )
}
