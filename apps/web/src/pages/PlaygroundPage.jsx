import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { TraceEventType } from '@/components/workbench/traceEvents'
import { kbService, analysisService, modelService } from '@/services/api'
import { QueryPanel } from '@/components/workbench/QueryPanel'
import { ResultsPanel } from '@/components/workbench/ResultsPanel'
import { openAnalysisStream } from '@/lib/api'

export default function PlaygroundPage() {
  const [query, setQuery] = useState('')
  const [kbId, setKbId] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [traceEvents, setTraceEvents] = useState([])
  const [activeTab, setActiveTab] = useState('answer')
  const [errorMsg, setErrorMsg] = useState('')
  const [enableWebSearch, setEnableWebSearch] = useState(false)
  const [webSearchProvider, setWebSearchProvider] = useState('both')
  const [elapsedSec, setElapsedSec] = useState(0)

  const streamRef = useRef(null)
  const pollTimerRef = useRef(null)
  const finalizedRef = useRef(false)
  const userTouchedEmbeddingRef = useRef(false)

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

  const { data: knowledgeBases } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list
  })

  useEffect(() => {
    if (!kbId && knowledgeBases && knowledgeBases.length > 0) {
      setKbId(knowledgeBases[0].id)
    }
  }, [knowledgeBases, kbId])

  const { data: providersData, refetch: refetchProviders } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
    // Re-poll every 8s so a model installed while the page is open (e.g. after
    // running scripts/discover_local_models.py or pulling a new GGUF) shows up
    // in the dropdown without a page reload.
    refetchInterval: 8000,
  })

  const [selectedProvider, setSelectedProvider] = useState('llama_cpp')
  const [selectedModel, setSelectedModel] = useState('')
  // Auto-select the discovered default on first load so runs never go out
  // with an empty model (previously rendered as "DEFAULT" everywhere).
  // One-shot: once set — by the user or here — nothing overrides it.
  const activeProviderDefault = providersData?.providers?.[selectedProvider]?.default_model
  useEffect(() => {
    if (!selectedModel && activeProviderDefault) {
      setSelectedModel(activeProviderDefault)
    }
  }, [activeProviderDefault, selectedModel])

  const [selectedEmbeddingProvider, setSelectedEmbeddingProvider] = useState('huggingface')
  const [selectedEmbeddingModel, setSelectedEmbeddingModel] = useState('BAAI/bge-small-en-v1.5')

  // Publish the effective engine to the top telemetry bar (AppLayout reads the
  // same localStorage key + event) so the navbar pills always show what the
  // Playground will actually run — not just the server default.
  useEffect(() => {
    try {
      localStorage.setItem('trustrag.playground.engine', JSON.stringify({
        provider: selectedProvider,
        model: selectedModel,
        embeddingProvider: selectedEmbeddingProvider,
        embeddingModel: selectedEmbeddingModel,
        ts: Date.now(),
      }))
      window.dispatchEvent(new CustomEvent('trustrag:engine-change'))
    } catch {
      // private-mode storage denial must never break the workbench
    }
  }, [selectedProvider, selectedModel, selectedEmbeddingProvider, selectedEmbeddingModel])

  useEffect(() => {
    if (!userTouchedEmbeddingRef.current) {
      if (providersData?.active_embedding_provider) {
        setSelectedEmbeddingProvider(providersData.active_embedding_provider)
      }
      if (providersData?.active_embedding_model) {
        setSelectedEmbeddingModel(providersData.active_embedding_model)
      }
    }
  }, [providersData?.active_embedding_provider, providersData?.active_embedding_model])

