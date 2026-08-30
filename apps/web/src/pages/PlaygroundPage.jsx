import { useState, useRef, useEffect } from 'react'
import { Database, Loader2, Zap, Download } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { ReliabilityBadge, StatusDot } from '@/components/workbench/ReliabilityBadge'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { ExecutionTrace, RecoveryTimeline } from '@/components/workbench/ExecutionTrace'
import { kbService, analysisService } from '@/services/api'
import api, { openAnalysisStream } from '@/lib/api'

export default function PlaygroundPage() {
  const [query, setQuery] = useState('')
  const [kbId, setKbId] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [traceEvents, setTraceEvents] = useState([])
  const [activeTab, setActiveTab] = useState('trace')
  const [errorMsg, setErrorMsg] = useState('')
  
  const streamRef = useRef(null)

  // Fetch KBs for the dropdown
  const { data: knowledgeBases } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list
  })

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.close()
      }
    }
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!query.trim() || !kbId) return
    
    setLoading(true)
    setAnalysis(null)
    setTraceEvents([])
    setErrorMsg('')
    setActiveTab('trace') // Default to trace while running so user sees progress

    try {
      // 1. Create analysis run
      const analysisCreated = await analysisService.create({ 
        knowledge_base_id: kbId, 
        query 
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

          if (finalAnalysis.status === 'completed') {
            setActiveTab('answer')
          }
          return
        } catch (err) {
          console.error("Polling error fetching analysis status:", err)
          await new Promise((r) => setTimeout(r, 2000))
        }
      }

      // If loop exhausted (timed out waiting for background task):
      if (lastFetched) {
        setAnalysis(lastFetched)
      } else {
        setErrorMsg("Analysis execution timed out. Please check again in a few moments.")
      }
    } catch (err) {
      console.error("Failed to fetch final analysis data:", err)
      const detail = err.response?.data?.detail || err.message || "Failed to fetch analysis"
      setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setLoading(false)
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
    .filter(e => e.event && e.event.startsWith('recovery.'))
    .map(e => ({
      strategy: e.event === 'recovery.rewrite' ? 'Targeted Query Rewrite' : 'Expanded Context Retrieval',
      reason: e.data?.message || 'Threshold checks failed, attempting adaptive healing',
      result: 'Context augmented, re-evaluating reliability',
      success: true,
    }))

  return (
    <AppLayout>
      <div className="flex flex-col lg:flex-row h-full min-h-[calc(100vh-4.5rem)]">
        {/* ── Left: Query panel ────────────────────────────────── */}
        <div className="w-full lg:w-80 shrink-0 lg:border-r border-b lg:border-b-0 border-slate-800 flex flex-col bg-surface-900/40">
          <div className="p-4 border-b border-slate-800">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Zap size={16} className="text-primary-400" /> Playground
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Run TRUSTRAG analysis</p>
          </div>

          <form onSubmit={handleSubmit} className="p-4 space-y-4 flex-1 flex flex-col">
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
            <div className="space-y-1.5 flex-1 flex flex-col">
              <label className="section-heading" htmlFor="query-input">Query</label>
              <textarea
                id="query-input"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Ask a question about your documents…"
                rows={5}
                className="flex-1 min-h-[120px] bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-600 transition-colors"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim() || !kbId}
              id="run-analysis"
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
              {loading ? 'Analyzing…' : 'Run Analysis'}
            </button>
          </form>
        </div>

        {/* ── Right: Results panel ──────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-y-auto lg:overflow-hidden">
          {!analysis && !loading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-primary-600/10 border border-primary-700/30 flex items-center justify-center">
                <Zap size={28} className="text-primary-400/60" />
              </div>
              <div>
                <p className="text-slate-300 font-medium">Submit a query to begin</p>
                <p className="text-slate-600 text-sm mt-1">
                  Select a knowledge base and enter your question
                </p>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex-1 flex flex-col overflow-y-auto p-5">
              <div className="flex items-center gap-3 mb-4">
                <StatusDot status="running" />
                <span className="text-sm text-slate-400">Running TRUSTRAG pipeline…</span>
              </div>
              <ExecutionTrace events={currentTraceEvents} isLive={true} />
            </div>
          )}

          {analysis && !loading && (
            <>
              {/* Reliability header */}
              <div className="shrink-0 p-4 border-b border-slate-800 flex items-center justify-between gap-4 bg-surface-900/30">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusDot status={analysis.status} />
                  <p className="text-sm text-slate-300 truncate font-medium">{analysis.query}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
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
                    title="Export Open Knowledge JSON-LD Dossier"
                    className="px-2.5 py-1 text-xs border border-slate-700 hover:border-slate-500 rounded-lg text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors bg-surface-800"
                  >
                    <Download size={13} />
                    Export
                  </button>
                </div>
              </div>

              {/* Tabs */}
              <div className="shrink-0 flex border-b border-slate-800 px-4 bg-surface-900/20">
                {TABS.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-3 py-2.5 text-sm font-medium border-b-2 transition-colors mr-1 ${
                      activeTab === tab.id
                        ? 'border-primary-500 text-primary-300'
                        : 'border-transparent text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="flex-1 overflow-y-auto p-5">
                {activeTab === 'answer' && (
                  <div className="space-y-5">
                    {(analysis.status === 'failed' || analysis.reliability?.status === 'FAILED') && (
                       <div className="rounded-lg border border-red-800/40 bg-red-950/20 px-4 py-3">
                         <p className="text-sm font-medium text-red-400">
                           {analysis.status === 'failed'
                             ? `Analysis failed: ${analysis.diagnosis?.failures?.[0] || 'Unknown error occurred'}`
                             : `Reliability check failed: ${analysis.diagnosis?.failures?.[0] || 'Thresholds not met'}`}
                         </p>
                       </div>
                    )}

                    {(analysis.status === 'abstained' || analysis.reliability?.status === 'ABSTAINED') && (
                      <div className="rounded-lg border border-amber-800/40 bg-amber-950/20 px-4 py-3">
                        <p className="text-sm font-medium text-amber-400">
                          ⊘ The agent abstained from answering because the retrieved document segments did not contain sufficient factual evidence to answer this question reliably without hallucinating.
                        </p>
                        <p className="text-xs text-amber-400/80 mt-1">
                          Tip: Try phrasing your question using specific topic names, section headings, or asking for an overview of topics covered in the document.
                        </p>
                      </div>
                    )}
                    
                    {analysis.answer && (
                      <div className="glass-card p-4">
                        <p className="section-heading">Generated Answer</p>
                        <p className="text-slate-200 text-sm leading-relaxed">{analysis.answer}</p>
                      </div>
                    )}

                    {analysis.claims?.some(c => c.state === 'NEUTRAL' || c.state === 'CONTRADICTED') && (
                      <div className="rounded-lg border border-amber-800/40 bg-amber-950/20 px-4 py-3 mt-4">
                        <p className="text-sm font-medium text-amber-400">
                          ⚠ Some claims could not be verified. Inspect the Claims tab.
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
            </>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
