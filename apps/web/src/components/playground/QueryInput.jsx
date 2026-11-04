const SAMPLE_PRESETS = [
  { text: "Explain key concepts", full: "Explain the key concepts in this document", icon: "📖" },
  { text: "Summarize takeaways", full: "Summarize the main findings and takeaways", icon: "📝" },
  { text: "Describe contents", full: "Describe the knowledge base and its contents", icon: "🔍" },
  { text: "Important details", full: "What are the important details I should know?", icon: "💡" },
]

export function QueryInput({ query, setQuery, loading, handleSubmit, handlePresetSelect }) {
  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <label className="section-heading !mb-0 font-medium" htmlFor="query-input">Query / Prompt</label>
        <span className={`text-[10px] font-mono ${
          query.length > 1800 ? 'text-amber-400' : 'text-slate-500'
        }`}>
          {query.length} / 2000
        </span>
      </div>

      <textarea
        id="query-input"
        name="query"
        aria-label="Query or prompt input"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about your documents… (Press ⌘+Enter to run)"
        rows={3}
        maxLength={2000}
        className="w-full min-h-[84px] bg-surface-800/90 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/80 focus:shadow-[0_0_16px_rgba(6,182,212,0.12)] transition-all duration-200"
        disabled={loading}
      />

      <div className="space-y-1">
        <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider block">
          Quick Prompts
        </span>
        <div className="flex flex-wrap gap-1.5">
          {SAMPLE_PRESETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handlePresetSelect(preset.full)}
              disabled={loading}
              title={preset.full}
              className="group text-left text-[11px] text-slate-400 hover:text-cyan-300 hover:bg-surface-800/90 px-2.5 py-1 rounded-lg border border-slate-800/80 hover:border-cyan-500/30 transition-all duration-150 ease-out inline-flex items-center gap-1.5 cursor-pointer"
            >
              <span className="text-[10px] opacity-70 group-hover:opacity-100 transition-opacity">{preset.icon}</span>
              <span className="truncate max-w-[130px]">{preset.text}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}