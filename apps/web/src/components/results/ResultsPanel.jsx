import { useRef, useEffect, useReducer } from 'react'
import {
  Download, Cpu, Globe
} from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'
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

function TabIndicator({ activeTab, tabRefs }) {
  const [, forceTick] = useReducer(x => x + 1, 0)
  useEffect(() => {
    const onResize = () => forceTick()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  const el = tabRefs.current[activeTab]
  if (!el) return null
  return (
    <motion.div
      layoutId="active-tab"
      transition={SPRING_SNAPPY}
      className="absolute bottom-0 h-0.5 bg-gradient-to-r from-primary-500 to-cyan-400 shadow-glow-cyan"
      style={{ left: el.offsetLeft, width: el.offsetWidth }}
    />
  )
}

const TABS = [
  { id: 'answer',    label: 'Answer' },
  { id: 'evidence',  label: 'Evidence' },
  { id: 'claims',    label: 'Claims' },
  { id: 'trace',     label: 'Trace' },
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
      const data = await api.get(`/api/v1/analyses/${analysis.id}/export?format=jsonld`).then(r => r.data)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/ld+json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `trustrag-audit-${analysis.id}.jsonld`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to export dossier', err)
    }
  }

  if (!analysis && !loading) {
    return <EmptyState enableWebSearch={enableWebSearch} />
  }

  if (loading) {
    return (
      <div className="flex-1 min-h-0 flex flex-col p-4 sm:p-6 space-y-4 overflow-hidden">
        <PipelineTelemetryHUD
          events={currentTraceEvents}
          query={query}
          enableWebSearch={enableWebSearch}
          provider={selectedProvider}
          model={selectedModel}
          embeddingModel={selectedEmbeddingModel}
          analysisStatus={analysisStatus}
        />

        <div className="border-beam stream-beam flex-1 min-h-0 flex flex-col rounded-2xl border border-slate-800 bg-surface-900/50 backdrop-blur-sm p-4 overflow-hidden shadow-lg shadow-black/20">
          <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800/80 shrink-0">
            <div className="flex items-center gap-2">
              <span className="section-heading !mb-0 text-slate-200">Real-Time Event Stream</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-950/70 border border-cyan-800/40 text-cyan-300 tabular-nums">
                {compactTraceEvents(currentTraceEvents).length} events logged
              </span>
            </div>
            <span className="text-[10px] font-mono text-cyan-400 flex items-center gap-1.5 bg-surface-950 px-2.5 py-1 rounded-lg border border-slate-800 shadow-sm">
              <span className={`w-2 h-2 rounded-full ${analysisStatus && !['pending', 'processing'].includes(analysisStatus) ? 'bg-emerald-400' : 'bg-cyan-400 animate-ping'}`} />
              {analysisStatus && !['pending', 'processing'].includes(analysisStatus) ? 'STREAM FINISHED' : 'STREAM ACTIVE'}
            </span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto pr-1">
            <ExecutionTrace events={currentTraceEvents} isLive={!analysisStatus || ['pending', 'processing'].includes(analysisStatus)} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col overflow-visible md:overflow-hidden">
      <div className="shrink-0 p-4 border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-3 bg-surface-900/70 backdrop-blur-md">
        <div className="flex items-center gap-3 min-w-0">
          <ReliabilityBadge status={analysis.status} />
          <div className="min-w-0">
            <p className="text-sm text-slate-100 truncate font-semibold">{analysis.query}</p>
            <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
              <span>ID: <code className="text-slate-300 font-mono">{analysis.id?.slice(-8)}</code></span>
              <span>•</span>
              <span>Evidence: <strong className="text-slate-200">{analysis.evidence?.length || 0} chunks</strong></span>
              <span>•</span>
              <span>Claims: <strong className="text-slate-200">{analysis.claims?.length || 0} assertions</strong></span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          {analysis.llm_provider && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary-950/80 text-primary-300 border border-primary-700/50 text-[10px] font-mono max-w-[260px]"
              title={analysis.llm_model ? `${providerShortLabel(analysis.llm_provider)}: ${analysis.llm_model}` : providerShortLabel(analysis.llm_provider)}
            >
              <Cpu size={11} className="text-primary-400 shrink-0" />
              <span className="truncate tracking-tight">{providerShortLabel(analysis.llm_provider)}: {shortModelId(analysis.llm_model) || 'DEFAULT'}</span>
            </span>
          )}
          {analysis.web_search_enabled && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-cyan-950/80 text-cyan-300 border border-cyan-700/50 text-[10px] font-mono">
              <Globe size={11} className="text-cyan-400" />
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
            title="Export Verification Audit Report (JSON-LD)"
            aria-label="Export verification audit report"
            className="px-3 py-1.5 text-xs border border-slate-700 hover:border-cyan-500/50 rounded-xl text-slate-300 hover:text-white flex items-center gap-1.5 transition-all bg-surface-800/90 hover:bg-surface-700/80 shadow-sm"
          >
            <Download size={13} className="text-cyan-400" />
            <span className="font-medium">Export</span>
          </button>
        </div>
      </div>

      <div className="shrink-0 relative border-b border-slate-800/80 px-4 bg-surface-900/30">
        <TabIndicator activeTab={activeTab} tabRefs={tabRefs} />
        {TABS.map(tab => (
          <motion.button
            key={tab.id}
            ref={(el) => { tabRefs.current[tab.id] = el }}
            onClick={() => setActiveTab(tab.id)}
            whileTap={{ scale: 0.98, transition: SPRING_SNAPPY }}
            className={`relative px-4 py-2.5 text-xs font-semibold uppercase tracking-wider ${
              activeTab === tab.id
                ? 'text-cyan-300'
                : 'text-slate-500 hover:text-slate-300'
            }`}>
            <span>{tab.label}</span>
          </motion.button>
        ))}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
        <AnimatePresence mode="wait">
          {activeTab === 'answer' && (
            <AnswerTab
              analysis={analysis}
              selectedProvider={selectedProvider}
              recoveryRuns={recoveryRuns}
              onExportDossier={handleExportDossier}
            />
          )}

          {activeTab === 'evidence' && (
            <EvidenceTab analysis={analysis} />
          )}

          {activeTab === 'claims' && (
            <ClaimsTab analysis={analysis} />
          )}

          {activeTab === 'trace' && (
            <TraceTab currentTraceEvents={currentTraceEvents} />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}