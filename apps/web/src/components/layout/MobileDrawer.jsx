import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { clsx } from 'clsx'
import { X, LayoutDashboard, Zap, Database, FileSearch, Brain, GitMerge, Settings, ShieldCheck } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { SPRING_SNAPPY } from '@/lib/motionConfig'

const NAV = [
  { label: 'Dashboard',       to: '/dashboard',       icon: LayoutDashboard, badge: null },
  { label: 'Playground',      to: '/playground',      icon: Zap,             badge: 'Live' },
  null,
  { label: 'Knowledge Bases', to: '/knowledge-bases', icon: Database,        badge: null },
  { label: 'Evidence',        to: '/evidence',        icon: FileSearch,      badge: null },
  { label: 'Claims',          to: '/claims',          icon: Brain,           badge: null },
  { label: 'Conflicts',       to: '/conflicts',       icon: GitMerge,        badge: null },
  null,
  { label: 'Settings',        to: '/settings',        icon: Settings,        badge: null },
]

const drawerWidth = 256

/**
 * MobileDrawer - Mobile navigation drawer with smooth slide-in animation
 * Called by: AppLayout.jsx
 */
export function MobileDrawer({ isMobileOpen, setIsMobileOpen }) {
  const mobileCloseRef = useRef(null)

  // Mobile drawer: Escape to close, scroll lock, focus close on open.
  useEffect(() => {
    if (!isMobileOpen) return
    mobileCloseRef.current?.focus()
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = e => {
      if (e.key === 'Escape') setIsMobileOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prevOverflow
      window.removeEventListener('keydown', onKey)
    }
  }, [isMobileOpen, setIsMobileOpen])

  return (
    <AnimatePresence>
      {isMobileOpen && (
        <>
          {/* Mobile Backdrop Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setIsMobileOpen(false)}
            className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm md:hidden"
            aria-hidden="true"
          />

          {/* Mobile Drawer */}
          <motion.div
            initial={{ x: -drawerWidth }}
            animate={{ x: 0 }}
            exit={{ x: -drawerWidth }}
            transition={SPRING_SNAPPY}
            className={clsx(
              'flex flex-col border-r border-slate-800/80 bg-surface-900/95 backdrop-blur-xl z-50 shrink-0',
              'md:hidden fixed inset-y-0 left-0 top-16 w-64 shadow-2xl shadow-black',
            )}
          >
            {/* Mobile close button header */}
            <div className="flex items-center justify-between p-3 border-b border-slate-800">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Navigation</span>
              <motion.button
                ref={mobileCloseRef}
                onClick={() => setIsMobileOpen(false)}
                whileTap={{ scale: 0.9 }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
                title="Close sidebar"
                aria-label="Close navigation menu"
              >
                <X size={16} aria-hidden="true" />
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
                    onNavigate={() => setIsMobileOpen(false)}
                  />
                )
              )}
            </nav>

            {/* Sidebar Footer / Quick Status */}
            <div className="p-3 border-t border-slate-800/80">
              <div className="p-2.5 rounded-xl bg-surface-800/40 border border-slate-800 flex items-center gap-2.5">
                <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-slate-300 truncate">Self-Healing Loop</p>
                  <p className="text-[10px] text-slate-500 truncate">StateGraph v1.0 Active</p>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

function SidebarLink({ to, label, icon: Icon, badge, onNavigate }) {
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) => clsx(
        'relative flex items-center rounded-xl text-sm font-medium group',
        isActive
          ? 'bg-primary-500/15 text-primary-300 border border-primary-500/30 shadow-sm shadow-primary-950/80'
          : 'text-slate-400 hover:text-slate-100 hover:bg-surface-800/60 border border-transparent',
        'gap-3 px-3.5 py-2.5'
      )}
    >
      {({ isActive }) => (
        <motion.div
          whileTap={{ scale: 0.98 }}
          transition={SPRING_SNAPPY}
          className="w-full flex items-center gap-3"
        >
          {/* Active cyan indicator bar */}
          <AnimatePresence>
            {isActive && (
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
              aria-hidden="true"
              focusable="false"
              className={clsx(
                'shrink-0 transition-colors',
                isActive ? 'text-primary-400' : 'text-slate-400 group-hover:text-slate-200'
              )}
            />
          </motion.div>

          <span className="truncate flex-1 overflow-hidden">
            {label}
          </span>

          {badge && (
            <span className="px-1.5 py-[2px] rounded text-[10px] font-mono font-semibold bg-primary-500/20 text-primary-300 border border-primary-500/30">
              {badge}
            </span>
          )}
        </motion.div>
      )}
    </NavLink>
  )
}