const activeProviderInfo = providersData?.providers?.[selectedProvider]
  const availableModels = activeProviderInfo?.models?.length
    ? activeProviderInfo.models
    : []

  const activeEmbeddingProviderInfo = providersData?.embedding_providers?.[selectedEmbeddingProvider]
  const availableEmbeddingModels = activeEmbeddingProviderInfo?.models?.length
    ? activeEmbeddingProviderInfo.models
    : []

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
            await fetchFinalAnalysis(analysisId)
          }
        }
      } catch {
        // ignore background polling errors; progress continues via finished callbacks
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

      finalizedRef.current = false
      streamRef.current = await openAnalysisStream(analysisCreated.id, {
        onEvent: (eventData) => {
          setTraceEvents(prev => [...prev, eventData])
        },
        onError: async () => {
          if (!finalizedRef.current) {
            await fetchFinalAnalysis(analysisCreated.id)
          }
        },
        onComplete: async () => {
          if (!finalizedRef.current) {
            await fetchFinalAnalysis(analysisCreated.id)
          }
        }
      })

      startFallbackPolling(analysisCreated.id)
    } catch (err) {
      console.error("Failed to start analysis:", err)
      setLoading(false)
      // Backend error shape is { error: { code, message } } — surface the
      // actionable message (e.g. LLM_UNAVAILABLE start instructions), not a
      // generic axios status string.
      const detail = err.response?.data?.error?.message || err.response?.data?.detail || err.message || "Failed to start analysis"
      setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail))
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

          if (finalAnalysis.status === 'pending' || finalAnalysis.status === 'processing') {
            try {
              const traceList = await analysisService.trace(analysisId)
              if (traceList && traceList.length > 0) {
                setTraceEvents(traceList)
              }
            } catch {
              // trace endpoint may 404 while still processing; continue polling
            }
            await new Promise((r) => setTimeout(r, 1500))
            continue
          }

          // Single-round-trip finalize (1 ownership check server-side);
          // fall back to the legacy 4-call flow on older backends.
          let claims = []
          let evidence = []
          let trace = []
          try {
            const detail = await analysisService.detail(analysisId)
            claims = detail.claims || []
            evidence = detail.evidence || []
            trace = detail.trace || []
          } catch {
            const [claimsRes, evidenceRes, traceRes] = await Promise.allSettled([
              analysisService.claims(analysisId),
              analysisService.evidence(analysisId),
              analysisService.trace(analysisId),
            ])
            claims = claimsRes.status === 'fulfilled' ? claimsRes.value : []
            evidence = evidenceRes.status === 'fulfilled' ? evidenceRes.value : []
            trace = traceRes.status === 'fulfilled' ? traceRes.value : []
          }

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

      if (lastFetched) {
        setAnalysis(lastFetched)
        setActiveTab('answer')
      } else {
        setErrorMsg("Analysis execution timed out. Please check again in a few moments.")
      }
    } catch (err) {
      console.error("Failed to fetch final analysis data:", err)
      const detail = err.response?.data?.error?.message || err.response?.data?.detail || err.message || "Failed to fetch analysis"
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
          // stream already closed; nothing to clean up
        }
        streamRef.current = null
      }
    }
  }

  const currentTraceEvents = loading ? traceEvents : (analysis?.trace || traceEvents)
  // Recovery timeline shows strategy decisions only — wrapper lifecycle events
  // (recovery.started/completed/...) are excluded so one attempt renders as one
  // card instead of three identically-labeled ones.
  const RECOVERY_STRATEGY_LABELS = {
    [TraceEventType.RECOVERY_REWRITE]: 'Targeted Query Rewrite',
    [TraceEventType.RECOVERY_RE_RETRIEVE]: 'Expanded Context Retrieval',
    [TraceEventType.RECOVERY_REGENERATE]: 'Regeneration Retry (no new retrieval)',
    [TraceEventType.RECOVERY_RE_RETRIEVE_SKIPPED]: 'Kept Narrow Retrieval',
    [TraceEventType.RETRIEVAL_REUSED]: 'Reused Saved Evidence',
  }
  const recoveryRuns = currentTraceEvents
    .filter(e => e.event && Object.hasOwn(RECOVERY_STRATEGY_LABELS, e.event))
    .map(e => ({
      strategy: RECOVERY_STRATEGY_LABELS[e.event],
      reason: e.data?.message || 'Threshold checks failed, attempting adaptive healing',
      result: 'Context augmented, re-evaluating reliability',
      success: true,
    }))

  const selectedKb = knowledgeBases?.find(k => k.id === kbId)

  // KB embedding-space pin: a KB's vectors live in exactly one embedding space
  // (recorded at first ingest). The backend rejects analyses that request any
  // other model, so auto-snap the selector whenever the KB (or its pin) changes.
  const kbEmbeddingPin = selectedKb?.embedding_model || null
  const kbEmbeddingProviderPin = selectedKb?.embedding_provider || null
  useEffect(() => {
    if (kbEmbeddingPin) {
      if (kbEmbeddingProviderPin) setSelectedEmbeddingProvider(kbEmbeddingProviderPin)
      setSelectedEmbeddingModel(kbEmbeddingPin)
      userTouchedEmbeddingRef.current = false
    }
  }, [kbId, kbEmbeddingPin, kbEmbeddingProviderPin])
  const embeddingMismatch = !!kbEmbeddingPin && selectedEmbeddingModel !== kbEmbeddingPin
  const snapEmbeddingToKb = () => {
    if (kbEmbeddingProviderPin) setSelectedEmbeddingProvider(kbEmbeddingProviderPin)
    if (kbEmbeddingPin) setSelectedEmbeddingModel(kbEmbeddingPin)
    userTouchedEmbeddingRef.current = false
  }

  return (
    <AppLayout>
      <div className="flex flex-col md:flex-row h-full min-h-0 w-full overflow-hidden">
        <QueryPanel
          query={query}
          setQuery={setQuery}
          kbId={kbId}
          setKbId={setKbId}
          loading={loading}
          handleSubmit={handleSubmit}
          handleReset={handleReset}
          handlePresetSelect={handlePresetSelect}
          errorMsg={errorMsg}
          setErrorMsg={setErrorMsg}
          selectedProvider={selectedProvider}
          setSelectedProvider={setSelectedProvider}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          selectedEmbeddingProvider={selectedEmbeddingProvider}
          setSelectedEmbeddingProvider={setSelectedEmbeddingProvider}
          selectedEmbeddingModel={selectedEmbeddingModel}
          setSelectedEmbeddingModel={setSelectedEmbeddingModel}
          enableWebSearch={enableWebSearch}
          setEnableWebSearch={setEnableWebSearch}
          webSearchProvider={webSearchProvider}
          setWebSearchProvider={setWebSearchProvider}
          providersData={providersData}
          userTouchedEmbeddingRef={userTouchedEmbeddingRef}
          elapsedSec={elapsedSec}
          activeProviderInfo={activeProviderInfo}
          activeEmbeddingProviderInfo={activeEmbeddingProviderInfo}
          availableModels={availableModels}
          availableEmbeddingModels={availableEmbeddingModels}
          refetchProviders={refetchProviders}
          selectedKb={selectedKb}
          knowledgeBases={knowledgeBases}
          kbEmbeddingPin={kbEmbeddingPin}
          embeddingMismatch={embeddingMismatch}
          snapEmbeddingToKb={snapEmbeddingToKb}
        />

        <ResultsPanel
          analysis={analysis}
          loading={loading}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          currentTraceEvents={currentTraceEvents}
          recoveryRuns={recoveryRuns}
          query={query}
          enableWebSearch={enableWebSearch}
          webSearchProvider={webSearchProvider}
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          selectedEmbeddingModel={selectedEmbeddingModel}
        />
      </div>
    </AppLayout>
  )
}