import { useState, useRef, useEffect } from 'react'
import { 
  Database, Loader2, Zap, Download, Globe, Copy, Sparkles, Check, Cpu, 
  RotateCcw, Clock, AlertTriangle, ArrowRight, CornerDownLeft, Shield, FileCheck, Layers
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { motion, useSpring, useMotionValue } from 'motion/react'
import AppLayout from '@/layouts/AppLayout'
import { ReliabilityBadge, StatusDot } from '@/components/workbench/ReliabilityBadge'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { ExecutionTrace, RecoveryTimeline } from '@/components/workbench/ExecutionTrace'
import { TraceEventType } from '@/components/workbench/traceEvents'
import { kbService, analysisService, modelService } from '@/services/api'
import { FormattedAnswer } from '@/components/workbench/FormattedAnswer'
import { PipelineTelemetryHUD } from '@/components/workbench/PipelineTelemetryHUD'
import api, { openAnalysisStream } from '@/lib/api'

const SAMPLE_PRESETS = [
  "What is the cancellation and refund policy?",
  "Are there any conflicting coverage terms or exclusions?",
  "Summarize key compliance obligations with exact citations",
]

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
  const [elapsedSec, setElapsedSec] = useState(0)

const streamRef = useRef(null)
const pollTimerRef = useRef(null)
const finalizedRef = useRef(false)

  // Track elapsed timer during execution
  useEffect(() => {
    let timer = null
    if (loading) {
      setElapsedSec(0)
      timer = setInterval(() => {
        setElapsedSec(prev => +(prev + 0.1).toFixed(1))
      }, 100)
    } else {
      if (timer) clearInterval(timer)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [loading])

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

  // Auto-select first KB if none selected
  useEffect(() => {
    if (!kbId && knowledgeBases && knowledgeBases.length > 0) {
      setKbId(knowledgeBases[0].id)
    }
  }, [knowledgeBases, kbId])

  // Fetch AI Providers and local models
  const { data: providersData } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
  })

  const [selectedProvider, setSelectedProvider] = useState('ollama')
  const [selectedModel, setSelectedModel] = useState('granite4.2:3b-q4_K_M')

  const [selectedEmbeddingProvider, setSelectedEmbeddingProvider] = useState('ollama')
  const [selectedEmbeddingModel, setSelectedEmbeddingModel] = useState('embeddinggemma:300m-qat-q8_0')

  // Auto-sync embedding defaults when provider data loads (once on mount)
  useEffect(() => {
    if (providersData?.active_embedding_provider) {
      setSelectedEmbeddingProvider(providersData.active_embedding_provider)
    }
    if (providersData?.active_embedding_model) {
      setSelectedEmbeddingModel(providersData.active_embedding_model)
    }
  }, [])

  const activeProviderInfo = providersData?.providers?.[selectedProvider]
  const availableModels = activeProviderInfo?.models?.length 
    ? activeProviderInfo.models 
    : (selectedProvider === 'ollama' 
        ? ['granite4.2:3b-q4_K_M', 'qwen3.5:4b', 'gemma4:e2b-it-qat'] 
        : (selectedProvider === 'llama_cpp' 
            ? ['ibm-granite/granite-4.2-3b-GGUF:Q4_K_M', 'psychopenguin/Qwen3.5-4B-Q4_K_M-GGUF:Q4_K_M', 'google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0'] 
            : ['default']))

  const activeEmbeddingProviderInfo = providersData?.embedding_providers?.[selectedEmbeddingProvider]
  const availableEmbeddingModels = activeEmbeddingProviderInfo?.models?.length
    ? activeEmbeddingProviderInfo.models
    : [
        { id: 'embeddinggemma:300m-qat-q8_0', name: 'embeddinggemma:300m-qat-q8_0 (768d)', dim: 768, tag: 'Ollama SOTA' },
        { id: 'ggml-org/embeddinggemma-300M-GGUF:Q8_0', name: 'embeddinggemma-300M (768d GGUF)', dim: 768, tag: 'llama.cpp Cache' },
        { id: 'BAAI/bge-small-en-v1.5', name: 'BAAI/bge-small-en-v1.5 (384d SOTA)', dim: 384, tag: 'Recommended' },
      ]

  const handleProviderChange = (providerKey) => {
    setSelectedProvider(providerKey)
    const prov = providersData?.providers?.[providerKey]
    if (prov?.default_model) {
      setSelectedModel(prov.default_model)
    } else if (providerKey === 'ollama') {
      setSelectedModel('granite4.2:3b-q4_K_M')
    } else if (providerKey === 'llama_cpp') {
      setSelectedModel('ibm-granite/granite-4.2-3b-GGUF:Q4_K_M')
    } else if (providerKey === 'gemini') {
      setSelectedModel('gemini-3.5-flash-lite')
    } else if (providerKey === 'nvidia') {
      setSelectedModel('meta/llama-3.3-70b-instruct')
    }
  }

  const handleEmbeddingProviderChange = (providerKey) => {
    setSelectedEmbeddingProvider(providerKey)
    const prov = providersData?.embedding_providers?.[providerKey]
    if (prov?.default_model) {
      setSelectedEmbeddingModel(prov.default_model)
    } else if (prov?.models?.[0]?.id) {
      setSelectedEmbeddingModel(prov.models[0].id)
    }
  }

  const handleReset = () => {
    setQuery('')
    setAnalysis(null)
    setTraceEvents([])
    setErrorMsg('')
    setActiveTab('answer')
  }

  const handlePresetSelect = (presetText) => {
    setQuery(presetText)
  }

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
          if (!finalizedRef.current) {
            finalizedRef.current = true
            await fetchFinalAnalysis(analysisId)
          }
        }
      } catch {
        // Ignore background polling errors
      }
    }, 2000)
  }

  async function handleSubmit(e) {
    if (e && e.preventDefault) e.preventDefault()
    if (!query.trim() || !kbId || loading) return
    
    setLoading(true)
    setAnalysis(null)
    setTraceEvents([])
    setErrorMsg('')
    setActiveTab('answer')

    try {
      // 1. Create analysis run
      const analysisCreated = await analysisService.create({ 
        knowledge_base_id: kbId, 
        query: query.trim(),
        enable_web_search: enableWebSearch,
        web_search_provider: webSearchProvider,
        llm_provider: selectedProvider,
        llm_model: selectedModel,
        embedding_provider: selectedEmbeddingProvider,
        embedding_model: selectedEmbeddingModel,
      })

      // 2. Connect to SSE stream
      finalizedRef.current = false
      streamRef.current = openAnalysisStream(analysisCreated.id, {
        onEvent: (eventData) => {
          setTraceEvents(prev => [...prev, eventData])
        },
        onError: async () => {
          // If SSE fails, wait a bit then fetch final state anyway
          if (!finalizedRef.current) {
            finalizedRef.current = true
            await fetchFinalAnalysis(analysisCreated.id)
          }
        },
        onComplete: async () => {
          if (!finalizedRef.current) {
            finalizedRef.current = true
            await fetchFinalAnalysis(analysisCreated.id)
          }
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

  // Keyboard shortcut listener: Cmd/Ctrl + Enter to run
  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  async function fetchFinalAnalysis(analysisId, maxPollAttempts = 45) {
    if (finalizedRef.current) return
    finalizedRef.current = true
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

  const selectedKb = knowledgeBases?.find(k => k.id === kbId)
  const answerWordCount = analysis?.answer ? analysis.answer.trim().split(/\s+/).filter(Boolean).length : 0
  const estimatedReadTime = Math.max(1, Math.ceil(answerWordCount / 180))

  return (
    <AppLayout>
      <div className="flex flex-col md:flex-row h-full min-h-0 w-full overflow-hidden">
        {/* ── Left: Query & Control Panel ───────────────────────── */}
        <div className="w-full md:w-[330px] lg:w-[370px] xl:w-[410px] shrink-0 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col bg-surface-900/60 backdrop-blur-md h-auto md:h-full overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-slate-800 shrink-0 flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-white flex items-center gap-2 text-sm">
                <span className="p-1 rounded-md bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
                  <Zap size={14} />
                </span>
                <span>Playground</span>
              </h2>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <p className="text-[11px] text-slate-400 font-medium">Reliability & Provenance Workbench</p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleReset}
              disabled={loading}
              title="Reset query and results (Clear)"
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-800 rounded-lg border border-slate-800 transition-colors"
            >
              <RotateCcw size={13} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {/* Scrollable form inputs area */}
            <div className="p-4 space-y-4 flex-1 min-h-0 overflow-y-auto">
              {errorMsg && (
                <div role="alert" className="p-3 bg-red-950/70 border border-red-800/80 rounded-xl text-xs text-red-300 flex items-start justify-between gap-2 shadow-glow-crimson animate-fade-in">
                  <div className="flex items-start gap-2">
                    <AlertTriangle size={14} className="shrink-0 mt-0.5 text-red-400" />
                    <span>{errorMsg}</span>
                  </div>
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

              {/* Knowledge Base selector */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <label className="section-heading !mb-0" htmlFor="kb-select">Knowledge Base</label>
                  {selectedKb && (
                    <span className="text-[10px] text-slate-400 font-mono">
                      {selectedKb.document_count ?? 0} docs
                    </span>
                  )}
                </div>
                <div className="relative">
                  <Database size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <select
                    id="kb-select"
                    value={kbId}
                    onChange={e => setKbId(e.target.value)}
                    className="w-full bg-surface-800 border border-slate-700/80 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50 appearance-none transition-colors"
                    disabled={loading}
                  >
                    <option value="">— select a KB —</option>
                    {knowledgeBases?.map(kb => (
                      <option key={kb.id} value={kb.id}>
                        {kb.name} ({kb.document_count ?? 0} docs)
                      </option>
                    ))}
                  </select>
                </div>
                {selectedKb && selectedKb.document_count === 0 && (
                  <p className="text-[10px] text-amber-400/90 leading-tight">
                    ⚠️ Selected knowledge base contains 0 indexed documents. Upload documents in the Knowledge Bases tab.
                  </p>
                )}
              </div>

              {/* AI Engine & Model Selector */}
              <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                    <Cpu className="w-3.5 h-3.5 text-primary-400" />
                    <span>AI Engine</span>
                  </label>
                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${
                    activeProviderInfo?.connected
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
                      : 'bg-amber-950/80 text-amber-400 border border-amber-800/40'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${activeProviderInfo?.connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                    {activeProviderInfo?.connected ? 'Connected' : 'Standby'}
                  </span>
                </div>

                {/* Hardware Adaptive Acceleration Pill */}
                {providersData?.hardware && (
                  <div className="p-2 rounded-lg bg-surface-900 border border-slate-800 flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <Zap size={13} className={providersData.hardware.accelerator === 'mps' ? 'text-amber-400' : 'text-cyan-400'} />
                      <span>
                        <strong className="text-slate-200">
                          {providersData.hardware.accelerator === 'mps' ? 'Metal (MPS)' : (providersData.hardware.accelerator === 'cuda' ? 'CUDA GPU' : 'CPU')}
                        </strong>
                        {' '}&bull; {providersData.hardware.memory?.total_gb}GB RAM
                      </span>
                    </div>
                    <span className="text-[10px] text-cyan-400 font-mono">
                      Target: {providersData.hardware.recommendations?.primary_llm?.split(':')[0]}
                    </span>
                  </div>
                )}

                {/* Provider Selector Grid */}
                <div className="grid grid-cols-2 gap-1.5 bg-surface-900 p-1 rounded-lg border border-slate-800">
                  <motion.button
                    type="button"
                    onClick={() => handleProviderChange('ollama')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedProvider === 'ollama'
                        ? 'bg-primary-600/30 text-primary-200 border border-primary-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>Ollama</span>
                    <span className="text-[9px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-emerald-400 font-mono">:11434</span>
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => handleProviderChange('llama_cpp')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedProvider === 'llama_cpp'
                        ? 'bg-cyan-600/30 text-cyan-200 border border-cyan-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>llama.cpp</span>
                    <span className="text-[9px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-cyan-400 font-mono">:8081</span>
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => handleProviderChange('gemini')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedProvider === 'gemini'
                        ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>Gemini</span>
                    <span className="text-[9px] text-slate-500">Cloud</span>
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => handleProviderChange('nvidia')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedProvider === 'nvidia'
                        ? 'bg-purple-600/30 text-purple-200 border border-purple-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>NVIDIA</span>
                    <span className="text-[9px] text-slate-500">Cloud</span>
                  </motion.button>
                </div>

                {/* Model Selection Dropdown */}
                <div className="space-y-1 pt-1 border-t border-slate-800">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-medium">Model:</span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {selectedProvider === 'ollama' ? ':11434' : (selectedProvider === 'llama_cpp' ? ':8081' : '')}
                    </span>
                  </div>
                  <div className="relative">
                    <select
                      value={selectedModel}
                      onChange={e => setSelectedModel(e.target.value)}
                      disabled={loading}
                      className="w-full bg-surface-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary-500/50"
                    >
                      {availableModels.map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* MCP Protocol Integration for Local LLMs */}
                {(selectedProvider === 'ollama' || selectedProvider === 'llama_cpp') && (
                  <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-1.5 text-cyan-300 font-medium">
                        <Sparkles size={12} className="text-cyan-400" />
                        <span>MCP Tool Grounding</span>
                      </div>
                      <span className="px-1.5 py-0.5 rounded bg-cyan-950/90 text-cyan-300 border border-cyan-700/50 text-[9px] font-mono">
                        Active
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 leading-relaxed">
                      Connected to local MCP tool suite: <code className="text-cyan-400 font-mono">trustrag_search</code>, <code className="text-cyan-400 font-mono">duckduckgo_search</code>, & <code className="text-cyan-400 font-mono">verify_claim</code>.
                    </p>
                  </div>
                )}
              </div>

              {/* Dense Embedding Model Selector */}
              <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Dense Embedding Model</span>
                  </label>
                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${
                    activeEmbeddingProviderInfo?.connected
                      ? 'bg-cyan-950/80 text-cyan-400 border border-cyan-800/40'
                      : 'bg-slate-800 text-slate-400 border border-slate-700/40'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${activeEmbeddingProviderInfo?.connected ? 'bg-cyan-400 animate-pulse' : 'bg-slate-500'}`} />
                    {selectedEmbeddingProvider === 'huggingface' ? 'Local BGE' : (selectedEmbeddingProvider === 'ollama' ? 'Local Ollama' : 'Cloud')}
                  </span>
                </div>

                {/* Embedding Provider Selector Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 bg-surface-900 p-1 rounded-lg border border-slate-800">
                  <motion.button
                    type="button"
                    onClick={() => handleEmbeddingProviderChange('ollama')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedEmbeddingProvider === 'ollama'
                        ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>Local Ollama</span>
                    <span className="text-[9px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-emerald-400 font-mono">768d</span>
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => handleEmbeddingProviderChange('llamacpp')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedEmbeddingProvider === 'llamacpp'
                        ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>Local llama.cpp</span>
                    <span className="text-[9px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-amber-400 font-mono">768d</span>
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => handleEmbeddingProviderChange('huggingface')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedEmbeddingProvider === 'huggingface'
                        ? 'bg-cyan-600/30 text-cyan-200 border border-cyan-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>Local BGE</span>
                    <span className="text-[9px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-cyan-400 font-mono">384d</span>
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => handleEmbeddingProviderChange('google_genai')}
                    disabled={loading}
                    whileTap={{ scale: 0.95 }}
                    className={`text-xs py-1 px-2 rounded-md font-medium flex items-center justify-between ${
                      selectedEmbeddingProvider === 'google_genai'
                        ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>Gemini Embed</span>
                    <span className="text-[9px] text-slate-500">Cloud</span>
                  </motion.button>
                </div>

                {/* Embedding Model Dropdown */}
                <div className="space-y-1 pt-1 border-t border-slate-800">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-medium">Embedding Model:</span>
                    <span className="font-mono text-[10px] text-cyan-400">
                      {availableEmbeddingModels.find(m => m.id === selectedEmbeddingModel)?.dim ? `${availableEmbeddingModels.find(m => m.id === selectedEmbeddingModel)?.dim}d vectors` : ''}
                    </span>
                  </div>
                  <div className="relative">
                    <select
                      value={selectedEmbeddingModel}
                      onChange={e => setSelectedEmbeddingModel(e.target.value)}
                      disabled={loading}
                      className="w-full bg-surface-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
                    >
                      {availableEmbeddingModels.map(m => (
                        <option key={m.id} value={m.id}>
                          {m.name || m.id} {m.tag ? `[${m.tag}]` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Query section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <label className="section-heading !mb-0" htmlFor="query-input">Query</label>
                  <span className={`text-[10px] font-mono ${
                    query.length > 1800 ? 'text-amber-400' : 'text-slate-500'
                  }`}>
                    {query.length} / 2000
                  </span>
                </div>

                <textarea
                  id="query-input"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your documents… (Press ⌘+Enter to run)"
                  rows={4}
                  className="w-full min-h-[105px] bg-surface-800 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-600 transition-colors"
                  disabled={loading}
                />

                {/* Quick Presets */}
                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider block">
                    Quick Prompts:
                  </span>
                  <div className="flex flex-col gap-1">
                    {SAMPLE_PRESETS.map((preset, idx) => (
                      <motion.button
                        key={idx}
                        type="button"
                        onClick={() => handlePresetSelect(preset)}
                        disabled={loading}
                        whileTap={{ scale: 0.98 }}
                        className="text-left text-[11px] text-slate-400 hover:text-cyan-300 hover:bg-surface-800/80 px-2 py-1 rounded-md border border-slate-800/80 hover:border-cyan-500/30 truncate"
                      >
                        {preset}
                      </motion.button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Web Search Grounding (MCP) - Explicit Checkbox Control */}
              <div className={`rounded-xl border p-3.5 space-y-3 transition-all shadow-sm ${
                enableWebSearch 
                  ? 'border-cyan-500/60 bg-cyan-950/20 ring-1 ring-cyan-500/20' 
                  : 'border-slate-800 bg-surface-850/60 hover:border-slate-700/80'
              }`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5">
                    <input
                      type="checkbox"
                      id="web-search-toggle"
                      checked={enableWebSearch}
                      onChange={e => setEnableWebSearch(e.target.checked)}
                      disabled={loading}
                      className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-surface-900 text-cyan-500 focus:ring-cyan-500 cursor-pointer accent-cyan-500"
                    />
                    <label
                      htmlFor="web-search-toggle"
                      className="cursor-pointer select-none space-y-0.5"
                    >
                      <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                        <Globe className={`w-3.5 h-3.5 ${enableWebSearch ? 'text-cyan-400' : 'text-slate-500'}`} />
                        <span>Enable MCP Web Search Grounding</span>
                        <span className="rounded bg-cyan-950/80 px-1.5 py-0.5 text-[10px] font-medium text-cyan-300 border border-cyan-700/40">
                          MCP Tool
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        {enableWebSearch 
                          ? 'Active: Live internet grounding will be queried via MCP.'
                          : 'Unchecked: 100% Private Local RAG — searches only your Knowledge Base.'}
                      </p>
                    </label>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono shrink-0 border ${
                    enableWebSearch
                      ? 'bg-cyan-950 text-cyan-300 border-cyan-700/60 font-semibold shadow-sm'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}>
                    {enableWebSearch ? 'MCP ENABLED' : 'OFFLINE ONLY'}
                  </span>
                </div>

                {enableWebSearch && (
                  <div className="pt-2 border-t border-slate-800/80 space-y-2 animate-fade-in">
                    <span className="text-[11px] text-slate-300 block font-medium">Select MCP Search Engine:</span>
                    <div className="grid grid-cols-3 gap-1 bg-surface-900 p-1 rounded-lg border border-slate-800">
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
                        DuckDuckGo (Free)
                      </button>
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
                        Tavily (AI)
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
                        Both (Parallel)
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-400 leading-tight">
                      {webSearchProvider === 'duckduckgo' && '🆓 100% Free search, zero API key or configuration required.'}
                      {webSearchProvider === 'tavily' && '⚡ High-accuracy AI RAG search with clean parsed content.'}
                      {webSearchProvider === 'both' && '🌐 Parallel search across Tavily + DuckDuckGo with URL deduplication.'}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Docked submit button (always visible, never cut off) */}
            <div className="p-4 border-t border-slate-800/80 bg-surface-900/95 backdrop-blur-md shrink-0 space-y-1.5">
              <button
                type="submit"
                disabled={loading || !query.trim() || !kbId}
                id="run-analysis"
                className="btn-primary w-full flex items-center justify-center gap-2 shadow-lg shadow-primary-950/60 transition-all relative overflow-hidden"
              >
                {loading ? (
                  <>
                    <Loader2 size={14} className="animate-spin text-cyan-300" />
                    <span>Executing Pipeline ({elapsedSec}s)…</span>
                  </>
                ) : (
                  <>
                    <Zap size={14} className="text-cyan-300" />
                    <span>Run Analysis</span>
                    <span className="text-[10px] opacity-75 font-mono ml-1 flex items-center gap-0.5">
                      <CornerDownLeft size={10} /> ⌘Enter
                    </span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* ── Right: Results & Telemetry Panel ─────────────────── */}
        <div className="flex-1 min-w-0 h-full min-h-0 flex flex-col overflow-hidden bg-surface-950/40">
          {/* Empty State / Mission Control */}
          {!analysis && !loading && (
            <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-6 sm:p-10 space-y-6 overflow-y-auto">
              <div className="relative">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-primary-600/20 via-cyan-500/10 to-transparent border border-primary-500/30 flex items-center justify-center shadow-glow-cyan animate-float">
                  <Zap size={34} className="text-cyan-400" />
                </div>
                <div className="absolute -inset-2.5 rounded-3xl border border-cyan-500/20 animate-pulse-slow pointer-events-none" />
              </div>

              <div className="max-w-md text-center space-y-2">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/70 border border-cyan-700/50 text-cyan-300 text-[11px] font-mono mb-1">
                  <Shield size={12} className="text-cyan-400" />
                  <span>Interactive Verification Workbench</span>
                </div>
                <h3 className="text-lg font-bold text-slate-100 tracking-tight">
                  Awaiting Pipeline Query
                </h3>
                <p className="text-slate-400 text-xs leading-relaxed">
                  Select a knowledge base, configure your AI engine, and execute your prompt to observe closed-loop NLI claim verification in real-time.
                </p>
              </div>

              {/* 3 Value Proposition Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl w-full text-left">
                <div className="p-3.5 rounded-xl border border-slate-800/90 bg-surface-900/60 backdrop-blur-sm space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                    <FileCheck size={14} className="text-emerald-400" />
                    <span>Closed-Loop NLI</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Decomposes generated answers into atomic claims and cross-verifies every proposition against citations.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-800/90 bg-surface-900/60 backdrop-blur-sm space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                    <Sparkles size={14} className="text-cyan-400" />
                    <span>Self-Healing Loop</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    LangGraph state machine automatically triggers targeted query rewrites and context expansions when uncertainty occurs.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-800/90 bg-surface-900/60 backdrop-blur-sm space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                    <Globe size={14} className="text-primary-400" />
                    <span>Zero-Key MCP Web</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Dynamic Model Context Protocol tool execution pulls fresh web facts via DuckDuckGo with 0 API keys.
                  </p>
                </div>
              </div>

              {/* Bottom Quick-Start Action */}
              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    if (SAMPLE_PRESETS[0]) handlePresetSelect(SAMPLE_PRESETS[0])
                  }}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-surface-800 border border-slate-700/80 hover:border-cyan-500/50 flex items-center gap-1.5 transition-all shadow-sm"
                >
                  <span>Load Sample Query</span>
                  <ArrowRight size={12} className="text-cyan-400" />
                </button>
              </div>
            </div>
          )}

          {/* Loading State with Real-Time Event Stream */}
          {loading && (
            <div className="flex-1 min-h-0 flex flex-col p-4 sm:p-6 space-y-4 overflow-hidden">
              {/* Ultra-Premium Executive Telemetry HUD */}
              <PipelineTelemetryHUD
                events={currentTraceEvents}
                query={query}
                enableWebSearch={enableWebSearch}
                webSearchProvider={webSearchProvider}
                provider={selectedProvider}
                model={selectedModel}
                embeddingModel={selectedEmbeddingModel}
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

          {/* Analysis Results View */}
          {analysis && !loading && (
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              {/* High-Tech Telemetry Header */}
              <div className="shrink-0 p-4 border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-3 bg-surface-900/70 backdrop-blur-md">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusDot status={analysis.status} />
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
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-950/80 text-purple-300 border border-purple-700/50 text-[10px] font-mono">
                      <Cpu size={11} className="text-purple-400" />
                      {analysis.llm_provider.toUpperCase()}: {analysis.llm_model || 'DEFAULT'}
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

              {/* Tabs with spring-animated indicator */}
              <div className="shrink-0 relative border-b border-slate-800/80 px-4 bg-surface-900/30">
                <motion.div
                  layoutId="active-tab"
                  transition={{ type: 'spring', damping: 1.0, response: 0.3 }}
                  className="absolute bottom-0 h-0.5 bg-gradient-to-r from-primary-500 to-cyan-400 shadow-glow-cyan"
                  style={{ width: 0 }} // width set by layout
                />
                {TABS.map(tab => (
                  <motion.button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    whileTap={{ scale: 0.98 }}
                    className={`relative px-4 py-2.5 text-xs font-semibold uppercase tracking-wider ${
                      activeTab === tab.id
                        ? 'text-cyan-300'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                    layout
                  >
                    <span>{tab.label}</span>
                  </motion.button>
                ))}
              </div>

              {/* Tab content */}
              <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
                {activeTab === 'answer' && (
                  <div className="space-y-5">
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
                        {/* Answer Metadata Ribbon */}
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
