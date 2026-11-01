import { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import { clsx } from 'clsx'
import { Link } from 'react-router-dom'
import {
  Brain, Database, FileSearch,
  GitMerge, LayoutDashboard, LogOut,
  Settings, Swords, Zap, Menu, X, ChevronLeft, ChevronRight,
  ShieldCheck, Cpu, Layers, RefreshCw
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/auth'
import { modelService } from '@/services/api'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'
import { SPRING_SNAPPY, SPRING_GENTLE } from '@/lib/motionConfig'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

function readPlaygroundEngine() {
  try {
    const raw = localStorage.getItem('trustrag.playground.engine')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/**
 * Navbar - Top header with brand, telemetry pills, and user menu
 * Called by: AppLayout.jsx
 * No existing file serves this purpose - extracted from AppLayout
 * Reads: localStorage 'trustrag.playground.engine', model providers from API, backend health
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function Navbar({ isOnline, isChecking, recheck, isCollapsed, setIsMobileOpen }) {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  // Playground engine override
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

  async function handleLogout() {
    await authService.logout()
    navigate('/login')
  }

  return (
    <header className="h-16 shrink-0 z-40 bg-surface-900/90 backdrop-blur-xl border-b border-slate-800/80 px-4 flex items-center justify-between shadow-md shadow-black/30">
      {/* Left: Brand + Sidebar Toggle Button */}
      <div className="flex items-center gap-3">
        {/* Mobile hamburger button */}
        <motion.button
          onClick={() => setIsMobileOpen(true)}
          whileTap={{ scale: 0.95 }}
          className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-800 border border-slate-800 transition-colors"
          title="Open Navigation Menu"
          aria-label="Open Navigation Menu"
        >
          <Menu size={18} />
        </motion.button>

        {/* Logo */}
        <Link to="/dashboard" className="flex items-center gap-2.5 group">
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="w-8 h-8 rounded-xl bg-gradient-to-tr from-primary-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-primary-950/60"
          >
            <Swords size={16} className="text-white" />
          </motion.div>
          <div className="flex flex-col">
            <span className="font-extrabold text-sm tracking-tight text-white flex items-center gap-1">
              TRUST<span className="text-primary-400">RAG</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest hidden sm:inline">
              Reliability Workbench
            </span>
          </div>
        </Link>

              </div>

      {/* Center: Live Engine Telemetry Badges (Desktop) */}
      <div className="hidden lg:flex items-center gap-2.5">
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={SPRING_GENTLE}
          className={clsx(
            'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono shadow-sm',
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
          <span>{isOnline === false ? 'API Offline' : isOnline === null ? 'Checking…' : 'API Online'}</span>
          {isOnline === false && (
            <motion.button
              onClick={recheck}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              className="ml-0.5 text-red-400/80 hover:text-red-300 transition-colors"
              title="Reconnect to backend"
            >
              <RefreshCw size={10} />
            </motion.button>
          )}
        </motion.div>

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
          <span className="max-w-[220px] truncate tracking-tight">
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
          <span className="max-w-[210px] truncate tracking-tight">
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

      {/* Right: Quick Action & User Profile */}
      <div className="flex items-center gap-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => navigate('/playground')}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-md shadow-primary-950/50 transition-all"
        >
          <Zap size={13} />
          <span>Run Analysis</span>
        </motion.button>

        {/* User initials & logout */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="w-8 h-8 rounded-full bg-surface-800 border border-slate-700 flex items-center justify-center text-xs font-mono font-bold text-slate-300 shadow-inner">
            {user?.email ? user.email.slice(0, 2).toUpperCase() : 'TR'}
          </div>
          <motion.button
            onClick={handleLogout}
            whileTap={{ scale: 0.9, rotate: 180 }}
            className="p-2 rounded-xl text-slate-400 hover:text-red-400 hover:bg-surface-800/80 border border-transparent hover:border-red-900/30 transition-colors"
            title="Logout"
            aria-label="Logout"
          >
            <LogOut size={16} />
          </motion.button>
        </div>
      </div>
    </header>
  )
}