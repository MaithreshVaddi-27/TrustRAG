import { Globe, Sparkles } from 'lucide-react'

export function WebSearchToggle({ enableWebSearch, setEnableWebSearch, loading, selectedProvider }) {
  const isLocalProvider = ['ollama', 'llama_cpp', 'mlx'].includes(selectedProvider)

  return (
    <div className={`rounded-xl border p-3.5 space-y-3 transition-all shadow-sm ${
      enableWebSearch
        ? 'border-cyan-500/60 bg-cyan-950/20 ring-1 ring-cyan-500/20'
        : 'border-slate-800 bg-surface-850/60 hover:border-slate-700/80'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <input
            type="checkbox"
            id="web-search-toggle"
            checked={enableWebSearch}
            onChange={e => setEnableWebSearch(e.target.checked)}
            disabled={loading}
            className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-surface-900 text-cyan-500 focus:ring-cyan-500 cursor-pointer accent-cyan-500"
          />
          <label htmlFor="web-search-toggle" className="cursor-pointer select-none space-y-0.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <Globe className={`w-3.5 h-3.5 ${enableWebSearch ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>Enable Web Search Grounding</span>
              <span className="rounded bg-cyan-950/80 px-1.5 py-0.5 text-[10px] font-medium text-cyan-300 border border-cyan-700/40">
                MCP Tool
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {enableWebSearch
                ? 'Active: Live internet grounding will be queried via MCP.'
                : 'Unchecked: 100% private local RAG limited to your knowledge base.'}
            </p>
          </label>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] font-mono shrink-0 border ${
          enableWebSearch
            ? 'bg-cyan-950 text-cyan-300 border-cyan-700/60 font-semibold shadow-sm'
            : 'bg-slate-900 text-slate-400 border-slate-800'
        }`}>
          {enableWebSearch ? 'WEB SEARCH ENABLED' : 'LOCAL ONLY'}
        </span>
      </div>

      {enableWebSearch && (
        <div className="pt-2 border-t border-slate-800/80 space-y-2 animate-fade-in">
          <span className="text-[11px] text-slate-300 block font-medium">MCP Search Engine:</span>
          <div className="flex items-center gap-1.5 text-[11px] py-1 px-1.5 rounded font-medium bg-primary-600/30 text-primary-300 border border-primary-500/40 shadow-sm w-fit">
            ⚡ Tavily (AI)
          </div>
          <p className="text-[10px] text-slate-400 leading-tight">
            High-accuracy AI RAG search with clean parsed content — the sole web provider.
          </p>

          {isLocalProvider && (
            <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 text-cyan-300 font-medium">
                  <Sparkles size={12} className="text-cyan-400" />
                  <span>MCP Tool Grounding</span>
                </div>
                <span className="px-1.5 py-0.5 rounded bg-cyan-950/90 text-cyan-300 border border-cyan-700/50 text-[10px] font-mono">
                  Active
                </span>
              </div>
              <p className="text-[10px] text-slate-400 leading-relaxed">
                Connected to local MCP tool suite: <code className="text-cyan-400 font-mono">trustrag_search</code>, <code className="text-cyan-400 font-mono">tavily_search</code>, & <code className="text-cyan-400 font-mono">verify_claim</code>.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}