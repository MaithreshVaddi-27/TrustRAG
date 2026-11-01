import { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import { clsx } from 'clsx'
import { RefreshCw, Cpu, Layers, Zap } from 'lucide-react'
import { modelService } from '@/services/api'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'
import { useQuery } from '@tanstack/react-query'

function readPlaygroundEngine() {
  try {
    const raw = localStorage.getItem('trustrag.playground.engine')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/**
 * EngineTelemetry - Live engine telemetry badges for mobile/small screens
 * Called by: AppLayout.jsx
 * No existing file serves this purpose - extracted from AppLayout
 * Reads: localStorage 'trustrag.playground.engine', model providers from API
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function EngineTelemetry({ isOnline, isChecking, recheck }) {
  const [playgroundEngine, setPlaygroundEngine] = useState(readPlaygroundEngine)
  useEffect(() => {
    const sync = () => setPlaygroundEngine(readPlaygroundEngine())
    window.addEventListener('trustrag:engine-change', sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener('trustrag:engine-change', sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const { data: providersData } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
    staleTime: 30000,
  })

  const serverProvider = providersData?.active_provider
  const serverModel = providersData?.active_model
  const effProvider = playgroundEngine?.provider || serverProvider
  const effModel = playgroundEngine?.model || serverModel
  const isEngineOverride = !!playgroundEngine?.model && playgroundEngine.model !== serverModel
  const effEmbeddingModel = providersData?.active_embedding_model || 'BAAI/bge-small-en-v1.5'

  return (
    <div className="lg:hidden px-4 py-2 space-y-2">
      {/* Backend Status */}
      <motion.div
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className={clsx(
          'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono shadow-sm w-full',
          isOnline === false
            ? 'bg-red-950/40 border border-red-800/50 text-red-300 shadow-red-950/30'
            : isOnline === null
              ? 'bg-slate-800/60 border border-slate-700/60 text-slate-400'
              : 'bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 shadow-emerald-950/30'
        )}
        title={isOnline === false ? 'Backend unreachable — start the API server' : isOnline === null ? 'Checking backend…' : 'Backend is healthy'}
      >
        <motion.span
          animate={isOnline === false ? { opacity: [1, 0.4, 1] } : isChecking ? { opacity: [1, 0.3, 1] } : { scale: [1, 1.2, 1] }}
          transition={isOnline === false ? { duration: 2, repeat: Infinity } : isChecking ? { duration: 1, repeat: Infinity } : { duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          className={clsx(
            'w-2 h-2 rounded-full',
            isOnline === false ? 'bg-red-400' : isOnline === null ? 'bg-slate-500' : 'bg-emerald-400'
          )}
        />
        <span className="flex-1 text-left">{isOnline === false ? 'API Offline' : isOnline === null ? 'Checking…' : 'API Online'}</span>
        {isOnline === false && (
          <motion.button
            onClick={recheck}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            className="text-red-400/80 hover:text-red-300 transition-colors"
            title="Reconnect to backend"
          >
            <RefreshCw size={10} />
          </motion.button>
        )}
      </motion.div>

      {/* Model pills - stacked on mobile */}
      <div className="space-y-1.5">
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-800/60 border border-slate-700/60 text-[11px] font-mono text-slate-300"
          title={effModel
            ? `${providerShortLabel(effProvider)}: ${effModel} · ${isEngineOverride ? 'Playground selection' : 'Server default'}`
            : 'Engine model not configured'}
        >
          <Cpu size={12} className="text-primary-400 shrink-0" />
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${isEngineOverride ? 'bg-cyan-400' : 'bg-slate-500'}`}
            title={isEngineOverride ? 'Playground selection' : 'Server default'}
          />
          <span className="max-w-[180px] truncate tracking-tight">
            {providerShortLabel(effProvider)}: {shortModelId(effModel) || 'Local LLM'}
          </span>
        </div>

        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-800/60 border border-slate-700/60 text-[11px] font-mono text-slate-300"
          title={effEmbeddingModel
            ? `${effEmbeddingModel} · Server default (single engine)`
            : 'Embedding model not configured'}
        >
          <Layers size={12} className="text-cyan-400 shrink-0" />
          <span
            className="w-1.5 h-1.5 rounded-full shrink-0 bg-slate-500"
            title="Server default"
          />
          <span className="max-w-[180px] truncate tracking-tight">
            {shortModelId(effEmbeddingModel) || 'bge-small-en-v1.5'}
          </span>
        </div>

        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-800/60 border border-slate-700/60 text-[11px] font-mono text-slate-300"
          title={`${providersData?.hardware?.accelerator_name || 'Hardware'} • Memory: ${providersData?.hardware?.memory?.total_gb || 8}GB`}
        >
          <Zap size={12} className={providersData?.hardware?.accelerator === 'mps' ? 'text-amber-400' : (providersData?.hardware?.accelerator === 'cuda' ? 'text-emerald-400' : 'text-slate-400')} />
          <span>
            {providersData?.hardware?.accelerator === 'mps' ? 'Metal (MPS)' : (providersData?.hardware?.accelerator === 'cuda' ? 'CUDA GPU' : 'Multi-Thread CPU')}
          </span>
        </div>
      </div>
    </div>
  )
}