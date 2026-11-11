import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  LogOut, Zap, Menu,
  Cpu, Layers, RefreshCw, PanelLeft, PanelLeftOpen
} from 'lucide-react'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/auth'
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
 * Navbar — the application top bar.
 *
 * A brand, quiet engine telemetry, one primary action and the account
 * control. The telemetry is mono text with a status dot, not a row of
 * coloured pills.
 */
export function Navbar({
  isOnline,
  recheck,
  setIsMobileOpen,
  isCollapsed,
  toggleSidebar,
}) {
  const navigate = useNavigate()
  const location = useLocation()
  const isPlayground = location.pathname === '/playground'
  const { user } = useAuthStore()

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
  const accelerator = providersData?.hardware?.accelerator

  async function handleLogout() {
    await authService.logout()
    navigate('/login')
  }

  return (
    <header className="lx-topbar">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setIsMobileOpen(true)}
          className="lx-icon-btn md:hidden"
          title="Open navigation"
          aria-label="Open navigation"
        >
          <Menu size={18} strokeWidth={1.5} aria-hidden="true" />
        </button>

        <Link to="/dashboard" className="lx-topbar__brand">
          <TrustRagEmblem size={28} framed />
          <span className="flex flex-col">
            <span className="lx-topbar__wordmark">TRUSTRAG</span>
            <span className="lx-topbar__meta hidden sm:block">Reliability workbench</span>
          </span>
        </Link>

        {toggleSidebar && (
          <button
            type="button"
            onClick={toggleSidebar}
            className="lx-icon-btn hidden md:inline-flex ml-1"
            title={isCollapsed ? 'Expand sidebar (⌘B)' : 'Collapse sidebar (⌘B)'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <PanelLeftOpen size={16} strokeWidth={1.5} aria-hidden="true" />
            ) : (
              <PanelLeft size={16} strokeWidth={1.5} aria-hidden="true" />
            )}
          </button>
        )}
      </div>

      {/* Engine telemetry — quiet mono text with a status dot. */}
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
          <span className="max-w-[210px] truncate">
            {shortModelId(effEmbeddingModel) || 'bge-small-en-v1.5'}
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

      <div className="flex items-center gap-3">
        {!isPlayground && (
          <button
            type="button"
            onClick={() => navigate('/playground')}
            className="lx-btn lx-btn--primary hidden sm:inline-flex"
          >
            <Zap size={13} strokeWidth={1.5} aria-hidden="true" />
            Run analysis
          </button>
        )}

        <div className="lx-userchip">
          <span className="lx-userchip__avatar" aria-hidden="true">
            {user?.email ? user.email.slice(0, 2).toUpperCase() : 'TR'}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="lx-icon-btn lx-icon-btn--alarm"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={16} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>
      </div>
    </header>
  )
}
