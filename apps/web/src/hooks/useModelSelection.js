import { useState, useEffect, useCallback } from 'react'

const LOCAL_PROVIDERS = ['ollama', 'llama_cpp', 'mlx']

/**
 * useModelSelection — which engine the playground runs on.
 *
 * The default is the server's ACTIVE engine, not the first model a provider
 * happens to advertise. The two are not the same: a provider can list a
 * model it has downloaded that the platform registry does not enable, and
 * the server rejects the request with "Model is not enabled for provider".
 * Adopting the server's active pair means the default always works.
 *
 * The user can still override either half; an override is kept as long as
 * it is one the provider actually offers.
 */
export function useModelSelection(providersData) {
  const [selectedProvider, setSelectedProviderState] = useState(null)
  const [selectedModel, setSelectedModel] = useState('')

  const providers = providersData?.providers

  const modelsFor = useCallback(
    (providerKey) => {
      const models = providers?.[providerKey]?.models
      return models?.length ? [...new Set(models)] : []
    },
    [providers],
  )

  const activeProviderInfo = providers?.[selectedProvider]
  const availableModels = modelsFor(selectedProvider)

  // Adopt the server's active provider once it is known.
  useEffect(() => {
    const provider = providersData?.active_provider
    if (!provider) return
    setSelectedProviderState((previous) => previous ?? provider)
  }, [providersData?.active_provider])

  // Adopt the server's active model when it belongs to the selected
  // provider; otherwise fall back to the provider's own default, and then
  // to whatever the provider does offer.
  useEffect(() => {
    if (!selectedProvider) return

    const models = modelsFor(selectedProvider)
    const serverActive = providersData?.active_model

    setSelectedModel((previous) => {
      if (previous && models.includes(previous)) return previous
      if (
        selectedProvider === providersData?.active_provider &&
        serverActive &&
        models.includes(serverActive)
      ) {
        return serverActive
      }
      const advertised = providers?.[selectedProvider]?.default_model
      if (advertised && models.includes(advertised)) return advertised
      return models[0] || ''
    })
  }, [selectedProvider, modelsFor, providers, providersData?.active_model, providersData?.active_provider])

  // Publish the effective engine to the telemetry bar.
  useEffect(() => {
    if (!selectedProvider) return
    try {
      localStorage.setItem(
        'trustrag.playground.engine',
        JSON.stringify({
          provider: selectedProvider,
          model: selectedModel,
          ts: Date.now(),
        }),
      )
      window.dispatchEvent(new CustomEvent('trustrag:engine-change'))
    } catch {
      // private-mode storage denial must never break the workbench
    }
  }, [selectedProvider, selectedModel])

  // Detect unresolved providers (backend down).
  // The hook no longer decides this. "The registry has not arrived yet" and
  // "the registry could not be read" are different answers, and only the
  // caller — which can see whether the request actually failed — knows
  // which one it is. Guessing "unresolved" here put an offline alarm on
  // the screen before the first request had even returned.

  const handleProviderChange = useCallback(
    (providerKey) => {
      setSelectedProviderState(providerKey)
      const models = modelsFor(providerKey)
      const advertised = providers?.[providerKey]?.default_model
      setSelectedModel(models.includes(advertised) ? advertised : (models[0] || ''))
    },
    [modelsFor, providers],
  )

  return {
    selectedProvider,
    setSelectedProvider: handleProviderChange,
    selectedModel,
    setSelectedModel,
    activeProviderInfo,
    availableModels,
    isLocalProvider: LOCAL_PROVIDERS.includes(selectedProvider),
  }
}
