import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import { Send, Sparkles, Loader2 } from 'lucide-react'

const SAMPLE_PRESETS = [
  { text: 'Explain key concepts', full: 'Explain the key concepts in this document', icon: Sparkles },
  { text: 'Summarize takeaways', full: 'Summarize the main findings and takeaways', icon: Send },
  { text: 'Describe contents', full: 'Describe the knowledge base and its contents', icon: Loader2 },
  { text: 'Important details', full: 'What are the important details I should know?', icon: Sparkles },
]

export function QueryInput({ query, setQuery, loading, handleSubmit, handlePresetSelect }) {
  const reduced = useReducedMotion()

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const springTransition = reduced
    ? { duration: 0.01 }
    : { type: 'spring', damping: 28, stiffness: 220 }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs">
        <label
          className="section-heading !mb-0 font-medium"
          htmlFor="query-input"
        >
          Query
        </label>
        <span
          className={`text-[10px] font-mono tabular-nums ${
            query.length > 1800 ? 'text-amber-400' : 'text-slate-500'
          }`}
        >
          {query.length} / 2000
        </span>
      </div>

      <div className="relative">
        <textarea
          id="query-input"
          name="query"
          aria-label="Query or prompt input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents… (Press ⌘+Enter to run)"
          rows={3}
          maxLength={2000}
          className="w-full min-h-[84px] bg-surface-800/90 border border-slate-700/80 rounded-xl px-3 py-2.5 text-xs text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/80 focus:shadow-[0_0_16px_rgba(6,182,212,0.12)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={loading}
          style={{ minHeight: '84px' }}
        />
        {loading && (
          <motion.div
            className="absolute bottom-2 right-2 flex items-center gap-1.5"
            initial={reduced ? { opacity: 1 } : { opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={springTransition}
          >
            <span className="thinking-orbs--sm" aria-hidden="true">
              <span className="orb" />
              <span className="orb" />
              <span className="orb" />
            </span>
            <span className="text-[10px] font-mono text-cyan-400">Thinking…</span>
          </motion.div>
        )}
      </div>

      <div className="space-y-2">
        <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider block">
          Quick Prompts
        </span>
        <div className="flex flex-wrap gap-1.5" role="list" aria-label="Quick prompt suggestions">
          {SAMPLE_PRESETS.map((preset, idx) => (
            <motion.button
              key={idx}
              type="button"
              onClick={() => handlePresetSelect(preset.full)}
              disabled={loading}
              title={preset.full}
              whileHover={{ y: -1, transition: springTransition }}
              whileTap={{ scale: 0.97, transition: { duration: 0.08, ease: 'easeOut' } }}
              className="group text-left text-[11px] text-slate-400 hover:text-cyan-300 hover:bg-surface-800/90 px-2.5 py-1.5 rounded-lg border border-slate-800/80 hover:border-cyan-500/30 transition-all duration-150 ease-out inline-flex items-center gap-2 cursor-pointer"
              style={{ minWidth: '44px', minHeight: '44px' }}
              role="listitem"
            >
              <motion.span
                className="text-[12px] opacity-70 group-hover:opacity-100 transition-opacity shrink-0"
                animate={!reduced && { scale: [1, 1.1, 1] }}
                transition={{ duration: 2, ease: 'easeInOut', repeat: Infinity, delay: idx * 0.2 }}
              >
                <preset.icon size={12} aria-hidden="true" />
              </motion.span>
              <span className="truncate max-w-[140px]">{preset.text}</span>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  )
}