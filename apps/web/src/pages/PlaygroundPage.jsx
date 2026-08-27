import { useState } from 'react'
import { ChevronRight, Database, Loader2, Zap } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import { ReliabilityBadge, ClaimStateBadge, StatusDot } from '@/components/workbench/ReliabilityBadge'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { ExecutionTrace, RecoveryTimeline } from '@/components/workbench/ExecutionTrace'

/**
 * PlaygroundPage — the core TRUSTRAG workbench UI.
 * Shows the full pipeline: Query → Evidence → Answer → Claims → Verification
 * → Reliability → Diagnosis → Recovery → Final Decision.
 *
 * Phase 6+ wires this to the real analysis API + SSE stream.
 * For Phase 2, the UI structure and components are fully built with mock state.
 */

const MOCK_ANALYSIS = {
  status: 'completed',
  query: 'What is the refund policy and how long does processing take?',
  answer: 'Refunds are available for 45 days from the purchase date. Processing typically takes 7 business days.',
  reliability: { score: 0.78, status: 'TRUSTED' },
  diagnosis: { type: null, failures: [] },
  claims: [
    { id: 'c1', text: 'Refunds are available for 45 days from the purchase date.', state: 'SUPPORTED', explanation: 'Policy v4 explicitly states 45-day window.', evidence_ids: ['e1'] },
    { id: 'c2', text: 'Processing typically takes 7 business days.', state: 'UNSUPPORTED', explanation: 'No evidence found for processing time.', evidence_ids: [] },
  ],
  evidence: [
    { id: 'e1', text: 'Customers may request a refund within 45 days of purchase. Refund eligibility is subject to product condition review.', filename: 'refund-policy-v4.pdf', retrieval_score: 0.921, fusion_score: 0.887, method: 'hybrid', integrity_status: 'ok' },
    { id: 'e2', text: 'All return requests must be submitted through the customer portal.', filename: 'returns-guide.pdf', retrieval_score: 0.743, fusion_score: 0.651, method: 'dense', integrity_status: 'ok' },
  ],
  trace: [
    { event: 'analysis.started',     timestamp: new Date().toISOString(), data: {} },
    { event: 'retrieval.completed',  timestamp: new Date().toISOString(), data: { message: '20 chunks retrieved' } },
    { event: 'generation.completed', timestamp: new Date().toISOString(), data: { latency_ms: 1240 } },
    { event: 'claims.extracted',     timestamp: new Date().toISOString(), data: { message: '2 claims' } },
    { event: 'verification.completed', timestamp: new Date().toISOString(), data: {} },
    { event: 'analysis.completed',   timestamp: new Date().toISOString(), data: {} },
  ],
}

export default function PlaygroundPage() {
  const [query,      setQuery]      = useState('')
  const [kbId,       setKbId]       = useState('')
  const [loading,    setLoading]    = useState(false)
  const [analysis,   setAnalysis]   = useState(null)
  const [activeTab,  setActiveTab]  = useState('answer')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setAnalysis(null)
    // Phase 6: replace with real API call + SSE stream
    await new Promise(r => setTimeout(r, 1500))
    setAnalysis(MOCK_ANALYSIS)
    setLoading(false)
    setActiveTab('answer')
  }

  const TABS = [
    { id: 'answer',    label: 'Answer' },
    { id: 'evidence',  label: `Evidence ${analysis ? `(${analysis.evidence.length})` : ''}` },
    { id: 'claims',    label: `Claims ${analysis ? `(${analysis.claims.length})` : ''}` },
    { id: 'trace',     label: 'Trace' },
  ]

  return (
    <AppLayout>
      <div className="flex h-full">
        {/* ── Left: Query panel ────────────────────────────────── */}
        <div className="w-80 shrink-0 border-r border-slate-800 flex flex-col bg-surface-900/40">
          <div className="p-4 border-b border-slate-800">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Zap size={16} className="text-primary-400" /> Playground
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Run TRUSTRAG analysis</p>
          </div>

          <form onSubmit={handleSubmit} className="p-4 space-y-4 flex-1 flex flex-col">
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
                >
                  <option value="">— select a KB —</option>
                  {/* Populated from API in Phase 3 */}
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
              />
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              id="run-analysis"
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
              {loading ? 'Analyzing…' : 'Run Analysis'}
            </button>
          </form>
        </div>

        {/* ── Right: Results panel ──────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
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
              <ExecutionTrace events={[]} isLive={true} />
            </div>
          )}

          {analysis && (
            <>
              {/* Reliability header */}
              <div className="shrink-0 p-4 border-b border-slate-800 flex items-center justify-between gap-4 bg-surface-900/30">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusDot status={analysis.status} />
                  <p className="text-sm text-slate-300 truncate font-medium">{analysis.query}</p>
                </div>
                <ReliabilityBadge
                  score={analysis.reliability.score}
                  status={analysis.reliability.status}
                  size="md"
                />
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
                    <div className="glass-card p-4">
                      <p className="section-heading">Generated Answer</p>
                      <p className="text-slate-200 text-sm leading-relaxed">{analysis.answer}</p>
                    </div>

                    {analysis.claims.some(c => c.state === 'UNSUPPORTED' || c.state === 'CONTRADICTED') && (
                      <div className="rounded-lg border border-amber-800/40 bg-amber-950/20 px-4 py-3">
                        <p className="text-sm font-medium text-amber-400">
                          ⚠ Some claims could not be verified. Inspect the Claims tab.
                        </p>
                      </div>
                    )}

                    <RecoveryTimeline recoveryRuns={[]} />
                  </div>
                )}

                {activeTab === 'evidence' && (
                  <EvidenceViewer chunks={analysis.evidence} />
                )}

                {activeTab === 'claims' && (
                  <ClaimInspector claims={analysis.claims} />
                )}

                {activeTab === 'trace' && (
                  <ExecutionTrace events={analysis.trace} isLive={false} />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
