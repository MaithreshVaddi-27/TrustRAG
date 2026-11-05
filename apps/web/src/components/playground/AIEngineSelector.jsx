import { Cpu, ServerOff, RotateCcw } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'

const PROVIDER_BUTTONS = [
  {
    key: 'ollama',
    label: 'Ollama',
    icon: ':11434',
    activeBtn: 'bg-primary-950/80 text-primary-200 border-primary-500/60 shadow-sm shadow-primary-950/50',
    activeBadge: 'text-primary-400 border-primary-700/60',
  },
  {
    key: 'llama_cpp',
    label: 'llama.cpp',
    icon: ':9931',
    activeBtn: 'bg-cyan-950/80 text-cyan-200 border-cyan-500/60 shadow-sm shadow-cyan-950/50',
    activeBadge: 'text-cyan-400 border-cyan-700/60',
  },
  {
    key: 'mlx',
    label: 'MLX',
    icon: ':8080',
    activeBtn: 'bg-primary-950/80 text-primary-200 border-primary-500/60 shadow-sm shadow-primary-950/50',
    activeBadge: 'text-primary-400 border-primary-700/60',
  },
  {
    key: 'gemini',
    label: 'Gemini',
    icon: 'Cloud',
    activeBtn: 'bg-primary-950/80 text-primary-200 border-primary-500/60 shadow-sm shadow-primary-950/50',
    activeBadge: 'text-primary-400 border-primary-700/60',
  },
]

const OFFLINE_MESSAGES = {
  ollama: (
    <>Run <code className="font-mono text-amber-100 bg-amber-900/60 px-1 py-0.5 rounded">ollama serve</code> in a terminal, then refresh.</>
  ),
  llama_cpp: (
    <>Run <code className="font-mono text-amber-100 bg-amber-900/60 px-1 py-0.5 rounded">./scripts/start_local_llm.sh</code> in a terminal, then refresh.</>
  ),
  mlx: (
    <>Run <code className="font-mono text-amber-100 bg-amber-900/60 px-1 py-0.5 rounded">mlx_lm.server</code> in a terminal (Apple Silicon), then refresh.</>
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
  const handleProviderChange = (providerKey) => {
    setSelectedProvider(providerKey)
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
          <Cpu className="w-3.5 h-3.5 text-primary-400" />
          <span>AI Engine</span>
        </div>
        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${
          activeProviderInfo?.connected
            ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
            : 'bg-amber-950/80 text-amber-400 border border-amber-800/40'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${activeProviderInfo?.connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          {activeProviderInfo?.connected ? 'Connected' : 'Standby'}
        </span>
      </div>

      <AnimatePresence>
      {(['ollama', 'llama_cpp', 'mlx'].includes(selectedProvider) && (providersUnresolved || (activeProviderInfo && !activeProviderInfo.connected))) && (
        <motion.div
          role="alert"
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={SPRING_SNAPPY}
          className="p-2.5 rounded-xl bg-amber-950/50 border border-amber-700/50 shadow-sm flex items-start justify-between gap-2"
        >
          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center gap-1.5 text-amber-300 text-[11px] font-semibold tracking-tight">
              <ServerOff size={13} className="shrink-0" />
              <span>Inference server offline</span>
            </div>
            <p className="text-[10px] leading-snug text-amber-200/80">
              {OFFLINE_MESSAGES[selectedProvider] || 'Start the inference server, then refresh.'}
            </p>
          </div>
          <button
            type="button"
            onClick={refetchProviders}
            disabled={loading}
            title="Recheck inference server"
            aria-label="Recheck inference server"
            className="shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium text-amber-200 bg-amber-900/60 border border-amber-700/50 hover:bg-amber-900/90 transition-colors cursor-pointer"
          >
            <RotateCcw size={10} />
            <span>Recheck</span>
          </button>
        </motion.div>
      )}
      </AnimatePresence>

      <div className="grid grid-cols-2 gap-1.5 bg-surface-900 p-1 rounded-lg border border-slate-800">
        {PROVIDER_BUTTONS.map(provider => {
          const isSelected = selectedProvider === provider.key
          return (
            <motion.button
              key={provider.key}
              type="button"
              onClick={() => handleProviderChange(provider.key)}
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.96, transition: SPRING_SNAPPY }}
              className={`text-xs py-1.5 px-2.5 rounded-md font-medium flex items-center justify-between border transition-all duration-150 ease-out ${
                isSelected
                  ? provider.activeBtn
                  : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-surface-800/60'
              }`}
            >
              <span>{provider.label}</span>
              <span className={`text-[10px] px-1 py-[2px] rounded bg-surface-950 font-mono border ${
                isSelected
                  ? provider.activeBadge
                  : 'border-slate-800 text-slate-500'
              }`}>
                {provider.icon}
              </span>
            </motion.button>
          )
        })}
      </div>

      <div className="space-y-1 pt-1 border-t border-slate-800">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <label htmlFor="ai-engine-model-select" className="font-medium cursor-pointer">Model:</label>
          <span className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-slate-500">
              {selectedProvider === 'ollama' ? ':11434' : selectedProvider === 'llama_cpp' ? ':9931' : selectedProvider === 'mlx' ? ':8080' : ''}
            </span>
            <button
              type="button"
              onClick={refetchProviders}
              disabled={loading}
              title="Refresh model list (after installing a new model)"
              className="p-1 rounded-md text-slate-500 hover:text-cyan-300 hover:bg-surface-800 border border-slate-800 transition-colors"
            >
              <RotateCcw size={11} />
            </button>
          </span>
        </div>
        <div className="relative">
          <select
            id="ai-engine-model-select"
            name="selectedModel"
            aria-label="Select AI Engine Model"
            value={selectedModel}
            onChange={e => setSelectedModel(e.target.value)}
            disabled={loading}
            className="w-full bg-surface-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary-500/50">
            {availableModels.length === 0 ? (
              <option value="">No models discovered — check server</option>
            ) : (
              availableModels.map(m => (
                <option key={m} value={m}>{m}</option>
              ))
            )}
          </select>
        </div>
      </div>
    </div>
  )
}