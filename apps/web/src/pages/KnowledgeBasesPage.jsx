import { Database, FolderPlus, Plus, Upload } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'

export default function KnowledgeBasesPage() {
  return (
    <AppLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Knowledge Bases</h1>
            <p className="text-slate-400 text-sm mt-1">Manage your document collections</p>
          </div>
          <button id="create-kb" className="btn-primary flex items-center gap-2">
            <Plus size={14} /> New Knowledge Base
          </button>
        </div>

        {/* Empty state — populated from API in Phase 3 */}
        <div className="glass-card p-12 flex flex-col items-center text-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-surface-800 border border-slate-700 flex items-center justify-center">
            <Database size={24} className="text-slate-500" />
          </div>
          <div>
            <p className="font-medium text-slate-300">No knowledge bases yet</p>
            <p className="text-sm text-slate-500 mt-1 max-w-xs">
              Create a knowledge base and upload PDF, TXT, or Markdown documents to get started.
            </p>
          </div>
          <button className="btn-primary flex items-center gap-2">
            <FolderPlus size={14} /> Create Knowledge Base
          </button>
        </div>

        {/* Supported formats reference */}
        <div className="glass-card p-4">
          <p className="section-heading">Supported Document Formats</p>
          <div className="flex gap-3 flex-wrap">
            {['PDF', 'TXT', 'Markdown (.md)'].map(fmt => (
              <div key={fmt} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 rounded-lg border border-slate-700 text-sm text-slate-300">
                <Upload size={12} className="text-primary-400" /> {fmt}
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-600 mt-3">Max file size: 20 MB. Chunked and indexed into Qdrant with 384-dim embeddings.</p>
        </div>
      </div>
    </AppLayout>
  )
}
