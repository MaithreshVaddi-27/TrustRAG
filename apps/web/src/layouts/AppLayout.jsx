import { useState, useEffect, useCallback } from 'react'
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { useQuery } from '@tanstack/react-query'
import { motion, useReducedMotion, useMotionValue, useSpring, useTransform, AnimatePresence } from 'motion/react'
import {
  Brain, Database, FileSearch,
  FlaskConical, GitMerge, LayoutDashboard, LogOut,
  Settings, Swords, Zap, Menu, X, ChevronLeft, ChevronRight,
  ShieldCheck, Cpu, Layers, RefreshCw
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/auth'
import { modelService } from '@/services/api'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'
import { SPRING_SNAPPY, SPRING_GENTLE } from '@/lib/motionConfig'
import useBackendHealth from '@/hooks/useBackendHealth'

function readPlaygroundEngine() {
  try {
    const raw = localStorage.getItem('trustrag.playground.engine')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const NAV = [
  { label: 'Dashboard',       to: '/dashboard',       icon: LayoutDashboard, badge: null },
  { label: 'Playground',      to: '/playground',      icon: Zap,             badge: 'Live' },
  null, // divider
  { label: 'Knowledge Bases', to: '/knowledge-bases', icon: Database,        badge: null },
  { label: 'Evidence',        to: '/evidence',        icon: FileSearch,      badge: null },
  { label: 'Claims',          to: '/claims',          icon: Brain,           badge: null },
  { label: 'Conflicts',       to: '/conflicts',       icon: GitMerge,        badge: null },
  null,
  { label: 'Experiments',     to: '/experiments',     icon: FlaskConical,    badge: null },
  null,
  { label: 'Settings',        to: '/settings',        icon: Settings,        badge: null },
]

export default function AppLayout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const reducedMotion = useReducedMotion()
  const { isOnline, isChecking, recheck } = useBackendHealth()

  // Cursor-follow glow position
  const cursorX = useMotionValue(0)
  const cursorY = useMotionValue(0)
  const glowX = useSpring(cursorX, { damping: 30, stiffness: 200 })
  const glowY = useSpring(cursorY, { damping: 30, stiffness: 200 })

  useEffect(() => {
    const handler = (e) => {
      cursorX.set(e.clientX)
      cursorY.set(e.clientY)
    }
    window.addEventListener('mousemove', handler)
    return () => window.removeEventListener('mousemove', handler)
  }, [cursorX, cursorY])

  // Dynamic model telemetry query
  const { data: providersData } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
    staleTime: 30000,
  })

  // Sidebar collapse state with localStorage persistence
  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return localStorage.getItem('trustrag_sidebar_collapsed') === 'true'
    } catch {
      return false
    }
  })

  // Mobile drawer state
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // Playground engine override: the top pills show what the Playground will
  // actually run (user selection), falling back to the server default.
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

  const serverProvider = providersData?.active_provider
  const serverModel = providersData?.active_model
  const effProvider = playgroundEngine?.provider || serverProvider
  const effModel = playgroundEngine?.model || serverModel
  const isEngineOverride = !!playgroundEngine?.model && playgroundEngine.model !== serverModel
  const serverEmbeddingModel = providersData?.active_embedding_model
  const effEmbeddingModel = playgroundEngine?.embeddingModel || serverEmbeddingModel
  const isEmbeddingOverride = !!playgroundEngine?.embeddingModel && playgroundEngine.embeddingModel !== serverEmbeddingModel

  // Motion values for spring animations
  const sidebarWidth = useSpring(isCollapsed ? 72 : 240, { damping: 20, stiffness: 220 })
  const mobileDrawerX = useSpring(isMobileOpen ? 0 : -256, { damping: 20, stiffness: 220 })

  // Close mobile drawer on route change
  useEffect(() => {
    setIsMobileOpen(false)
  }, [location.pathname])

  // Animate sidebar width on collapse/expand with spring
  useEffect(() => {
    const targetWidth = isCollapsed ? 72 : 240
    sidebarWidth.set(targetWidth)
  }, [isCollapsed, sidebarWidth])

  // Animate mobile drawer
  useEffect(() => {
    const targetX = isMobileOpen ? 0 : -256
    mobileDrawerX.set(targetX)
  }, [isMobileOpen, mobileDrawerX])

  const toggleSidebar = useCallback(() => {
    setIsCollapsed(prev => {
      const next = !prev
      try {
        localStorage.setItem('trustrag_sidebar_collapsed', String(next))
      } catch (e) {
        console.warn('Could not persist sidebar preference', e)
      }
      return next
    })
  }, [])

  // Rubber-band drag for mobile drawer
  const dragX = useMotionValue(0)
  const drawerWidth = 256

  // Transform dragX with rubber-banding: resist progressively past boundaries
  const rubberBandTransform = useTransform(dragX,
    [-drawerWidth, 0, drawerWidth],
    [-drawerWidth * 1.5, 0, drawerWidth * 1.5]
  )

  async function handleLogout() {
    await authService.logout()
    navigate('/login')
  }

  return (
    <div className="flex flex-col h-screen bg-surface-950 text-slate-100 overflow-hidden select-none">
      {/* ── CURSOR GLOW ──────────────────────────────────────────────────── */}
      {!reducedMotion && (
        <motion.div
          className="cursor-glow hidden md:block"
          style={{ left: glowX, top: glowY }}
        />
      )}

      {/* ── TOP NAVBAR ─────────────────────────────────────────────────── */}
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

          {/* Desktop Sidebar Collapse / Expand Toggle Button */}
          <motion.button
            onClick={toggleSidebar}
            whileTap={{ scale: 0.9 }}
            className="hidden md:flex items-center justify-center w-8 h-8 rounded-xl text-slate-400 hover:text-white hover:bg-surface-800/90 border border-slate-800 transition-all ml-2"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </motion.button>
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
              ? `${effEmbeddingModel} · ${isEmbeddingOverride ? 'Playground selection' : 'Server default'}`
              : 'Embedding model not configured'}
          >
            <Layers size={12} className="text-cyan-400 shrink-0" />
            <span
              className={`w-1.5 h-1.5 rounded-full shrink-0 ${isEmbeddingOverride ? 'bg-cyan-400' : 'bg-slate-500'}`}
              title={isEmbeddingOverride ? 'Playground selection' : 'Server default'}
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

      {/* ── BACKEND-DOWN BANNER ─────────────────────────────────────────── */}
      <AnimatePresence>
        {isOnline === false && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={SPRING_SNAPPY}
            className="overflow-hidden z-30 border-b border-red-900/40 bg-red-950/30 backdrop-blur-sm"
          >
            <div className="flex items-center justify-center gap-2 py-2 px-4 text-xs text-red-300">
              <span className="shrink-0">
                Backend unreachable — start the API server to enable analysis.
              </span>
              <motion.button
                onClick={recheck}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="shrink-0 ml-1 px-2 py-0.5 rounded-lg bg-red-900/30 border border-red-800/40 text-red-200 hover:text-red-100 hover:bg-red-900/50 transition-colors text-[11px] font-mono"
              >
                <RefreshCw size={11} className="inline mr-1" />
                Retry
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── BODY (SIDEBAR + CONTENT) ───────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden relative">
        {/* Mobile Backdrop Overlay */}
        <AnimatePresence>
          {isMobileOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setIsMobileOpen(false)}
              className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm md:hidden"
            />
          )}
        </AnimatePresence>

        {/* ── DESKTOP SIDEBAR (glassmorphism) ──────────────────────────── */}
        <motion.aside
          style={{
            width: sidebarWidth,
            flexShrink: 0,
          }}
          className={clsx(
            'flex flex-col glass-sidebar z-50 shrink-0',
            'hidden md:flex',
          )}
          transition={SPRING_SNAPPY}
        >
          {/* Navigation Links — staggered entrance */}
          <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
            {NAV.map((item, i) =>
              item === null ? (
                <motion.div
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03, ...SPRING_GENTLE }}
                  className="my-2 border-t border-slate-800/60"
                />
              ) : (
                <motion.div
                  key={item.to}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03, ...SPRING_GENTLE }}
                >
                  <SidebarLink
                    {...item}
                    isCollapsed={isCollapsed}
                  />
                </motion.div>
              )
            )}
          </nav>

          {/* Sidebar Footer / Quick Status */}
          <div className="p-3 border-t border-slate-800/80">
            <AnimatePresence mode="wait">
              {!isCollapsed ? (
                <motion.div
                  key="expanded-status"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={SPRING_SNAPPY}
                  className="p-2.5 rounded-xl bg-surface-800/40 border border-slate-800 flex items-center gap-2.5 overflow-hidden"
                >
                  <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold text-slate-300 truncate">Self-Healing Loop</p>
                    <p className="text-[10px] text-slate-500 truncate">StateGraph v1.0 Active</p>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="collapsed-status"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={SPRING_SNAPPY}
                  className="flex justify-center"
                  title="Self-Healing Loop Active"
                >
                  <ShieldCheck size={18} className="text-emerald-400" />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.aside>

        {/* ── MOBILE DRAWER with Rubber-Banding ────────────────────────── */}
        <motion.div
          style={{
            x: isMobileOpen ? dragX : rubberBandTransform,
            display: isMobileOpen ? 'flex' : 'none',
          }}
          className={clsx(
            'flex flex-col border-r border-slate-800/80 bg-surface-900/95 backdrop-blur-xl z-50 shrink-0',
            'md:hidden fixed inset-y-0 left-0 top-16 w-64 shadow-2xl shadow-black',
          )}
          drag="x"
          dragConstraints={{ left: -drawerWidth, right: 0 }}
          dragElastic={0.2}
          transition={SPRING_SNAPPY}
        >
          {/* Mobile close button header */}
          <div className="flex items-center justify-between p-3 border-b border-slate-800">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Navigation</span>
            <motion.button
              onClick={() => setIsMobileOpen(false)}
              whileTap={{ scale: 0.9 }}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
              title="Close sidebar"
            >
              <X size={16} />
            </motion.button>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
            {NAV.map((item, i) =>
              item === null ? (
                <div key={i} className="my-2 border-t border-slate-800/60" />
              ) : (
                <SidebarLink
                  key={item.to}
                  {...item}
                  isCollapsed={false}
                />
              )
            )}
          </nav>

          {/* Sidebar Footer / Quick Status */}
          <div className="p-3 border-t border-slate-800/80">
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={SPRING_SNAPPY}
              className="p-2.5 rounded-xl bg-surface-800/40 border border-slate-800 flex items-center gap-2.5"
            >
              <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
              <div className="min-w-0">
                <p className="text-[11px] font-semibold text-slate-300 truncate">Self-Healing Loop</p>
                <p className="text-[10px] text-slate-500 truncate">StateGraph v1.0 Active</p>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* ── MAIN CONTENT AREA ─────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-surface-950 bg-cyber-grid relative h-full flex flex-col">
          {children}
        </main>
      </div>
    </div>
  )
}

