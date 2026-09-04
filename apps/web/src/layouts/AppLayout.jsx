import { useState, useEffect } from 'react'
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { useQuery } from '@tanstack/react-query'
import { motion, useReducedMotion, useMotionValue, useSpring, useDragControls, useTransform } from 'motion/react'
import {
  Brain, Database, FileSearch,
  FlaskConical, GitMerge, LayoutDashboard, LogOut,
  Settings, Swords, Zap, Menu, X, ChevronLeft, ChevronRight,
  ShieldCheck, Cpu, Layers
} from 'lucide-react'
import { authStore, useAuthStore } from '@/store/authStore'
import { modelService } from '@/services/api'

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

  // Motion values for spring animations
  const sidebarWidth = useSpring(isCollapsed ? 72 : 240, { damping: 15, stiffness: 150 })
  const sidebarOpacity = useMotionValue(1)
  const mobileDrawerX = useSpring(isMobileOpen ? 0 : -256, { damping: 15, stiffness: 150 })
  
  // Track if we're currently animating

  // Close mobile drawer on route change
  useEffect(() => {
    setIsMobileOpen(false)
  }, [location.pathname])

  // Animate sidebar width on collapse/expand with spring
  useEffect(() => {
    const targetWidth = isCollapsed ? 72 : 240
    if (!reducedMotion) {
      sidebarWidth.set(targetWidth)
    } else {
      sidebarWidth.set(targetWidth)
    }
  }, [isCollapsed, sidebarWidth, reducedMotion])

  // Animate mobile drawer
  useEffect(() => {
    const targetX = isMobileOpen ? 0 : -256
    if (!reducedMotion) {
      mobileDrawerX.set(targetX)
    } else {
      mobileDrawerX.set(targetX)
    }
  }, [isMobileOpen, mobileDrawerX, reducedMotion])

  const toggleSidebar = () => {
    setIsCollapsed(prev => {
      const next = !prev
      try {
        localStorage.setItem('trustrag_sidebar_collapsed', String(next))
      } catch (e) {
        console.warn('Could not persist sidebar preference', e)
      }
      return next
    })
  }

  // Rubber-band drag for mobile drawer
  const dragX = useMotionValue(0)
  const drawerWidth = 256 // w-64 = 256px
  
  // Transform dragX with rubber-banding: resist progressively past boundaries
  const rubberBandTransform = useTransform(dragX, 
    [-drawerWidth, 0, drawerWidth], // input range
    [-drawerWidth * 1.5, 0, drawerWidth * 1.5] // output range with rubber-band
  )

  const dragControls = useDragControls()

  function handleLogout() {
    authStore.clearSession()
    navigate('/login')
  }

  return (
    <div className="flex flex-col h-screen bg-surface-950 text-slate-100 overflow-hidden select-none">
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
            transition={{ type: 'spring', damping: 15, stiffness: 150 }}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/40 border border-emerald-800/50 text-[11px] font-mono text-emerald-300 shadow-sm shadow-emerald-950/30"
          >
            <motion.span
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
              className="w-2 h-2 rounded-full bg-emerald-400"
            />
            <span>API Online</span>
          </motion.div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-800/60 border border-slate-700/60 text-[11px] font-mono text-slate-300">
            <Cpu size={12} className="text-primary-400" />
            <span className="max-w-[200px] truncate" title={providersData?.active_model}>
              {providersData?.active_provider === 'ollama'
                ? `Ollama: ${providersData?.active_model || 'granite4.2:3b-q4_K_M'}`
                : (providersData?.active_provider === 'llama_cpp' || providersData?.active_provider === 'llamacpp')
                ? `llama.cpp: ${providersData?.active_model || 'GGUF'}`
                : (providersData?.active_model || 'Local LLM')}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-800/60 border border-slate-700/60 text-[11px] font-mono text-slate-300">
            <Layers size={12} className="text-cyan-400" />
            <span className="max-w-[210px] truncate" title={providersData?.active_embedding_model}>
              {providersData?.active_embedding_model || 'embeddinggemma:300m-qat-q8_0'}
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

      {/* ── BODY (SIDEBAR + CONTENT) ───────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden relative">
        {/* Mobile Backdrop Overlay */}
        {isMobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsMobileOpen(false)}
            className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm md:hidden"
          />
        )}

        {/* ── DESKTOP SIDEBAR ──────────────────────────────────────────────────── */}
        <motion.aside
          style={{
            width: sidebarWidth,
            opacity: sidebarOpacity,
            flexShrink: 0,
          }}
          className={clsx(
            'flex flex-col border-r border-slate-800/80 bg-surface-900/95 backdrop-blur-xl z-50 shrink-0',
            'hidden md:flex',
          )}
          transition={{ type: 'spring', damping: 15, stiffness: 150 }}
        >
          {/* Navigation Links */}
          <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
            {NAV.map((item, i) =>
              item === null ? (
                <div key={i} className="my-2 border-t border-slate-800/60" />
              ) : (
                <SidebarLink
                  key={item.to}
                  {...item}
                  isCollapsed={isCollapsed}
                />
              )
            )}
          </nav>

          {/* Sidebar Footer / Quick Status */}
          <div className="p-3 border-t border-slate-800/80">
            {!isCollapsed ? (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ type: 'spring', damping: 15, stiffness: 150 }}
                className="p-2.5 rounded-xl bg-surface-800/40 border border-slate-800 flex items-center gap-2.5"
              >
                <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-slate-300 truncate">Self-Healing Loop</p>
                  <p className="text-[10px] text-slate-500 truncate">StateGraph v1.0 Active</p>
                </div>
              </motion.div>
            ) : (
              <div className="flex justify-center" title="Self-Healing Loop Active">
                <ShieldCheck size={18} className="text-emerald-400" />
              </div>
            )}
          </div>
        </motion.aside>

        {/* ── MOBILE DRAWER with Rubber-Banding ────────────────────────── */}
        <motion.div
          {...dragControls}
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
          transition={{ type: 'spring', damping: 15, stiffness: 150 }}
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
              transition={{ type: 'spring', damping: 15, stiffness: 150 }}
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
        'relative flex items-center rounded-xl text-sm font-medium transition-all duration-200 group',
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
          className="w-full flex items-center"
        >
          {/* Active cyan indicator bar */}
          {isActive && !isCollapsed && (
            <motion.span
              initial={{ height: 0 }}
              animate={{ height: 'calc(100% - 8px)' }}
              exit={{ height: 0 }}
              transition={{ type: 'spring', damping: 15, stiffness: 150 }}
              className="absolute left-0 inset-y-2 w-1 rounded-r-full bg-cyan-400 shadow-sm shadow-cyan-400"
            />
          )}

          <motion.div
            whileTap={{ scale: 0.9 }}
            className="shrink-0 transition-transform group-hover:scale-110"
          >
            <Icon
              size={18}
              className={clsx(
                'shrink-0 transition-transform group-hover:scale-110',
                isActive ? 'text-primary-400' : 'text-slate-400 group-hover:text-slate-200'
              )}
            />
          </motion.div>

          {!isCollapsed && (
            <span className="truncate flex-1">{label}</span>
          )}

          {!isCollapsed && badge && (
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ type: 'spring', damping: 15, stiffness: 150 }}
              className="px-1.5 py-[2px] rounded text-[10px] font-mono font-semibold bg-primary-500/20 text-primary-300 border border-primary-500/30"
            >
              {badge}
            </motion.span>
          )}

          {/* Floating Tooltip in Collapsed Mode */}
          {isCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ type: 'spring', damping: 15, stiffness: 150 }}
              className="absolute left-full ml-2 px-2.5 py-1 rounded-lg bg-surface-800 border border-slate-700 text-xs text-slate-200 font-medium whitespace-nowrap pointer-events-none shadow-xl z-50"
            >
              {label}
            </motion.div>
          )}
        </motion.div>
      )}
    </NavLink>
  )
}
