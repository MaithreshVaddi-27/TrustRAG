import { useState, useRef, useEffect } from 'react'
import { Database, Loader2, Zap, Download, Globe, Copy, Sparkles, Check } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { ReliabilityBadge, StatusDot } from '@/components/workbench/ReliabilityBadge'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { ExecutionTrace, RecoveryTimeline } from '@/components/workbench/ExecutionTrace'
import { TraceEventType } from '@/components/workbench/traceEvents'
import { kbService, analysisService } from '@/services/api'
import { FormattedAnswer } from '@/components/workbench/FormattedAnswer'
import { PipelineTelemetryHUD } from '@/components/workbench/PipelineTelemetryHUD'
import api, { openAnalysisStream } from '@/lib/api'

export default function PlaygroundPage() {
  const [query, setQuery] = useState('')
  const [kbId, setKbId] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [traceEvents, setTraceEvents] = useState([])
  const [activeTab, setActiveTab] = useState('answer')
  const [errorMsg, setErrorMsg] = useState('')
  const [enableWebSearch, setEnableWebSearch] = useState(false)
  const [webSearchProvider, setWebSearchProvider] = useState('both') // 'tavily' | 'duckduckgo' | 'both'
  const [copied, setCopied] = useState(false)
  
  const streamRef = useRef(null)
  const pollTimerRef = useRef(null)

  const handleCopyAnswer = () => {
    if (!analysis?.answer) return
    navigator.clipboard.writeText(analysis.answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Fetch KBs for the dropdown
  const { data: knowledgeBases } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list
  })

  // Cleanup stream and fallback polling on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.close()
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

  function startFallbackPolling(analysisId) {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)

    pollTimerRef.current = setInterval(async () => {
      try {
        const snap = await analysisService.get(analysisId)
        if (snap && (snap.status === 'completed' || snap.status === 'abstained' || snap.status === 'failed')) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
          await fetchFinalAnalysis(analysisId)
        }
      } catch {
        // Ignore background polling errors
      }
    }, 2000)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!query.trim() || !kbId) return
    
    setLoading(true)
    setAnalysis(null)
    setTraceEvents([])
    setErrorMsg('')
    setActiveTab('answer')

    try {
      // 1. Create analysis run
      const analysisCreated = await analysisService.create({ 
        knowledge_base_id: kbId, 
        query,
        enable_web_search: enableWebSearch,
        web_search_provider: webSearchProvider,
      })

      // 2. Connect to SSE stream
      streamRef.current = openAnalysisStream(analysisCreated.id, {
        onEvent: (eventData) => {
          setTraceEvents(prev => [...prev, eventData])
        },
        onError: async () => {
          // If SSE fails, wait a bit then fetch final state anyway
          await fetchFinalAnalysis(analysisCreated.id)
        },
        onComplete: async () => {
          await fetchFinalAnalysis(analysisCreated.id)
        }
      })

      // 3. Start fallback active polling watcher (guarantees completion even if SSE stalls)
      startFallbackPolling(analysisCreated.id)
    } catch (err) {
      console.error("Failed to start analysis:", err)
      setLoading(false)
      const detail = err.response?.data?.detail || err.message || "Failed to start analysis"
      setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
  }

  async function fetchFinalAnalysis(analysisId, maxPollAttempts = 45) {
    let attempts = 0
    let lastFetched = null

    try {
      while (attempts < maxPollAttempts) {
        attempts++
        try {
          const finalAnalysis = await analysisService.get(analysisId)
          lastFetched = finalAnalysis

          // If still running, poll every 1.5s and sync live traces
          if (finalAnalysis.status === 'pending' || finalAnalysis.status === 'processing') {
            try {
              const traceList = await analysisService.trace(analysisId)
              if (traceList && traceList.length > 0) {
                setTraceEvents(traceList)
              }
            } catch {
              // Ignore trace polling errors
            }
            await new Promise((r) => setTimeout(r, 1500))
            continue
          }

          // Terminal state (completed, abstained, or failed): fetch claims, evidence, trace safely
          const [claimsRes, evidenceRes, traceRes] = await Promise.allSettled([
            analysisService.claims(analysisId),
            analysisService.evidence(analysisId),
            analysisService.trace(analysisId),
          ])

          const claims = claimsRes.status === 'fulfilled' ? claimsRes.value : []
          const evidence = evidenceRes.status === 'fulfilled' ? evidenceRes.value : []
          const trace = traceRes.status === 'fulfilled' ? traceRes.value : []

          const fullAnalysis = {
            ...finalAnalysis,
            claims: claims || [],
            evidence: evidence || [],
            trace: (trace && trace.length > 0) ? trace : traceEvents,
          }

          setAnalysis(fullAnalysis)
          setActiveTab('answer')
          return
        } catch (err) {
          console.error("Polling error fetching analysis status:", err)
          await new Promise((r) => setTimeout(r, 2000))
        }
      }

      // If loop exhausted (timed out waiting for background task):
      if (lastFetched) {
        setAnalysis(lastFetched)
        setActiveTab('answer')
      } else {
        setErrorMsg("Analysis execution timed out. Please check again in a few moments.")
      }
    } catch (err) {
      console.error("Failed to fetch final analysis data:", err)
      const detail = err.response?.data?.detail || err.message || "Failed to fetch analysis"
      setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setLoading(false)
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      if (streamRef.current) {
        try {
          streamRef.current.close()
        } catch {
          // ignore
        }
        streamRef.current = null
      }
    }
  }

  const TABS = [
    { id: 'answer',    label: 'Answer' },
    { id: 'evidence',  label: `Evidence ${analysis ? `(${analysis.evidence?.length || 0})` : ''}` },
    { id: 'claims',    label: `Claims ${analysis ? `(${analysis.claims?.length || 0})` : ''}` },
    { id: 'trace',     label: 'Trace' },
  ]

  async function handleExportDossier() {
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

  // Determine which trace events to show (live during load, or fetched after)
  const currentTraceEvents = loading ? traceEvents : (analysis?.trace || traceEvents)
  const recoveryRuns = currentTraceEvents
    .filter(e => e.event && (e.event === TraceEventType.RECOVERY_REWRITE || e.event === TraceEventType.RECOVERY_RE_RETRIEVE || e.event.startsWith('recovery.')))
    .map(e => ({
      strategy: e.event === TraceEventType.RECOVERY_REWRITE ? 'Targeted Query Rewrite' : 'Expanded Context Retrieval',
      reason: e.data?.message || 'Threshold checks failed, attempting adaptive healing',
      result: 'Context augmented, re-evaluating reliability',
      success: true,
    }))

  return (
    <AppLayout>
      <div className="flex flex-col md:flex-row h-full min-h-0 w-full overflow-hidden">
        {/* ── Left: Query panel ────────────────────────────────── */}
        <div className="w-full md:w-[320px] lg:w-[360px] xl:w-[400px] shrink-0 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col bg-surface-900/50 backdrop-blur-md h-auto md:h-full overflow-hidden">
          <div className="p-4 border-b border-slate-800 shrink-0">
            <h2 className="font-semibold text-white flex items-center gap-2 text-sm">
              <Zap size={16} className="text-primary-400" /> Playground
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Reliability & provenance workbench</p>
          </div>

          <form onSubmit={handleSubmit} className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {/* Scrollable form inputs area */}
            <div className="p-4 space-y-4 flex-1 min-h-0 overflow-y-auto">
              {errorMsg && (
                <div role="alert" className="p-3 bg-red-950/60 border border-red-800/80 rounded-lg text-xs text-red-300 flex items-start justify-between gap-2">
                  <span>{errorMsg}</span>
                  <button
                    type="button"
                    onClick={() => setErrorMsg('')}
                    aria-label="Dismiss error"
                    className="text-red-400 hover:text-red-200 text-sm font-bold leading-none shrink-0"
                  >
                    &times;
                  </button>
                </div>
              )}
              {/* KB selector */}
              <div className="space-y-1.5">
                <label className="section-heading" htmlFor="kb-select">Knowledge Base</label>
                <div className="relative">
                  <Database size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <select
                    id="kb-select"
                    value={kbId}
                    onChange={e => setKbId(e.target.value)}
                    className="w-full bg-surface-800 border border-slate-700 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50 appearance-none"
                    disabled={loading}
                  >
                    <option value="">— select a KB —</option>
                    {knowledgeBases?.map(kb => (
                      <option key={kb.id} value={kb.id}>{kb.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Query */}
              <div className="space-y-1.5">
                <label className="section-heading" htmlFor="query-input">Query</label>
                <textarea
                  id="query-input"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Ask a question about your documents…"
                  rows={5}
                  className="w-full min-h-[110px] bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-600 transition-colors"
                  disabled={loading}
                />
              </div>

              {/* Web Search Grounding (MCP) */}
              <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-2.5 transition-colors hover:border-slate-700">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="web-search-toggle"
                    className="flex items-center gap-2 text-xs font-semibold text-slate-200 cursor-pointer"
                  >
                    <Globe className={`w-3.5 h-3.5 ${enableWebSearch ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span>Web Search Grounding</span>
                    <span className="rounded bg-cyan-950/80 px-1.5 py-0.5 text-[10px] font-medium text-cyan-300 border border-cyan-700/40">
                      MCP
                    </span>
                  </label>
                  <input
                    type="checkbox"
                    id="web-search-toggle"
                    checked={enableWebSearch}
                    onChange={e => setEnableWebSearch(e.target.checked)}
                    disabled={loading}
                    className="h-4 w-4 rounded border-slate-700 bg-surface-900 text-primary-500 focus:ring-primary-500 cursor-pointer"
                  />
                </div>

                {enableWebSearch && (
                  <div className="pt-2 border-t border-slate-800 space-y-2">
                    <span className="text-[11px] text-slate-400 block font-medium">MCP Search Engine:</span>
                    <div className="grid grid-cols-3 gap-1 bg-surface-900 p-1 rounded-lg border border-slate-800">
                      <button
                        type="button"
                        disabled={loading}
                        onClick={() => setWebSearchProvider('tavily')}
                        className={`text-[11px] py-1 px-1.5 rounded font-medium transition-all ${
                          webSearchProvider === 'tavily'
                            ? 'bg-primary-600/30 text-primary-300 border border-primary-500/40 shadow-sm'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Tavily
                      </button>
                      <button
                        type="button"
                        disabled={loading}
                        onClick={() => setWebSearchProvider('duckduckgo')}
                        className={`text-[11px] py-1 px-1.5 rounded font-medium transition-all ${
                          webSearchProvider === 'duckduckgo'
                            ? 'bg-amber-600/30 text-amber-300 border border-amber-500/40 shadow-sm'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        DuckDuckGo
                      </button>
                      <button
                        type="button"
                        disabled={loading}
                        onClick={() => setWebSearchProvider('both')}
                        className={`text-[11px] py-1 px-1.5 rounded font-medium transition-all ${
                          webSearchProvider === 'both'
                            ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 shadow-sm'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Both (Hybrid)
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-400 leading-tight">
                      {webSearchProvider === 'tavily' && '⚡ High-accuracy AI RAG search with clean parsed content'}
                      {webSearchProvider === 'duckduckgo' && '🆓 100% Free search, zero API key or configuration required'}
                      {webSearchProvider === 'both' && '🌐 Parallel search across Tavily + DuckDuckGo with URL deduplication'}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Docked submit button (always visible, never cut off) */}
            <div className="p-4 border-t border-slate-800/80 bg-surface-900/90 backdrop-blur-md shrink-0">
              <button
                type="submit"
                disabled={loading || !query.trim() || !kbId}
                id="run-analysis"
                className="btn-primary w-full flex items-center justify-center gap-2 shadow-lg shadow-primary-950/60"
              >
                {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                {loading ? 'Executing Pipeline…' : 'Run Analysis'}
              </button>
            </div>
          </form>
        </div>

        {/* ── Right: Results panel ──────────────────────────────── */}
        <div className="flex-1 min-w-0 h-full min-h-0 flex flex-col overflow-hidden bg-surface-950/40">
          {!analysis && !loading && (
            <div className="flex-1 min-h-0 flex flex-col items-center justify-center text-center p-8 space-y-5 overflow-y-auto">
              <div className="relative">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-primary-600/20 via-cyan-500/10 to-transparent border border-primary-500/30 flex items-center justify-center shadow-glow-cyan animate-float">
                  <Zap size={32} className="text-cyan-400" />
                </div>
                <div className="absolute -inset-2 rounded-3xl border border-cyan-500/20 animate-pulse-slow pointer-events-none" />
              </div>
              <div className="max-w-sm space-y-2">
                <h3 className="text-base font-semibold text-slate-100 tracking-tight">
                  Awaiting Telemetry Query
                </h3>
                <p className="text-slate-400 text-xs leading-relaxed">
                  Select a knowledge base, configure live web grounding, and execute your prompt to observe closed-loop NLI claim verification in real-time.
                </p>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex-1 min-h-0 flex flex-col p-4 sm:p-6 space-y-4 overflow-hidden">
              {/* Ultra-Premium Executive Telemetry HUD */}
              <PipelineTelemetryHUD
                events={currentTraceEvents}
                query={query}
                enableWebSearch={enableWebSearch}
                webSearchProvider={webSearchProvider}
              />

              {/* Execution Trace Stream Dedicated Scroll Container */}
              <div className="flex-1 min-h-0 flex flex-col rounded-2xl border border-slate-800 bg-surface-900/50 backdrop-blur-sm p-4 overflow-hidden shadow-lg shadow-black/20">
                <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800/80 shrink-0">
                  <div className="flex items-center gap-2">
                    <span className="section-heading !mb-0 text-slate-200">Real-Time Event Stream</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-950/70 border border-cyan-800/40 text-cyan-300">
                      {currentTraceEvents.length} events logged
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
          )}

          {analysis && !loading && (
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              {/* High-Tech Telemetry Header */}
              <div className="shrink-0 p-4 border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-3 bg-surface-900/70 backdrop-blur-md">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusDot status={analysis.status} />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200 truncate font-semibold">{analysis.query}</p>
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

              {/* Tabs with glowing indicator */}
              <div className="shrink-0 flex border-b border-slate-800/80 px-4 bg-surface-900/30">
                {TABS.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`relative px-4 py-2.5 text-xs font-semibold uppercase tracking-wider transition-all mr-2 ${
                      activeTab === tab.id
                        ? 'text-cyan-300'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <span>{tab.label}</span>
                    {activeTab === tab.id && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-primary-500 to-cyan-400 shadow-glow-cyan" />
                    )}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
                {activeTab === 'answer' && (
                  <div className="space-y-5">
                    {(analysis.status === 'failed' || analysis.reliability?.status === 'FAILED') && (
                       <div className="rounded-xl border border-red-800/50 bg-red-950/30 p-4 shadow-glow-crimson">
                         <p className="text-sm font-medium text-red-300">
                           {analysis.status === 'failed'
                             ? `Analysis failed: ${analysis.diagnosis?.failures?.[0] || 'Unknown error occurred'}`
                             : `Reliability check failed: ${analysis.diagnosis?.failures?.[0] || 'Thresholds not met'}`}
                         </p>
                       </div>
                    )}

                    {(analysis.status === 'abstained' || analysis.reliability?.status === 'ABSTAINED') && (
                      <div className="rounded-xl border border-amber-800/50 bg-amber-950/30 p-4 shadow-glow-amber">
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
                        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800/80">
                          <div className="flex items-center gap-2">
                            <span className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
                              <Sparkles size={14} />
                            </span>
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                              Grounded Synthesis
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
                  </div>
                )}

                {activeTab === 'evidence' && (
                  <EvidenceViewer chunks={analysis.evidence || []} />
                )}

                {activeTab === 'claims' && (
                  <ClaimInspector claims={analysis.claims || []} />
                )}

                {activeTab === 'trace' && (
                  <ExecutionTrace events={currentTraceEvents} isLive={false} />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
