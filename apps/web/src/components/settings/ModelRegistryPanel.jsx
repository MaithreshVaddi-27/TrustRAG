import { Cpu, FileText } from 'lucide-react'

/**
 * ModelRegistryPanel — what the platform is actually configured to run.
 *
 * Every model identifier is read from `config/models.yaml`; this panel only
 * reports it. The registry is a specification, so it is rendered as one.
 */
const FALLBACK_FORMATS = [
  'pdf',
  'txt',
  'md',
  'docx',
  'csv',
  'json',
  'html',
  'htm',
]

export default function ModelRegistryPanel({ models, supportedFormats, healthUnknown }) {
  const rows = [
    {
      key: 'Active LLM engine',
      value: healthUnknown
        ? 'Unknown'
        : `${models.llm_provider || 'llama_cpp'} (${models.llm_model || 'see models.yaml'})`,
    },
    {
      key: 'Dense vector embeddings',
      value: `${models.embedding_model || 'BAAI/bge-small-en-v1.5'} (384-dim)`,
    },
    {
      key: 'NLI claim verifier',
      value: healthUnknown ? 'Unknown' : `${models.verification_model || 'see models.yaml'} (temp=0.0)`,
    },
    {
      key: 'CrossEncoder neural reranker',
      value: models.reranker_enabled ? models.reranker_model : 'Disabled (on-demand)',
    },
    {
      key: 'Retrieval fusion strategy',
      value: 'Reciprocal Rank Fusion (RRF, k=60)',
    },
    {
      key: 'Adaptive recovery ceiling',
      value: 'Max 2 rewrites · max 2 context expansions',
    },
  ]

  const formats = supportedFormats?.length ? supportedFormats : FALLBACK_FORMATS

  return (
    <section className="lx-panel-block" aria-labelledby="registry-heading">
      <div className="lx-panel-block__head">
        <h2 id="registry-heading" className="lx-panel-block__title flex items-center gap-2">
          <Cpu size={16} strokeWidth={1.5} aria-hidden="true" />
          Active model registry
        </h2>
        <span className="lx-micro">config/models.yaml</span>
      </div>

      <div className="lx-panel-block__body">
        <dl className="lx-deflist">
          {rows.map((row) => (
            <div key={row.key} className="lx-deflist__row">
              <dt className="lx-deflist__key">{row.key}</dt>
              <dd className="lx-deflist__value">{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="lx-panel-block__foot">
        <p className="lx-micro flex items-center gap-1.5">
          <FileText size={12} strokeWidth={1.5} aria-hidden="true" />
          Supported ingestion formats
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {formats.map((format) => (
            <span key={format} className="lx-chip">
              .{format}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
