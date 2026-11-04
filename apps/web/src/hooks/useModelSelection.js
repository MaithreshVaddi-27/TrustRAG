import { useState, useEffect, useCallback } from 'react'

const LOCAL_PROVIDERS = ['ollama', 'llama_cpp', 'mlx']

const PROVIDER_DEFAULTS = {
  ollama: 'granite4.2:3b-q4_K_M',
  llama_cpp: 'occ-ai/OCC-RAG-1.7B-GGUF:Q4_K_M',
  mlx: 'mlx-community/Llama-3.2-1B-Instruct-4bit',
  gemini: 'gemini-3.5-flash-lite',
}

export function useModelSelection(providersData) {
  const [selectedProvider, setSelectedProvider] = useState('llama_cpp')
  const [selectedModel, setSelectedModel] = useState('LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M')
  const [providersUnresolved, setProvidersUnresolved] = useState(false)
  const [refetchTrigger, setRefetchTrigger] = useState(0)

  const activeProviderInfo = providersData?.providers?.[selectedProvider]
  const availableModels = activeProviderInfo?.models?.length
    ? [...new Set(activeProviderInfo.models)]
    : []

  // Publish effective engine to telemetry bar
  useEffect(() => {
    try {
      localStorage.setItem('trustrag.playground.engine', JSON.stringify({
        provider: selectedProvider,
        model: selectedModel,
        ts: Date.now(),
      }))
      window.dispatchEvent(new CustomEvent('trustrag:engine-change'))
    } catch {
      // private-mode storage denial must never break the workbench
    }
  }, [selectedProvider, selectedModel])

  // Auto-select default model when provider changes
  const activeProviderDefault = providersData?.providers?.[selectedProvider]?.default_model
  useEffect(() => {
    if (!selectedModel && activeProviderDefault) {
      setSelectedModel(activeProviderDefault)
    }
  }, [activeProviderDefault, selectedModel])

  // Detect unresolved providers (backend down)
  useEffect(() => {
    const data = providersData
    setProvidersUnresolved(!data && !data?.providers)
  }, [providersData])

  const handleProviderChange = useCallback((providerKey) => {
    setSelectedProvider(providerKey)
    const prov = providersData?.providers?.[providerKey]
    if (prov?.default_model) {
      setSelectedModel(prov.default_model)
    } else if (PROVIDER_DEFAULTS[providerKey]) {
      setSelectedModel(PROVIDER_DEFAULTS[providerKey])
    }
  }, [providersData])

  const refetchProviders = useCallback(() => {
    setRefetchTrigger(t => t + 1)
  }, [])

  return {
    selectedProvider,
    setSelectedProvider: handleProviderChange,
    selectedModel,
    setSelectedModel,
    activeProviderInfo,
    availableModels,
    providersUnresolved,
    refetchProviders,
    refetchTrigger,
    isLocalProvider: LOCAL_PROVIDERS.includes(selectedProvider),
  }
}