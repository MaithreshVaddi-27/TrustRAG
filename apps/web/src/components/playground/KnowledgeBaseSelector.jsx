import { Database } from 'lucide-react'

export function KnowledgeBaseSelector({ kbId, setKbId, knowledgeBases = [], selectedKb, loading, disabled }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <label className="section-heading !mb-0" htmlFor="kb-select">Knowledge Base</label>
        {selectedKb && (
          <span className="text-[10px] text-slate-400 font-mono">
            {selectedKb.document_count ?? 0} docs
          </span>
        )}
      </div>
      <div className="relative">
        <Database size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <select
          id="kb-select"
          name="kbId"
          aria-label="Select Knowledge Base"
          value={kbId}
          onChange={e => setKbId(e.target.value)}
          className="w-full bg-surface-800 border border-slate-700/80 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50 appearance-none transition-colors"
          disabled={loading || disabled}
        >
          <option value="">— select a KB —</option>
          {knowledgeBases?.map(kb => (
            <option key={kb.id} value={kb.id}>
              {kb.name} ({kb.document_count ?? 0} docs)
            </option>
          ))}
        </select>
      </div>
      {selectedKb && selectedKb.document_count === 0 && (
        <p className="text-[10px] text-amber-400/90 leading-tight">
          ⚠️ Selected knowledge base contains 0 indexed documents. Upload documents in the Knowledge Bases tab.
        </p>
      )}
    </div>
  )
}