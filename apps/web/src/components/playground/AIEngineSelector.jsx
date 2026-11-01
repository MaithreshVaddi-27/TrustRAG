import { Cpu, Zap, ServerOff, RotateCcw } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'

const PROVIDER_BUTTONS = [
  { key: 'ollama', label: 'Ollama', icon: ':11434', color: 'primary' },
  { key: 'llama_cpp', label: 'llama.cpp', icon: ':8080', color: 'cyan' },
  { key: 'mlx', label: 'MLX', icon: 'Mac', color: 'orange' },
  { key: 'gemini', label: 'Gemini', icon: 'Cloud', color: 'indigo' },
]

const OFFLINE_MESSAGES = {
  ollama: 'Run <code className="font-mono text-amber-100">ollama serve</code> in a terminal, then refresh.',
  llama_cpp: 'Run <code className="font-mono text-amber-100">./scripts/start_local_llm.sh</code> in a terminal, then refresh.',
  mlx: 'Run <code className="font-mono text-amber-100">mlx_lm.server --model mlx-community/Llama-3.2-1B-Instruct-4bit</code> in a terminal (Apple Silicon), then refresh.',
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

      <AnimatePresence>
      {(['ollama', 'llama_cpp', 'mlx'].includes(selectedProvider) && (providersUnresolved || (activeProviderInfo && !activeProviderInfo.connected))) && (
        <motion.div
          role="alert"
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={SPRING_SNAPPY}
          className="p-2.5 rounded-xl bg-amber-950/60 border border-amber-700/50 shadow-sm"
        >
          <div className="flex items-center gap-1.5 text-amber-300 text-[11px] font-semibold tracking-tight">
            <ServerOff size={13} className="shrink-0" />
            <span>Inference server offline</span>
          </div>
          <p className="mt-1 text-[10px] leading-relaxed text-amber-200/80">
            {OFFLINE_MESSAGES[selectedProvider] || 'Start the inference server, then refresh.'}
          </p>
          <button
            type="button"
            onClick={refetchProviders}
            disabled={loading}
            className="mt-1.5 inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium text-amber-200 bg-amber-900/50 border border-amber-700/50 hover:bg-amber-900/80 transition-colors"
          >
            <RotateCcw size={10} />
            Recheck server
          </button>
        </motion.div>
      )}
      </AnimatePresence>

      <div className="grid grid-cols-2 gap-1.5 bg-surface-900 p-1 rounded-lg border border-slate-800">
        {PROVIDER_BUTTONS.map(provider => (
          <motion.button
            key={provider.key}
            type="button"
            onClick={() => handleProviderChange(provider.key)}
            disabled={loading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.96, transition: SPRING_SNAPPY }}
            className={`text-xs py-1.5 px-2 rounded-md font-medium flex items-center justify-between transition-all duration-150 ease-out ${
              selectedProvider === provider.key
                ? `bg-${provider.color}-600/30 text-${provider.color}-200 border border-${provider.color}-500/50 shadow-sm`
                : 'text-slate-400 hover:text-slate-200 border border-transparent'
            }`}>
            <span>{provider.label}</span>
            <span className={`text-[10px] px-1 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-${provider.color}-400 font-mono`}>
              {provider.icon}
            </span>
          </motion.button>
        ))}
      </div>

      <div className="space-y-1 pt-1 border-t border-slate-800">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="font-medium">Model:</span>
          <span className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-slate-500">
              {selectedProvider === 'ollama' ? ':11434' : ((selectedProvider === 'llama_cpp' || selectedProvider === 'mlx') ? ':8080' : '')}
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