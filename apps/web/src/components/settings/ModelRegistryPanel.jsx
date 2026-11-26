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
  // Every row is read from the registry. The panel's own claim is that it
  // reports config/models.yaml and nothing else, so a row that cannot be
  // sourced from it does not belong here — it used to print a fusion
  // constant and a recovery ceiling that the registry never reported.
  const rows = [
    {
      key: 'Active LLM engine',
      value: healthUnknown
        ? 'Unknown'
        : `${models.llm_provider ?? 'Unknown'} (${models.llm_model ?? 'Unknown'})`,
    },
    {
      key: 'Dense vector embeddings',
      value: healthUnknown
        ? 'Unknown'
        : `${models.embedding_model ?? 'Unknown'} (${
            models.embedding_dimensionality ?? '?'
          }-dim)`,
    },
    {
      key: 'NLI claim verifier',
      value: healthUnknown
        ? 'Unknown'
        : `${models.verification_provider ?? 'Unknown'} (${
            models.verification_model ?? 'Unknown'
          })`,
    },
    {
      key: 'CrossEncoder neural reranker',
      value: healthUnknown
        ? 'Unknown'
        : models.reranker_enabled
          ? (models.reranker_model ?? 'Enabled')
          : 'Disabled (on-demand)',
    },
    {
      key: 'Web search provider',
      value: healthUnknown
        ? 'Unknown'
        : `${models.search_provider ?? 'Unknown'} · ${
            models.tavily_configured
              ? 'Tavily configured'
              : 'Tavily not configured'
          }`,
    },
    {
      key: 'Registry version',
      value: healthUnknown
        ? 'Unknown'
        : `models.yaml ${models.config_version ?? '?'}`,
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
