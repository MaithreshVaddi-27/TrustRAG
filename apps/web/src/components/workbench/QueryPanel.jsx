import { 
  Database, Loader2, Zap, Globe, Sparkles, Cpu, 
  RotateCcw, AlertTriangle, CornerDownLeft, Layers
} from 'lucide-react'
import { motion } from 'motion/react'

const SAMPLE_PRESETS = [
  "What is the cancellation and refund policy?",
  "Are there any conflicting coverage terms or exclusions?",
  "Summarize key compliance obligations with exact citations",
]

export function QueryPanel({
  query,
  setQuery,
  kbId,
  setKbId,
  loading,
  handleSubmit,
  handleReset,
  handlePresetSelect,
  errorMsg,
  setErrorMsg,
  selectedProvider,
  setSelectedProvider,
  selectedModel,
  setSelectedModel,
  selectedEmbeddingProvider,
  setSelectedEmbeddingProvider,
  selectedEmbeddingModel,
  setSelectedEmbeddingModel,
  enableWebSearch,
  setEnableWebSearch,
  webSearchProvider,
  setWebSearchProvider,
  providersData,
  userTouchedEmbeddingRef,
  elapsedSec,
  activeProviderInfo,
  activeEmbeddingProviderInfo,
  availableModels,
  availableEmbeddingModels,
  selectedKb,
  knowledgeBases,
}) {
  const handleProviderChange = (providerKey) => {
    setSelectedProvider(providerKey)
    const prov = providersData?.providers?.[providerKey]
    if (prov?.default_model) {
      setSelectedModel(prov.default_model)
    } else if (providerKey === 'ollama') {
      setSelectedModel('granite4.2:3b-q4_K_M')
    } else if (providerKey === 'llama_cpp') {
      setSelectedModel('ibm-granite/granite-4.2-3b-GGUF:Q4_K_M')
    } else if (providerKey === 'gemini') {
      setSelectedModel('gemini-3.5-flash-lite')
    } else if (providerKey === 'nvidia') {
      setSelectedModel('meta/llama-3.3-70b-instruct')
    }
  }

  const handleEmbeddingProviderChange = (providerKey) => {
    setSelectedEmbeddingProvider(providerKey)
    userTouchedEmbeddingRef.current = true
    const prov = providersData?.embedding_providers?.[providerKey]
    if (prov?.default_model) {
      setSelectedEmbeddingModel(prov.default_model)
    } else if (prov?.models?.[0]?.id) {
      setSelectedEmbeddingModel(prov.models[0].id)
    }
  }

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="w-full md:w-[330px] lg:w-[370px] xl:w-[410px] shrink-0 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col bg-surface-900/60 backdrop-blur-md h-auto md:h-full overflow-hidden">
      <div className="p-4 border-b border-slate-800 shrink-0 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-white flex items-center gap-2 text-sm">
            <span className="p-1 rounded-md bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
              <Zap size={14} />
            </span>
            <span>Playground</span>
          </h2>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <p className="text-[11px] text-slate-400 font-medium">Reliability & Provenance Workbench</p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleReset}
          disabled={loading}
          title="Reset query and results (Clear)"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-800 rounded-lg border border-slate-800 transition-colors"
        >
          <RotateCcw size={13} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="p-4 space-y-4 flex-1 min-h-0 overflow-y-auto">
          {errorMsg && (
            <div role="alert" className="p-3 bg-red-950/70 border border-red-800/80 rounded-xl text-xs text-red-300 flex items-start justify-between gap-2 shadow-glow-crimson animate-fade-in">
              <div className="flex items-start gap-2">
                <AlertTriangle size={14} className="shrink-0 mt-0.5 text-red-400" />
                <span>{errorMsg}</span>
              </div>
              <button
                type="button"
                onClick={() => setErrorMsg('')}
                aria-label="Dismiss error"
                className="text-red-400 hover:text-red-200 text-sm font-bold leading-none shrink-0"
              >
                &times;
              </button>
            </div>
          )}

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
                value={kbId}
                onChange={e => setKbId(e.target.value)}
                className="w-full bg-surface-800 border border-slate-700/80 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50 appearance-none transition-colors"
                disabled={loading}
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

          <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                <Cpu className="w-3.5 h-3.5 text-primary-400" />
                <span>AI Engine</span>
              </label>
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${
                activeProviderInfo?.connected
                  ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
                  : 'bg-amber-950/80 text-amber-400 border border-amber-800/40'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${activeProviderInfo?.connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                {activeProviderInfo?.connected ? 'Connected' : 'Standby'}
              </span>
            </div>

            {providersData?.hardware && (
              <div className="p-2 rounded-lg bg-surface-900 border border-slate-800 flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 text-slate-300">
                  <Zap size={13} className={providersData.hardware.accelerator === 'mps' ? 'text-amber-400' : 'text-cyan-400'} />
                  <span>
                    <strong className="text-slate-200">
                      {providersData.hardware.accelerator === 'mps' ? 'Metal (MPS)' : (providersData.hardware.accelerator === 'cuda' ? 'CUDA GPU' : 'CPU')}
                    </strong>
                    {' '}&bull; {providersData.hardware.memory?.total_gb}GB RAM
                  </span>
                </div>
                <span className="text-[10px] text-cyan-400 font-mono">
                  Target: {providersData.hardware.recommendations?.primary_llm?.split(':')[0]}
                </span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-1.5 bg-surface-900 p-1 rounded-lg border border-slate-800">
              <motion.button
                type="button"
                onClick={() => handleProviderChange('ollama')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedProvider === 'ollama'
                    ? 'bg-primary-600/30 text-primary-200 border border-primary-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>Ollama</span>
                <span className="text-[10px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-emerald-400 font-mono">:11434</span>
              </motion.button>
              <motion.button
                type="button"
                onClick={() => handleProviderChange('llama_cpp')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedProvider === 'llama_cpp'
                    ? 'bg-cyan-600/30 text-cyan-200 border border-cyan-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>llama.cpp</span>
                <span className="text-[10px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-cyan-400 font-mono">:8081</span>
              </motion.button>
              <motion.button
                type="button"
                onClick={() => handleProviderChange('gemini')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedProvider === 'gemini'
                    ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>Gemini</span>
                <span className="text-[10px] text-slate-500">Cloud</span>
              </motion.button>
              <motion.button
                type="button"
                onClick={() => handleProviderChange('nvidia')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedProvider === 'nvidia'
                    ? 'bg-purple-600/30 text-purple-200 border border-purple-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>NVIDIA</span>
                <span className="text-[10px] text-slate-500">Cloud</span>
              </motion.button>
            </div>

            <div className="space-y-1 pt-1 border-t border-slate-800">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-medium">Model:</span>
                <span className="font-mono text-[10px] text-slate-500">
                  {selectedProvider === 'ollama' ? ':11434' : (selectedProvider === 'llama_cpp' ? ':8081' : '')}
                </span>
              </div>
              <div className="relative">
                <select
                  value={selectedModel}
                  onChange={e => setSelectedModel(e.target.value)}
                  disabled={loading}
                  className="w-full bg-surface-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary-500/50">
                {availableModels.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
                </select>
              </div>
            </div>

            {(selectedProvider === 'ollama' || selectedProvider === 'llama_cpp') && (
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
                  Connected to local MCP tool suite: <code className="text-cyan-400 font-mono">trustrag_search</code>, <code className="text-cyan-400 font-mono">duckduckgo_search</code>, & <code className="text-cyan-400 font-mono">verify_claim</code>.
                </p>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>Dense Embedding Model</span>
              </label>
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${
                activeEmbeddingProviderInfo?.connected
                  ? 'bg-cyan-950/80 text-cyan-400 border border-cyan-800/40'
                  : 'bg-slate-800 text-slate-400 border border-slate-700/40'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${activeEmbeddingProviderInfo?.connected ? 'bg-cyan-400 animate-pulse' : 'bg-slate-500'}`} />
                {selectedEmbeddingProvider === 'huggingface' ? 'Local BGE' : (selectedEmbeddingProvider === 'ollama' ? 'Local Ollama' : 'Cloud')}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 bg-surface-900 p-1 rounded-lg border border-slate-800">
              <motion.button
                type="button"
                onClick={() => handleEmbeddingProviderChange('ollama')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedEmbeddingProvider === 'ollama'
                    ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>Local Ollama</span>
                <span className="text-[10px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-emerald-400 font-mono">768d</span>
              </motion.button>
              <motion.button
                type="button"
                onClick={() => handleEmbeddingProviderChange('llamacpp')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedEmbeddingProvider === 'llamacpp'
                    ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>Local llama.cpp</span>
                <span className="text-[10px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-amber-400 font-mono">768d</span>
              </motion.button>
              <motion.button
                type="button"
                onClick={() => handleEmbeddingProviderChange('huggingface')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedEmbeddingProvider === 'huggingface'
                    ? 'bg-cyan-600/30 text-cyan-200 border border-cyan-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>Local BGE</span>
                <span className="text-[10px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-cyan-400 font-mono">384d</span>
              </motion.button>
              <motion.button
                type="button"
                onClick={() => handleEmbeddingProviderChange('google_genai')}
                disabled={loading}
                whileTap={{ scale: 0.95 }}
                className={`text-xs py-1 px-2 rounded-md font-medium flex items-center justify-between ${
                  selectedEmbeddingProvider === 'google_genai'
                    ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}>
                <span>Gemini Embed</span>
                <span className="text-[10px] text-slate-500">Cloud</span>
              </motion.button>
            </div>

            <div className="space-y-1 pt-1 border-t border-slate-800">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-medium">Embedding Model:</span>
                <span className="font-mono text-[10px] text-cyan-400">
                  {availableEmbeddingModels.find(m => m.id === selectedEmbeddingModel)?.dim ? `${availableEmbeddingModels.find(m => m.id === selectedEmbeddingModel)?.dim}d vectors` : ''}
                </span>
              </div>
              <div className="relative">
                <select
                  value={selectedEmbeddingModel}
                  onChange={e => {
                    setSelectedEmbeddingModel(e.target.value)
                    userTouchedEmbeddingRef.current = true
                  }}
                  disabled={loading}
                  className="w-full bg-surface-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500/50">
                {availableEmbeddingModels.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.name || m.id} {m.tag ? `[${m.tag}]` : ''}
                  </option>
                ))}
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <label className="section-heading !mb-0" htmlFor="query-input">Query</label>
              <span className={`text-[10px] font-mono ${
                query.length > 1800 ? 'text-amber-400' : 'text-slate-500'
              }`}>
                {query.length} / 2000
              </span>
            </div>

            <textarea
              id="query-input"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents… (Press ⌘+Enter to run)"
              rows={4}
              className="w-full min-h-[105px] bg-surface-800 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-600 transition-colors"
              disabled={loading}
            />

            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider block">
                Quick Prompts:
              </span>
              <div className="flex flex-col gap-1">
                {SAMPLE_PRESETS.map((preset, idx) => (
                  <motion.button
                    key={idx}
                    type="button"
                    onClick={() => handlePresetSelect(preset)}
                    disabled={loading}
                    whileTap={{ scale: 0.98 }}
                    className="text-left text-[11px] text-slate-400 hover:text-cyan-300 hover:bg-surface-800/80 px-2 py-1 rounded-md border border-slate-800/80 hover:border-cyan-500/30 truncate"
                  >
                    {preset}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>

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
                <label
                  htmlFor="web-search-toggle"
                  className="cursor-pointer select-none space-y-0.5"
                >
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <Globe className={`w-3.5 h-3.5 ${enableWebSearch ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span>Enable MCP Web Search Grounding</span>
                    <span className="rounded bg-cyan-950/80 px-1.5 py-0.5 text-[10px] font-medium text-cyan-300 border border-cyan-700/40">
                      MCP Tool
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    {enableWebSearch 
                      ? 'Active: Live internet grounding will be queried via MCP.'
                      : 'Unchecked: 100% Private Local RAG — searches only your Knowledge Base.'}
                  </p>
                </label>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono shrink-0 border ${
                enableWebSearch
                  ? 'bg-cyan-950 text-cyan-300 border-cyan-700/60 font-semibold shadow-sm'
                  : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}>
                {enableWebSearch ? 'MCP ENABLED' : 'OFFLINE ONLY'}
              </span>
            </div>

            {enableWebSearch && (
              <div className="pt-2 border-t border-slate-800/80 space-y-2 animate-fade-in">
                <span className="text-[11px] text-slate-300 block font-medium">Select MCP Search Engine:</span>
                <div className="grid grid-cols-3 gap-1 bg-surface-900 p-1 rounded-lg border border-slate-800">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => setWebSearchProvider('duckduckgo')}
                    className={`text-[11px] py-1 px-1.5 rounded font-medium transition-all ${
                      webSearchProvider === 'duckduckgo'
                        ? 'bg-amber-600/30 text-amber-300 border border-amber-500/40 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}>
                    DuckDuckGo (Free)
                  </button>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => setWebSearchProvider('tavily')}
                    className={`text-[11px] py-1 px-1.5 rounded font-medium transition-all ${
                      webSearchProvider === 'tavily'
                        ? 'bg-primary-600/30 text-primary-300 border border-primary-500/40 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}>
                    Tavily (AI)
                  </button>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => setWebSearchProvider('both')}
                    className={`text-[11px] py-1 px-1.5 rounded font-medium transition-all ${
                      webSearchProvider === 'both'
                        ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}>
                    Both (Parallel)
                  </button>
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">
                  {webSearchProvider === 'duckduckgo' && '🆓 100% Free search, zero API key or configuration required.'}
                  {webSearchProvider === 'tavily' && '⚡ High-accuracy AI RAG search with clean parsed content.'}
                  {webSearchProvider === 'both' && '🌐 Parallel search across Tavily + DuckDuckGo with URL deduplication.'}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="p-4 border-t border-slate-800/80 bg-surface-900/95 backdrop-blur-md shrink-0 space-y-1.5">
          <button
            type="submit"
            disabled={loading || !query.trim() || !kbId}
            id="run-analysis"
            className="btn-primary w-full flex items-center justify-center gap-2 shadow-lg shadow-primary-950/60 transition-all relative overflow-hidden"
          >
            {loading ? (
              <>
                <Loader2 size={14} className="animate-spin text-cyan-300" />
                <span>Executing Pipeline ({elapsedSec}s)…</span>
              </>
            ) : (
              <>
                <Zap size={14} className="text-cyan-300" />
                <span>Run Analysis</span>
                <span className="text-[10px] opacity-75 font-mono ml-1 flex items-center gap-0.5">
                  <CornerDownLeft size={10} /> ⌘Enter
                </span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}