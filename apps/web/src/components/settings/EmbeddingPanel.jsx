import { Layers, Sparkles } from 'lucide-react'

/**
 * EmbeddingPanel — the vector engine and the MCP surface.
 *
 * Two things that belong on one screen because they are the two ways
 * TrustRAG is reached from outside the browser: embedded vectors, and the
 * tool protocol.
 */
const TOOLS = [
  { name: 'trustrag_search', role: 'Hybrid RRF search' },
  { name: 'trustrag_verify_claim', role: 'NLI verification' },
  { name: 'tavily_search', role: 'AI web grounding' },
  { name: 'local_llm_chat', role: 'Ollama / llama.cpp MCP' },
]

export default function EmbeddingPanel({ activeModel }) {
  return (
    <section className="lx-panel-block" aria-labelledby="embedding-heading">
      <div className="lx-panel-block__head">
        <h2 id="embedding-heading" className="lx-panel-block__title flex items-center gap-2">
          <Layers size={16} strokeWidth={1.5} aria-hidden="true" />
          Dense vector embedding infrastructure
        </h2>
        <span className="lx-chip">{activeModel || 'BAAI/bge-small-en-v1.5'}</span>
      </div>

      <div className="lx-panel-block__body">
        <dl className="lx-deflist">
          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Local BGE (ONNX)</dt>
            <dd className="lx-deflist__value">384d · offline</dd>
          </div>
          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Runtime</dt>
            <dd className="lx-deflist__value">ONNX Runtime / CPU</dd>
          </div>
          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Cost</dt>
            <dd className="lx-deflist__value">Zero API cost · torch-free</dd>
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
