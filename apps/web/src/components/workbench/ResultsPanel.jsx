import { useState, useRef } from 'react'
import { 
  Download, Copy, Sparkles, Check, Cpu, Globe, Clock
} from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'
import { ReliabilityBadge } from './ReliabilityBadge'
import { ClaimInspector } from './ClaimInspector'
import { EvidenceViewer } from './EvidenceViewer'
import { ExecutionTrace, RecoveryTimeline } from './ExecutionTrace'
import { FormattedAnswer } from './FormattedAnswer'
import { EmptyState } from './EmptyState'
import { PipelineTelemetryHUD } from './PipelineTelemetryHUD'
import { copyToClipboard } from '@/lib/clipboard'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'
import { compactTraceEvents } from './traceEvents'
import api from '@/lib/api'

function TabIndicator({ activeTab, tabRefs }) {
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
  webSearchProvider,
  selectedProvider,
  selectedModel,
  selectedEmbeddingModel,
}) {
  const [copied, setCopied] = useState(false)
  const tabRefs = useRef({})

  const answerWordCount = analysis?.answer ? analysis.answer.trim().split(/\s+/).filter(Boolean).length : 0
  const estimatedReadTime = Math.max(1, Math.ceil(answerWordCount / 180))

  const handleCopyAnswer = async () => {
    if (!analysis?.answer) return
    const ok = await copyToClipboard(analysis.answer)
    if (!ok) return
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

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
    return <EmptyState onLoadSample={() => {}} />
  }

  if (loading) {
    return (
      <div className="flex-1 min-h-0 flex flex-col p-4 sm:p-6 space-y-4 overflow-hidden">
        <PipelineTelemetryHUD
          events={currentTraceEvents}
          query={query}
          enableWebSearch={enableWebSearch}
          webSearchProvider={webSearchProvider}
          provider={selectedProvider}
          model={selectedModel}
          embeddingModel={selectedEmbeddingModel}
        />

        <div className="flex-1 min-h-0 flex flex-col rounded-2xl border border-slate-800 bg-surface-900/50 backdrop-blur-sm p-4 overflow-hidden shadow-lg shadow-black/20">
          <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800/80 shrink-0">
            <div className="flex items-center gap-2">
              <span className="section-heading !mb-0 text-slate-200">Real-Time Event Stream</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-950/70 border border-cyan-800/40 text-cyan-300 tabular-nums">
                {compactTraceEvents(currentTraceEvents).length} events logged
              </span>
            </div>
            <span className="text-[10px] font-mono text-cyan-400 flex items-center gap-1.5 bg-surface-950 px-2.5 py-1 rounded-lg border border-slate-800 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              STREAM ACTIVE
            </span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto pr-1">
            <ExecutionTrace events={currentTraceEvents} isLive={true} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
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
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-950/80 text-purple-300 border border-purple-700/50 text-[10px] font-mono max-w-[260px]"
              title={analysis.llm_model ? `${providerShortLabel(analysis.llm_provider)}: ${analysis.llm_model}` : providerShortLabel(analysis.llm_provider)}
            >
              <Cpu size={11} className="text-purple-400 shrink-0" />
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
            <motion.div
              key="answer"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={SPRING_SNAPPY}
              className="space-y-5"
            >
            {(analysis.status === 'failed' || analysis.reliability?.status === 'FAILED') && (
              <div className="rounded-xl border border-red-800/50 bg-red-950/30 p-4 shadow-glow-crimson animate-fade-in">
                <p className="text-sm font-medium text-red-300">
                  {analysis.status === 'failed'
                    ? `Analysis failed: ${analysis.diagnosis?.failures?.[0] || 'Unknown error occurred'}`
                    : `Reliability check failed: ${analysis.diagnosis?.failures?.[0] || 'Thresholds not met'}`}
                </p>
              </div>
            )}

            {(analysis.status === 'abstained' || analysis.reliability?.status === 'ABSTAINED') && (
              <div className="rounded-xl border border-amber-800/50 bg-amber-950/30 p-4 shadow-glow-amber animate-fade-in">
                <p className="text-sm font-medium text-amber-300">
                  ⊘ The agent abstained from answering because the retrieved document segments did not contain sufficient factual evidence to answer this question reliably without hallucinating.
                </p>
                <p className="text-xs text-amber-400/90 mt-1.5">
                  Tip: Try phrasing your question using specific section names or verify that your uploaded documents cover this topic.
                </p>
              </div>
            )}
            
            {analysis.answer && analysis.answer !== 'ABSTAIN' && (
              <div className="glass-card p-5 sm:p-6 relative overflow-hidden border-slate-700/60 hover:border-cyan-500/40 transition-all shadow-lg">
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800/80 flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
                      <Sparkles size={14} />
                    </span>
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                      Grounded Synthesis
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1 ml-2">
                      <Clock size={11} /> ~{estimatedReadTime} min read ({answerWordCount} words)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyAnswer}
                    className="text-xs text-slate-400 hover:text-cyan-300 flex items-center gap-1.5 transition-all px-3 py-1.5 rounded-lg bg-surface-800/90 border border-slate-700/60 hover:border-cyan-500/50 shadow-sm"
                    title="Copy answer to clipboard"
                  >
                    {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    <span className={copied ? 'text-emerald-400 font-medium' : ''}>
                      {copied ? 'Copied!' : 'Copy Answer'}
                    </span>
                  </button>
                </div>
                <FormattedAnswer content={analysis.answer} />
              </div>
            )}

            {analysis.claims?.some(c => c.state === 'NEUTRAL' || c.state === 'CONTRADICTED') && (
              <div className="rounded-xl border border-amber-800/40 bg-amber-950/20 px-4 py-3">
                <p className="text-xs text-amber-300">
                  ⚠ Some claims could not be verified against the citation corpus. Inspect the Claims tab for proposition-level breakdown.
                </p>
              </div>
            )}

            <RecoveryTimeline recoveryRuns={recoveryRuns} />
            </motion.div>
          )}

          {activeTab === 'evidence' && (
            <motion.div
              key="evidence"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={SPRING_SNAPPY}
            >
              <EvidenceViewer chunks={analysis.evidence || []} />
            </motion.div>
          )}

          {activeTab === 'claims' && (
            <motion.div
              key="claims"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={SPRING_SNAPPY}
            >
              <ClaimInspector claims={analysis.claims || []} />
            </motion.div>
          )}

          {activeTab === 'trace' && (
            <motion.div
              key="trace"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={SPRING_SNAPPY}
            >
              <ExecutionTrace events={currentTraceEvents} isLive={false} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}