import { Cpu, ServerOff, RotateCcw, Cloud } from 'lucide-react'

/**
 * AIEngineSelector — which model runs the reasoning.
 *
 * A segmented control for the provider, a select for the model. The
 * selected provider carries crimson on its lower edge, which is the one
 * place crimson means "this is the active choice".
 */
const PROVIDERS = [
  { key: 'ollama', label: 'Ollama', port: ':11434' },
  { key: 'llama_cpp', label: 'llama.cpp', port: ':9931' },
  { key: 'mlx', label: 'MLX', port: ':8080' },
  { key: 'gemini', label: 'Gemini', port: 'cloud' },
]

const OFFLINE_MESSAGES = {
  ollama: (
    <>
      Run <code>ollama serve</code> in a terminal, then recheck.
    </>
  ),
  llama_cpp: (
    <>
      Run <code>./scripts/start_local_llm.sh</code> in a terminal, then recheck.
    </>
  ),
  mlx: (
    <>
      Run <code>mlx_lm.server</code> in a terminal on Apple Silicon, then recheck.
    </>
  ),
}

export function AIEngineSelector({
  selectedProvider,
  setSelectedProvider,
  activeProviderInfo,
  availableModels,
  selectedModel,
  setSelectedModel,
  loading,
  providersUnresolved,
  refetchProviders,
}) {
  // The engine is offline when the provider registry could not be read at
  // all, or when the selected local provider is not answering.
  const isOffline =
    providersUnresolved ||
    (['ollama', 'llama_cpp', 'mlx'].includes(selectedProvider) &&
      Boolean(activeProviderInfo) &&
      !activeProviderInfo.connected)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <span className="lx-workbench__label !mb-0 flex items-center gap-2">
          <Cpu size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
          AI engine
        </span>
        <span className="lx-chip">
          {activeProviderInfo?.connected ? 'Connected' : 'Standby'}
        </span>
      </div>

      {isOffline && (
        <div className="lx-message lx-message--alarm" role="alert">
          <ServerOff size={14} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <span className="lx-message__title">Inference server offline</span>
            <span className="lx-message__body">
              {selectedProvider
                ? OFFLINE_MESSAGES[selectedProvider] ||
                  'Start the inference server, then recheck.'
                : 'The provider registry could not be read. Check that the API server is running, then recheck.'}
            </span>
          </div>
          <button
            type="button"
            onClick={refetchProviders}
            disabled={loading}
            className="lx-btn lx-btn--secondary shrink-0"
          >
            <RotateCcw size={12} strokeWidth={1.75} aria-hidden="true" />
            <span>Recheck</span>
          </button>
        </div>
      )}

      <div className="lx-tabs" role="group" aria-label="Inference provider">
        {PROVIDERS.map((provider) => {
          const selected = selectedProvider === provider.key
          const Icon = provider.key === 'gemini' ? Cloud : null
          return (
            <button
              key={provider.key}
              type="button"
              onClick={() => setSelectedProvider(provider.key)}
              disabled={loading}
              aria-pressed={selected}
              className="lx-tab"
            >
              {Icon && <Icon size={12} strokeWidth={1.5} aria-hidden="true" />}
              {provider.label}
              <span className="ml-1 font-mono text-[0.625rem] text-silver-500">{provider.port}</span>
            </button>
          )
        })}
      </div>

      <div className="flex items-center justify-between gap-2">
        <label className="lx-workbench__label !mb-0" htmlFor="ai-engine-model-select">
          Model
        </label>
        <button
          type="button"
          onClick={refetchProviders}
          disabled={loading}
          className="lx-icon-btn h-7 w-7"
          title="Refresh the model list"
          aria-label="Refresh the model list"
        >
          <RotateCcw size={12} strokeWidth={1.75} aria-hidden="true" />
        </button>
      </div>

      <select
        id="ai-engine-model-select"
        name="selectedModel"
        aria-label="Select the AI engine model"
        value={selectedModel}
        onChange={(event) => setSelectedModel(event.target.value)}
        disabled={loading || !selectedProvider}
        className="lx-control font-mono text-[0.8125rem]"
      >
        {availableModels.length === 0 ? (
          <option value="">
            {selectedProvider
              ? 'No models discovered — check the server'
              : 'Detecting the active engine…'}
          </option>
        ) : (
          availableModels.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))
        )}
      </select>
    </div>
  )
}
