import { Send, Sparkles, ScrollText, Info } from 'lucide-react'

/**
 * QueryInput — the question.
 *
 * A labelled textarea with a character budget and four quick prompts. The
 * quick prompts are shortcuts, not decoration, so the tooltip carries the
 * full prompt.
 *
 * The visible label is always the opening of the prompt it sends.
 * WCAG 2.5.3 requires an accessible name to contain the visible text, and
 * the name here is the full prompt — so "Explain key concepts" and
 * "Explain the key concepts in this document" would disagree, because the
 * visible words are not a contiguous run of the name's words.
 */
const SAMPLE_PRESETS = [
  {
    text: 'Explain the key concepts',
    full: 'Explain the key concepts in this document',
    icon: Sparkles,
  },
  {
    text: 'Summarize the main findings',
    full: 'Summarize the main findings and takeaways',
    icon: ScrollText,
  },
  {
    text: 'Describe the knowledge base',
    full: 'Describe the knowledge base and its contents',
    icon: Info,
  },
  {
    text: 'What are the important details',
    full: 'What are the important details I should know?',
    icon: Send,
  },
]

const LIMIT = 2000

export function QueryInput({ query, setQuery, loading, handleSubmit, handlePresetSelect }) {
  const handleKeyDown = (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  const overBudget = query.length > LIMIT * 0.9

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <label className="lx-workbench__label !mb-0" htmlFor="query-input">
          Query
        </label>
        <span
          className="lx-micro tabular-nums"
          style={overBudget ? { color: 'var(--color-crimson-300)' } : undefined}
        >
          {query.length} / {LIMIT}
        </span>
      </div>

      <textarea
        id="query-input"
        name="query"
        aria-label="Query or prompt input"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about your documents…"
        rows={4}
        maxLength={LIMIT}
        className="lx-control"
        disabled={loading}
      />

      <div className="space-y-2">
        <span className="lx-workbench__label">Quick prompts</span>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_PRESETS.map((preset) => {
            const Icon = preset.icon
            return (
              <button
                key={preset.text}
                type="button"
                onClick={() => handlePresetSelect(preset.full)}
                disabled={loading}
                title={preset.full}
                aria-label={preset.full}
                className="lx-chip transition-colors hover:border-[color:var(--rule-strong)] hover:text-silver-200"
              >
                <Icon size={11} strokeWidth={1.75} aria-hidden="true" />
                {preset.text}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
