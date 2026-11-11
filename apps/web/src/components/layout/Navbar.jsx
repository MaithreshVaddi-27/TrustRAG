import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Zap, Menu, Cpu, Layers, RefreshCw } from 'lucide-react'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'
import { modelService } from '@/services/api'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'
import { useQuery } from '@tanstack/react-query'
import { AccountMenu } from './AccountMenu'

function readPlaygroundEngine() {
  try {
    const raw = localStorage.getItem('trustrag.playground.engine')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/**
 * Navbar — the application top bar.
 *
 * The header carries three things and nothing else: the brand, the state
 * of the engine, and the account. The telemetry is quiet mono text with a
 * status dot, and it sheds items as the bar narrows rather than
 * overflowing — the API state is the one that must survive, so it is the
 * last to go.
 */
export function Navbar({ isOnline, recheck, setIsMobileOpen }) {
  const navigate = useNavigate()
  const location = useLocation()
  const isPlayground = location.pathname === '/playground'

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
  const isEngineOverride = Boolean(
    playgroundEngine?.model && playgroundEngine.model !== serverModel,
  )
  const effEmbeddingModel =
    providersData?.active_embedding_model || 'BAAI/bge-small-en-v1.5'
  const accelerator = providersData?.hardware?.accelerator

  const acceleratorLabel =
    accelerator === 'mps'
      ? 'Metal (MPS)'
      : accelerator === 'cuda'
        ? 'CUDA GPU'
        : 'Multi-thread CPU'

  return (
    <header className="lx-topbar">
      <div className="lx-topbar__left">
        <button
          type="button"
          onClick={() => setIsMobileOpen(true)}
          className="lx-icon-btn md:hidden"
          title="Open navigation"
          aria-label="Open navigation"
        >
          <Menu size={18} strokeWidth={1.5} aria-hidden="true" />
        </button>

        <Link to="/dashboard" className="lx-topbar__brand" aria-label="TrustRAG home">
          <TrustRagEmblem size={28} framed />
          <span className="lx-topbar__wordmark">TRUSTRAG</span>
          <span className="lx-topbar__meta">Reliability workbench</span>
        </Link>
      </div>

      {/* Engine telemetry — quiet mono text with a status dot. The API state
          is always present; the rest steps down with the width. */}
      <div className="lx-telemetry">
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
              isOnline === false
                ? 'lx-dot--alarm'
                : isOnline === null
                  ? ''
                  : 'lx-dot--live',
            ]
              .filter(Boolean)
              .join(' ')}
            aria-hidden="true"
          />
          <strong>
            {isOnline === false
              ? 'API offline'
              : isOnline === null
                ? 'Checking'
                : 'API online'}
          </strong>
          {isOnline === false && (
            <button
              type="button"
              onClick={recheck}
              className="lx-telemetry__action"
              title="Reconnect to backend"
              aria-label="Reconnect to backend"
            >
              <RefreshCw size={11} strokeWidth={1.5} aria-hidden="true" />
            </button>
          )}
        </span>

        <span
          className="lx-telemetry__item lx-telemetry__item--engine"
          title={
            effModel
              ? `${providerShortLabel(effProvider)}: ${effModel} · ${
                  isEngineOverride ? 'Playground selection' : 'Server default'
                }`
              : 'Engine model not configured'
          }
        >
          <Cpu size={12} strokeWidth={1.5} aria-hidden="true" />
          <span className="lx-truncate">
            {providerShortLabel(effProvider)}: {shortModelId(effModel) || 'Local LLM'}
          </span>
          {isEngineOverride && <span className="lx-dot lx-dot--live" aria-hidden="true" />}
        </span>

        <span
          className="lx-telemetry__item lx-telemetry__item--embed"
          title={
            effEmbeddingModel
              ? `${effEmbeddingModel} · Server default (single engine)`
              : 'Embedding model not configured'
          }
        >
          <Layers size={12} strokeWidth={1.5} aria-hidden="true" />
          <span className="lx-truncate">
            {shortModelId(effEmbeddingModel) || 'bge-small-en-v1.5'}
          </span>
        </span>

        <span
          className="lx-telemetry__item lx-telemetry__item--accel"
          title={`${providersData?.hardware?.accelerator_name || 'Hardware'} · Memory: ${
            providersData?.hardware?.memory?.total_gb || 8
          }GB`}
        >
          <Zap size={12} strokeWidth={1.5} aria-hidden="true" />
          <span>{acceleratorLabel}</span>
        </span>
      </div>

      <div className="lx-topbar__right">
        {!isPlayground && (
          <button
            type="button"
            onClick={() => navigate('/playground')}
            className="lx-btn lx-btn--primary lx-topbar__run"
          >
            <Zap size={13} strokeWidth={1.5} aria-hidden="true" />
            <span className="lx-topbar__run-label">Run analysis</span>
          </button>
        )}

        <AccountMenu />
      </div>
    </header>
  )
}
