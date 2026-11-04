import { Globe, Sparkles, Zap } from 'lucide-react'

export function WebSearchToggle({ enableWebSearch, setEnableWebSearch, loading, selectedProvider }) {
  const isLocalProvider = ['ollama', 'llama_cpp', 'mlx'].includes(selectedProvider)

  return (
    <div
      className={`rounded-2xl border p-3.5 space-y-3 transition-all duration-200 ${
        enableWebSearch
          ? 'border-cyan-500/50 bg-gradient-to-b from-cyan-950/25 to-surface-900/90 shadow-sm shadow-cyan-950/30'
          : 'border-slate-800 bg-surface-850/60 hover:border-slate-700/80'
      }`}
    >
      {/* Header Row: Icon, Title, Badge & Custom Accessible Switch */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
              enableWebSearch
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.25)]'
                : 'bg-surface-800 text-slate-400 border border-slate-700/60'
            }`}
          >
            <Globe className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span
                id="web-search-grounding-label"
                onClick={() => !loading && setEnableWebSearch(!enableWebSearch)}
                className="text-xs font-semibold text-slate-200 cursor-pointer select-none truncate"
              >
                Web Search Grounding
              </span>
              <span className="font-mono text-[9px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider bg-surface-900 text-cyan-400 border border-cyan-500/30 shrink-0">
                MCP
              </span>
            </div>
            <p className="text-[10px] text-slate-400 truncate">
              {enableWebSearch
                ? 'Live internet evidence via Model Context Protocol'
                : 'Local-only RAG · Knowledge base isolated'}
            </p>
          </div>
        </div>

        {/* Custom Toggle Switch */}
        <button
          type="button"
          role="switch"
          id="web-search-toggle"
          aria-checked={enableWebSearch}
          aria-labelledby="web-search-grounding-label"
          aria-label="Toggle Web Search Grounding via MCP"
          disabled={loading}
          onClick={() => setEnableWebSearch(!enableWebSearch)}
          className={`relative inline-flex h-6 w-11 p-0.5 shrink-0 cursor-pointer rounded-full border transition-all duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:ring-offset-2 focus:ring-offset-surface-950 disabled:opacity-50 disabled:cursor-not-allowed ${
            enableWebSearch
              ? 'bg-cyan-500 border-cyan-400/80 shadow-[0_0_12px_rgba(6,182,212,0.35)]'
              : 'bg-surface-800 border-slate-700/80 hover:border-slate-600'
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
              enableWebSearch ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>
      </div>

      {/* Expanded MCP Configuration Details */}
      {enableWebSearch && (
        <div className="pt-2.5 border-t border-slate-800/80 space-y-2.5 animate-fade-in">
          {/* Provider Card */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-surface-900/80 border border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded-lg flex items-center justify-center bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                <Zap size={12} />
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-200 flex items-center gap-1.5">
                  Tavily AI Search
                  <span className="text-[9px] font-mono text-cyan-400 font-normal">Sole MCP Web Provider</span>
                </div>
                <div className="text-[10px] text-slate-400">High-precision parsed content for RAG citations</div>
              </div>
            </div>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Active
            </span>
          </div>

          {/* MCP Tools Available */}
          <div className="px-2.5 py-2 rounded-xl bg-surface-900/50 border border-slate-800/60 flex items-center justify-between text-[10px]">
            <span className="text-slate-400 font-medium">Active MCP Tools:</span>
            <div className="flex items-center gap-1.5 font-mono text-[9px] text-cyan-300">
              <span className="bg-surface-800/90 px-2 py-0.5 rounded-md border border-slate-700/60">tavily_search</span>
              <span className="bg-surface-800/90 px-2 py-0.5 rounded-md border border-slate-700/60">verify_claim</span>
            </div>
          </div>

          {isLocalProvider && (
            <div className="flex items-start gap-2 p-2.5 rounded-xl bg-cyan-950/30 border border-cyan-800/30 text-[10px] text-cyan-200/90 leading-relaxed">
              <Sparkles size={13} className="text-cyan-400 mt-0.5 shrink-0" />
              <span>
                Autonomous Tool Calling: The agent invokes web retrieval when knowledge base confidence is below 75%.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}