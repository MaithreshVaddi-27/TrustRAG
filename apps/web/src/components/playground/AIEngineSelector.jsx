import { Cpu, ServerOff, RotateCcw, Cloud } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { useReducedMotion } from 'motion/react'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

const PROVIDER_BUTTONS = [
  {
    key: 'ollama',
    label: 'Ollama',
    icon: ':11434',
    accent: 'primary',
    accentClass: 'bg-primary-950/80 text-primary-200 border-primary-500/60 shadow-sm shadow-primary-950/50',
    badgeClass: 'text-primary-400 border-primary-700/60',
    iconComponent: null,
  },
  {
    key: 'llama_cpp',
    label: 'llama.cpp',
    icon: ':9931',
    accent: 'cyan',
    accentClass: 'bg-cyan-950/80 text-cyan-200 border-cyan-500/60 shadow-sm shadow-cyan-950/50',
    badgeClass: 'text-cyan-400 border-cyan-700/60',
    iconComponent: null,
  },
  {
    key: 'mlx',
    label: 'MLX',
    icon: ':8080',
    accent: 'primary',
    accentClass: 'bg-primary-950/80 text-primary-200 border-primary-500/60 shadow-sm shadow-primary-950/50',
    badgeClass: 'text-primary-400 border-primary-700/60',
    iconComponent: null,
  },
  {
    key: 'gemini',
    label: 'Gemini',
    icon: Cloud,
    accent: 'primary',
    accentClass: 'bg-primary-950/80 text-primary-200 border-primary-500/60 shadow-sm shadow-primary-950/50',
    badgeClass: 'text-primary-400 border-primary-700/60',
    iconComponent: Cloud,
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
  const reduced = useReducedMotion()

  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  const handleProviderChange = (providerKey) => {
    setSelectedProvider(providerKey)
  }

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
          <Cpu className="w-3.5 h-3.5 text-primary-400" aria-hidden="true" />
          <span>AI Engine</span>
        </div>
        <motion.span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${
            activeProviderInfo?.connected
              ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
              : 'bg-amber-950/80 text-amber-400 border border-amber-800/40'
          }`}
          initial={reduced ? { opacity: 1 } : { opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={springTransition}
        >
          <motion.span
            className={`w-1.5 h-1.5 rounded-full ${activeProviderInfo?.connected ? 'bg-emerald-400' : 'bg-amber-400'}`}
            animate={activeProviderInfo?.connected && !reduced ? { scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] } : false}
            transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
            aria-hidden="true"
          />
          {activeProviderInfo?.connected ? 'Connected' : 'Standby'}
        </motion.span>
      </div>

      <AnimatePresence>
        {(['ollama', 'llama_cpp', 'mlx'].includes(selectedProvider) && (providersUnresolved || (activeProviderInfo && !activeProviderInfo.connected))) && (
          <motion.div
            role="alert"
            initial={reduced ? { opacity: 1, height: 'auto' } : { opacity: 0, height: 0, y: -6 }}
            animate={{ opacity: 1, height: 'auto', y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0, y: -6 }}
            transition={reduced ? { duration: 0.01 } : { duration: 0.25, ease: 'easeOut' }}
            className="p-2.5 rounded-xl bg-amber-950/50 border border-amber-700/50 shadow-sm flex items-start justify-between gap-2"
          >
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center gap-1.5 text-amber-300 text-[11px] font-semibold tracking-tight">
                <ServerOff size={13} className="shrink-0" aria-hidden="true" />
                <span>Inference server offline</span>
              </div>
              <p className="text-[10px] leading-snug text-amber-200/80">
                {OFFLINE_MESSAGES[selectedProvider] || 'Start the inference server, then refresh.'}
              </p>
            </div>
            <motion.button
              type="button"
              onClick={refetchProviders}
              disabled={loading}
              title="Recheck inference server"
              aria-label="Recheck inference server"
              whileHover={{ scale: 1.05, transition: springTransition }}
              whileTap={{ scale: 0.95, transition: pressTransition }}
              className="shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium text-amber-200 bg-amber-900/60 border border-amber-700/50 hover:bg-amber-900/90 transition-colors cursor-pointer"
            >
              <RotateCcw size={10} aria-hidden="true" />
              <span>Recheck</span>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-2 gap-1.5 bg-surface-900 p-1 rounded-lg border border-slate-800">
        {PROVIDER_BUTTONS.map((provider, idx) => {
          const isSelected = selectedProvider === provider.key

          return (
            <motion.button
              key={provider.key}
              type="button"
              onClick={() => handleProviderChange(provider.key)}
              disabled={loading}
              whileHover={{ scale: 1.02, transition: springTransition }}
              whileTap={{ scale: 0.96, transition: pressTransition }}
              className={`text-xs py-1.5 px-2.5 rounded-md font-medium flex items-center justify-between border transition-all duration-150 ease-out relative overflow-hidden ${
                isSelected
                  ? provider.accentClass
                  : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-surface-800/60'
              }`}
              style={{ minHeight: '44px', minWidth: '44px' }}
              initial={reduced ? { opacity: 1 } : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...springTransition, delay: idx * 0.04 }}
            >
              <span className="relative z-10">{provider.label}</span>
              <span className={`relative z-10 text-[10px] px-1 py-[2px] rounded bg-surface-950 font-mono border ${
                isSelected
                  ? provider.badgeClass
                  : 'border-slate-800 text-slate-500'
              }`}>
                {provider.iconComponent ? (
                  <provider.iconComponent size={10} aria-hidden="true" />
                ) : (
                  provider.icon
                )}
              </span>
              {isSelected && (
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
                  initial={reduced ? { opacity: 1 } : { opacity: 0, scaleX: 0 }}
                  animate={{ opacity: 1, scaleX: 1 }}
                  transition={reduced ? { duration: 0.01 } : { delay: 0.1, type: 'spring', damping: 30, stiffness: 300 }}
                  style={{ transformOrigin: 'left center' }}
                  aria-hidden="true"
                />
              )}
            </motion.button>
          )
        })}
      </div>

      <motion.div
        initial={reduced ? { opacity: 1 } : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springTransition, delay: 0.1 }}
        className="space-y-1 pt-1 border-t border-slate-800"
      >
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <label htmlFor="ai-engine-model-select" className="font-medium cursor-pointer">
            Model
          </label>
          <motion.button
            type="button"
            onClick={refetchProviders}
            disabled={loading}
            title="Refresh model list (after installing a new model)"
            whileHover={{ scale: 1.05, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: pressTransition }}
            className="p-1 rounded-md text-slate-500 hover:text-cyan-300 hover:bg-surface-800 border border-slate-800 transition-colors"
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            <RotateCcw size={11} aria-hidden="true" />
          </motion.button>
        </div>
        <div className="relative">
          <select
            id="ai-engine-model-select"
            name="selectedModel"
            aria-label="Select AI Engine Model"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={loading}
            className="w-full bg-surface-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary-500/50 appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ minHeight: '44px' }}
          >
            {availableModels.length === 0 ? (
              <option value="">No models discovered — check server</option>
            ) : (
              availableModels.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))
            )}
          </select>
        </div>
      </motion.div>
    </motion.div>
  )
}