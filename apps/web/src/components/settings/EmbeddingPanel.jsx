import { Layers, Sparkles } from 'lucide-react'

/**
 * EmbeddingPanel — the vector engine and the MCP surface.
 *
 * Two things that belong on one screen because they are the two ways
 * TrustRAG is reached from outside the browser: embedded vectors, and
 * the tool protocol.
 *
 * The vector engine's readings come from the registry. It used to print
 * "384d · offline" and "ONNX Runtime / CPU" in fixed strings — a
 * description of one particular deployment, presented as a reading.
 */
const TOOLS = [
  { name: 'trustrag_search', role: 'Hybrid RRF search' },
  { name: 'trustrag_verify_claim', role: 'NLI verification' },
  { name: 'tavily_search', role: 'AI web grounding' },
  { name: 'local_llm_chat', role: 'Ollama / llama.cpp MCP' },
]

export default function EmbeddingPanel({ activeModel, embedding }) {
  const known = Boolean(embedding)
  const provider = embedding?.provider
  const dimension = embedding?.dim
  const type = embedding?.type

  return (
    <section className="lx-panel-block" aria-labelledby="embedding-heading">
      <div className="lx-panel-block__head">
        <h2 id="embedding-heading" className="lx-panel-block__title flex items-center gap-2">
          <Layers size={16} strokeWidth={1.5} aria-hidden="true" />
          Dense vector embedding infrastructure
        </h2>
        <span className="lx-chip">{activeModel || 'Detecting…'}</span>
      </div>

      <div className="lx-panel-block__body">
        <dl className="lx-deflist">
          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Provider</dt>
            <dd className="lx-deflist__value">
              {known ? provider.toUpperCase() : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Vector dimension</dt>
            <dd className="lx-deflist__value">
              {known && dimension ? `${dimension}d` : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Execution</dt>
            <dd className="lx-deflist__value">
              {known
                ? `${type === 'cloud' ? 'cloud' : 'local'} · ${
                    embedding.connected ? 'reachable' : 'unreachable'
                  }`
                : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Cost</dt>
            <dd className="lx-deflist__value">
              {known
                ? type === 'cloud'
                  ? 'Metered by the provider'
                  : 'Local — no API cost'
                : 'Detecting…'}
            </dd>
          </div>
        </dl>
      </div>

      <div className="border-t border-[color:var(--rule-faint)] px-5 py-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 text-[var(--size-body)] text-silver-100">
            <Sparkles size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
            Model Context Protocol interface
          </h3>
          <span className="lx-chip">stdio and in-process active</span>
        </div>

        <p className="lx-body-sm mt-2 max-w-[72ch]">
          A standardized MCP server exposes TrustRAG and the local LLM tools to
          Cursor, Claude Desktop, Antigravity IDE and external agents.
        </p>

        <dl className="lx-deflist mt-4">
          {TOOLS.map((tool) => (
            <div key={tool.name} className="lx-deflist__row">
              <dt className="lx-deflist__key font-mono text-silver-200">{tool.name}</dt>
              <dd className="lx-deflist__value">{tool.role}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
