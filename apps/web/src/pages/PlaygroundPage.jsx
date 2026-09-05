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

  const { data: providersData } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
  })

  const [selectedProvider, setSelectedProvider] = useState('ollama')
  const [selectedModel, setSelectedModel] = useState('granite4.2:3b-q4_K_M')

  const [selectedEmbeddingProvider, setSelectedEmbeddingProvider] = useState('ollama')
  const [selectedEmbeddingModel, setSelectedEmbeddingModel] = useState('embeddinggemma:300m-qat-q8_0')

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
      const detail = err.response?.data?.detail || err.message || "Failed to start analysis"
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
          // stream already closed; nothing to clean up
        }
        streamRef.current = null
      }
    }
  }

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
          selectedKb={selectedKb}
          knowledgeBases={knowledgeBases}
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