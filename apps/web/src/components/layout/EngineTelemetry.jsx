import { useState, useEffect } from 'react'
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
 * EngineTelemetry — the engine readout for narrow screens.
 *
 * The same quiet mono text the desktop bar uses, stacked. A status dot
 * rather than a coloured pill.
 *
 * The desktop bar sheds its optional items as it narrows — engine,
 * embedding model, accelerator — and the API state is the only thing it
 * keeps. On a phone there is no room for that, so the whole readout moves
 * into the drawer, where it is one tap away instead of gone.
 */
export function EngineTelemetry({ isOnline, recheck }) {
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

  const effProvider = playgroundEngine?.provider || providersData?.active_provider
  const effModel = playgroundEngine?.model || providersData?.active_model
  const isEngineOverride = !!playgroundEngine?.model && playgroundEngine.model !== providersData?.active_model
  const effEmbeddingModel = providersData?.active_embedding_model || null
  const accelerator = providersData?.hardware?.accelerator

  return (
    <div className="flex flex-col gap-2 border-t border-[color:var(--rule)] pt-3">
      <span
        className="lx-telemetry__item"
        title={
          isOnline === false
            ? 'Backend unreachable — start the API server'
            : isOnline === null
              ? 'Checking backend…'
              : 'Backend is healthy'
        }
      >
        <span
          className={[
            'lx-dot',
            isOnline === false ? 'lx-dot--alarm' : isOnline === null ? '' : 'lx-dot--live',
          ]
            .filter(Boolean)
            .join(' ')}
          aria-hidden="true"
        />
        <strong>
          {isOnline === false ? 'API offline' : isOnline === null ? 'Checking' : 'API online'}
        </strong>
        {isOnline === false && (
          <button
            type="button"
            onClick={recheck}
            className="ml-1 text-crimson-400 hover:text-crimson-300 transition-colors"
            title="Reconnect to backend"
            aria-label="Reconnect to backend"
          >
            <RefreshCw size={11} strokeWidth={1.5} aria-hidden="true" />
          </button>
        )}
      </span>

      <span
        className="lx-telemetry__item"
        title={
          effModel
            ? `${providerShortLabel(effProvider)}: ${effModel} · ${
                isEngineOverride ? 'Playground selection' : 'Server default'
              }`
            : 'Engine model not configured'
        }
      >
        <Cpu size={12} strokeWidth={1.5} aria-hidden="true" />
        <span className="max-w-[220px] truncate">
          {providerShortLabel(effProvider)}: {shortModelId(effModel) || 'Local LLM'}
        </span>
        {isEngineOverride && <span className="lx-dot lx-dot--live" aria-hidden="true" />}
      </span>

      <span
        className="lx-telemetry__item"
        title={
          effEmbeddingModel
            ? `${effEmbeddingModel} · Server default (single engine)`
            : 'Embedding model not configured'
        }
      >
        <Layers size={12} strokeWidth={1.5} aria-hidden="true" />
        <span className="max-w-[220px] truncate">
          {shortModelId(effEmbeddingModel) || 'Embedding model'}
        </span>
      </span>

      <span
        className="lx-telemetry__item"
        title={`${providersData?.hardware?.accelerator_name || 'Hardware'} · Memory: ${
          providersData?.hardware?.memory?.total_gb || 8
        }GB`}
      >
        <Zap size={12} strokeWidth={1.5} aria-hidden="true" />
        <span>
          {accelerator === 'mps'
            ? 'Metal (MPS)'
            : accelerator === 'cuda'
              ? 'CUDA GPU'
              : 'Multi-thread CPU'}
        </span>
      </span>
    </div>
  )
}