function SidebarLink({ to, label, icon: Icon, badge, isCollapsed }) {
  return (
    <NavLink
      to={to}
      title={isCollapsed ? label : undefined}
      className={({ isActive }) => clsx(
        'relative flex items-center rounded-xl text-sm font-medium group',
        isCollapsed
          ? 'justify-center p-3'
          : 'gap-3 px-3.5 py-2.5',
        isActive
          ? 'bg-primary-500/15 text-primary-300 border border-primary-500/30 shadow-sm shadow-primary-950/80'
          : 'text-slate-400 hover:text-slate-100 hover:bg-surface-800/60 border border-transparent',
      )}
    >
      {({ isActive }) => (
        <motion.div
          whileTap={{ scale: isCollapsed ? 0.9 : 0.98 }}
          transition={SPRING_SNAPPY}
          className="w-full flex items-center"
        >
          {/* Active cyan indicator bar */}
          <AnimatePresence>
            {isActive && !isCollapsed && (
              <motion.span
                initial={{ height: 0 }}
                animate={{ height: 'calc(100% - 8px)' }}
                exit={{ height: 0 }}
                transition={SPRING_SNAPPY}
                className="absolute left-0 inset-y-2 w-1 rounded-r-full bg-cyan-400 shadow-sm shadow-cyan-400"
              />
            )}
          </AnimatePresence>

          <motion.div
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.9 }}
            transition={SPRING_SNAPPY}
            className="shrink-0"
          >
            <Icon
              size={18}
              className={clsx(
                'shrink-0 transition-colors',
                isActive ? 'text-primary-400' : 'text-slate-400 group-hover:text-slate-200'
              )}
            />
          </motion.div>

          {/* Label — AnimatePresence for smooth collapse/expand */}
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.span
                key="label"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={SPRING_SNAPPY}
                className="truncate flex-1 overflow-hidden"
              >
                {label}
              </motion.span>
            )}
          </AnimatePresence>

          {/* Badge — AnimatePresence for smooth appearance */}
          <AnimatePresence>
            {!isCollapsed && badge && (
              <motion.span
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={SPRING_SNAPPY}
                className="px-1.5 py-[2px] rounded text-[10px] font-mono font-semibold bg-primary-500/20 text-primary-300 border border-primary-500/30"
              >
                {badge}
              </motion.span>
            )}
          </AnimatePresence>

          {/* Floating Tooltip in Collapsed Mode — AnimatePresence for spring entrance */}
          <AnimatePresence>
            {isCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -8, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -8, scale: 0.95 }}
                transition={SPRING_GENTLE}
                className="sidebar-tooltip"
              >
                {label}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </NavLink>
  )
}
