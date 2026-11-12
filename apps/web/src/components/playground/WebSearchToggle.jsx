import { Globe, Sparkles } from 'lucide-react'

/**
 * WebSearchToggle — let the agent reach the public internet.
 *
 * A switch, not a card. When it is on, the panel below explains what
 * changes: which provider grounds the search, which MCP tools become
 * available, and that the agent may invoke web retrieval on its own when
 * the knowledge base cannot ground the answer.
 */
export function WebSearchToggle({ enableWebSearch, setEnableWebSearch, loading, selectedProvider }) {
  const isLocalProvider = ['ollama', 'llama_cpp', 'mlx'].includes(selectedProvider)

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2.5">
          <Globe
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            className="mt-0.5 shrink-0 text-silver-500"
          />
          <div className="min-w-0">
            <span
              id="web-search-grounding-label"
              className="block text-[var(--size-label)] font-medium text-silver-200"
            >
              Web search grounding
            </span>
            <span className="lx-micro mt-0.5 block">
              {enableWebSearch
                ? 'Live internet evidence via Model Context Protocol'
                : 'Local-only retrieval, knowledge base isolated'}
            </span>
          </div>
        </div>

        <button
          type="button"
          role="switch"
          id="web-search-toggle"
          aria-checked={enableWebSearch}
          aria-labelledby="web-search-grounding-label"
          disabled={loading}
          onClick={() => setEnableWebSearch(!enableWebSearch)}
          className="lx-switch shrink-0"
        >
          <span className="lx-switch__knob" aria-hidden="true" />
        </button>
      </div>

      {enableWebSearch && (
        <div className="space-y-2 border-t border-[color:var(--rule-faint)] pt-3">
          <dl className="lx-deflist">
            <div className="lx-deflist__row">
              <dt className="lx-deflist__key">Web provider</dt>
              <dd className="lx-deflist__value">Tavily AI search</dd>
            </div>
            <div className="lx-deflist__row">
              <dt className="lx-deflist__key">Active MCP tools</dt>
              <dd className="lx-deflist__value">tavily_search · trustrag_verify_claim</dd>
            </div>
          </dl>

          {isLocalProvider && (
            <p className="lx-micro flex items-start gap-2">
              <Sparkles
                size={12}
                strokeWidth={1.75}
                className="mt-0.5 shrink-0 text-silver-500"
                aria-hidden="true"
              />
              <span>
                Autonomous tool calling: with web search enabled, the agent may
                reach for the public web to ground an answer the knowledge base
                cannot support on its own.
              </span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
