import { useRef } from 'react'
import { Download, Cpu, Globe } from 'lucide-react'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'
import { PipelineTelemetryHUD } from '@/components/workbench/PipelineTelemetryHUD'
import { ExecutionTrace } from '@/components/workbench/ExecutionTrace'
import { EmptyState } from '@/components/workbench/EmptyState'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'
import { compactTraceEvents } from '@/components/workbench/traceEvents'
import api from '@/lib/api'
import { AnswerTab } from './AnswerTab'
import { EvidenceTab } from './EvidenceTab'
import { ClaimsTab } from './ClaimsTab'
import { TraceTab } from './TraceTab'

/**
 * ResultsPanel — the fluid pane of the workbench.
 *
 * A header that states what was run, a segmented control for the four
 * readings of that run, and one pane of content. The tabs are `aria-selected`
 * so the active one is unambiguous to a screen reader, and the crimson
 * underline is the only colour on the screen.
 */
const TABS = [
  { id: 'answer', label: 'Answer' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'claims', label: 'Claims' },
  { id: 'trace', label: 'Trace' },
]

export function ResultsPanel({
  analysis,
  loading,
  activeTab,
  setActiveTab,
  currentTraceEvents,
  recoveryRuns,
  query,
  enableWebSearch,
  selectedProvider,
  selectedModel,
  selectedEmbeddingModel,
  analysisStatus,
}) {
  const tabRefs = useRef({})

  const handleExportDossier = async () => {
    if (!analysis?.id) return
    try {
      const data = await api
        .get(`/api/v1/analyses/${analysis.id}/export?format=jsonld`)
        .then((r) => r.data)
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/ld+json',
      })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `trustrag-audit-${analysis.id}.jsonld`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to export dossier', err)
    }
  }

  if (!analysis && !loading) {
    return (
      <div className="lx-workbench__pane lx-workbench__pane--flush">
        <EmptyState enableWebSearch={enableWebSearch} />
      </div>
    )
  }

  if (loading) {
    const streamActive =
      !analysisStatus || ['pending', 'processing'].includes(analysisStatus)

    return (
      <div className="lx-workbench__pane lx-workbench__pane--flush flex flex-col">
        <div className="shrink-0">
          <PipelineTelemetryHUD
            events={currentTraceEvents}
            query={query}
            enableWebSearch={enableWebSearch}
            provider={selectedProvider}
            model={selectedModel}
            embeddingModel={selectedEmbeddingModel}
            analysisStatus={analysisStatus}
          />
        </div>

        <div className="lx-panel-block flex min-h-0 flex-1 flex-col rounded-none border-x-0 border-b-0">
          <div className="lx-panel-block__head">
            <h2 className="lx-panel-block__title">Real-time event stream</h2>
            <span className="lx-chip">
              {compactTraceEvents(currentTraceEvents).length} events
            </span>
            <span className="lx-chip">
              <span
                className={`lx-dot${streamActive ? ' lx-dot--live' : ''}`}
                aria-hidden="true"
              />
              {streamActive ? 'Stream active' : 'Stream finished'}
            </span>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <ExecutionTrace events={currentTraceEvents} isLive={streamActive} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="lx-workbench__pane lx-workbench__pane--flush flex flex-col">
      <div className="shrink-0 border-b border-[color:var(--rule)] px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <ReliabilityBadge status={analysis.status} />
              <h2 className="truncate text-[var(--size-h3)] text-silver-050">
                {analysis.query}
              </h2>
            </div>

            <div className="lx-list__meta mt-2">
              <span>
                ID <span className="text-silver-300">{analysis.id?.slice(-8)}</span>
              </span>
              <span>
                Evidence{' '}
                <span className="text-silver-300">{analysis.evidence?.length || 0} chunks</span>
              </span>
              <span>
                Claims{' '}
                <span className="text-silver-300">{analysis.claims?.length || 0} assertions</span>
              </span>
            </div>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {analysis.llm_provider && (
              <span
                className="lx-chip"
                title={
                  analysis.llm_model
                    ? `${providerShortLabel(analysis.llm_provider)}: ${analysis.llm_model}`
                    : providerShortLabel(analysis.llm_provider)
                }
              >
                <Cpu size={11} strokeWidth={1.75} aria-hidden="true" />
                {providerShortLabel(analysis.llm_provider)}:{' '}
                {shortModelId(analysis.llm_model) || 'DEFAULT'}
              </span>
            )}

            {analysis.web_search_enabled && (
              <span className="lx-chip">
                <Globe size={11} strokeWidth={1.75} aria-hidden="true" />
                MCP {analysis.web_search_provider?.toUpperCase() || 'WEB'}
              </span>
            )}

            {analysis.reliability && (
              <ReliabilityBadge
                score={analysis.reliability.score}
                status={analysis.reliability.status}
                size="md"
              />
            )}

            <button
              type="button"
              onClick={handleExportDossier}
              className="lx-btn lx-btn--secondary"
              title="Export the verification audit report as JSON-LD"
              aria-label="Export the verification audit report"
            >
              <Download size={13} strokeWidth={1.75} aria-hidden="true" />
              <span>Export</span>
            </button>
          </div>
        </div>
      </div>

      <div className="shrink-0 border-b border-[color:var(--rule-faint)] px-5 py-3">
        <div className="lx-tabs" role="tablist" aria-label="Analysis readings">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              ref={(el) => {
                tabRefs.current[tab.id] = el
              }}
              type="button"
              role="tab"
              id={`results-tab-${tab.id}`}
              aria-selected={activeTab === tab.id}
              aria-controls={`results-panel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className="lx-tab"
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div
        role="tabpanel"
        id={`results-panel-${activeTab}`}
        aria-labelledby={`results-tab-${activeTab}`}
        className="min-h-0 flex-1 overflow-y-auto px-5 py-6"
      >
        {activeTab === 'answer' && (
          <AnswerTab
            analysis={analysis}
            selectedProvider={selectedProvider}
            recoveryRuns={recoveryRuns}
            onExportDossier={handleExportDossier}
          />
        )}

        {activeTab === 'evidence' && <EvidenceTab analysis={analysis} />}

        {activeTab === 'claims' && <ClaimsTab analysis={analysis} />}

        {activeTab === 'trace' && <TraceTab currentTraceEvents={currentTraceEvents} />}
      </div>
    </div>
  )
}
