import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import AppLayout from '@/layouts/AppLayout'
import { TraceEventType } from '@/components/workbench/traceEvents'
import { modelService } from '@/services/api'
import { QueryPanel } from '@/components/playground/QueryPanel'
import { ResultsPanel } from '@/components/results/ResultsPanel'
import { useAnalysisStream } from '@/hooks/useAnalysisStream'
import { useModelSelection } from '@/hooks/useModelSelection'
import { useKnowledgeBaseSelection } from '@/hooks/useKnowledgeBaseSelection'

const RECOVERY_STRATEGY_LABELS = {
  [TraceEventType.RECOVERY_REWRITE]: 'Targeted Query Rewrite',
  [TraceEventType.RECOVERY_RE_RETRIEVE]: 'Expanded Context Retrieval',
  [TraceEventType.RECOVERY_REGENERATE]: 'Regeneration Retry (no new retrieval)',
  [TraceEventType.RECOVERY_RE_RETRIEVE_SKIPPED]: 'Kept Narrow Retrieval',
  [TraceEventType.RETRIEVAL_REUSED]: 'Reused Saved Evidence',
}

const webSearchProvider = 'tavily'

export default function PlaygroundPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [traceEvents, setTraceEvents] = useState([])
  const [activeTab, setActiveTab] = useState('answer')
  const [errorMsg, setErrorMsg] = useState('')
  const [enableWebSearch, setEnableWebSearch] = useState(false)
  const [elapsedSec, setElapsedSec] = useState(0)

  const finalizedRef = useRef(false)

  const { data: providersData, refetch: refetchProviders, isLoading: providersLoading, isError: providersError } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
    refetchInterval: 8000,
  })

  const providersUnresolved = !providersLoading && providersError && !providersData

  const {
    selectedProvider,
    setSelectedProvider,
    selectedModel,
    setSelectedModel,
    activeProviderInfo,
    availableModels,
    providersUnresolved: modelProvidersUnresolved,
  } = useModelSelection(providersData)

  const selectedEmbeddingModel = providersData?.active_embedding_model || 'BAAI/bge-small-en-v1.5'

  const {
    kbId,
    setKbId,
    knowledgeBases,
    selectedKb,
  } = useKnowledgeBaseSelection()

  const {
    startAnalysis,
    cleanup,
  } = useAnalysisStream()

  // Timer for elapsed seconds display
  useEffect(() => {
    if (!loading) return
    setElapsedSec(0)
    const timer = setInterval(() => {
      setElapsedSec(prev => +(prev + 0.1).toFixed(1))
    }, 100)
    return () => clearInterval(timer)
  }, [loading])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [cleanup])

  const handleReset = useCallback(() => {
    setQuery('')
    setAnalysis(null)
    setTraceEvents([])
    setErrorMsg('')
    setActiveTab('answer')
  }, [])

  const handlePresetSelect = useCallback((presetText) => {
    setQuery(presetText)
  }, [])

  const handleSubmit = useCallback(async (e) => {
    if (e && e.preventDefault) e.preventDefault()
    if (!query.trim() || !kbId || loading) return

    setLoading(true)
    setAnalysis(null)
    setTraceEvents([])
    setErrorMsg('')
    setActiveTab('answer')
    finalizedRef.current = false

    try {
      await startAnalysis(
        {
          kbId,
          query: query.trim(),
          enableWebSearch,
          webSearchProvider,
          llmProvider: selectedProvider,
          llmModel: selectedModel,
        },
        {
          onEvent: (eventData) => {
            setTraceEvents(prev => [...prev, eventData])
          },
          onComplete: (fullAnalysis) => {
            if (!finalizedRef.current) {
              finalizedRef.current = true
              setAnalysis(fullAnalysis)
              setActiveTab('answer')
              setLoading(false)
            }
          },
          onError: (err) => {
            if (!finalizedRef.current) {
              finalizedRef.current = true
              setLoading(false)
              const detail = err.message
              setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail))
            }
          },
        }
      )
    } catch (err) {
      console.error('Failed to start analysis:', err)
      setLoading(false)
      const detail = err.response?.data?.error?.message || err.response?.data?.detail || err.message || 'Failed to start analysis'
      setErrorMsg(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
  }, [query, kbId, loading, enableWebSearch, selectedProvider, selectedModel, startAnalysis])

  // KB embedding-space pin check
  const kbEmbeddingPin = selectedKb?.embedding_model || null
  const embeddingMismatch = !!kbEmbeddingPin && selectedEmbeddingModel !== kbEmbeddingPin

  const currentTraceEvents = loading ? traceEvents : (analysis?.trace || traceEvents)

  const recoveryRuns = currentTraceEvents
    .filter(e => e.event && Object.hasOwn(RECOVERY_STRATEGY_LABELS, e.event))
    .map(e => ({
      strategy: RECOVERY_STRATEGY_LABELS[e.event],
      reason: e.data?.message || 'Threshold checks failed, attempting adaptive healing',
      result: 'Context augmented, re-evaluating reliability',
      success: true,
    }))

  return (
    <AppLayout>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200, delay: 0.1 }}
        className="flex flex-col md:flex-row h-full min-h-0 w-full overflow-hidden"
      >
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
          selectedEmbeddingModel={selectedEmbeddingModel}
          enableWebSearch={enableWebSearch}
          setEnableWebSearch={setEnableWebSearch}
          providersData={providersData}
          elapsedSec={elapsedSec}
          activeProviderInfo={activeProviderInfo}
          availableModels={availableModels}
          refetchProviders={refetchProviders}
          providersUnresolved={providersUnresolved || modelProvidersUnresolved}
          selectedKb={selectedKb}
          knowledgeBases={knowledgeBases}
          kbEmbeddingPin={kbEmbeddingPin}
          embeddingMismatch={embeddingMismatch}
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
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          selectedEmbeddingModel={selectedEmbeddingModel}
          analysisStatus={analysis?.status}
        />
      </motion.div>
    </AppLayout>
  )
}