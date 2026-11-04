import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import { motion, AnimatePresence } from 'motion/react'
import {
  Brain, Database, FileSearch,
  GitMerge, LayoutDashboard,
  Settings, Zap, ShieldCheck,
  PanelLeftClose, PanelLeftOpen,
} from 'lucide-react'
import { SPRING_SNAPPY, SPRING_GENTLE } from '@/lib/motionConfig'

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

// Self-healing status item (always visible, not a navigation link)
const STATUS_ITEM = {
  id: 'status',
  label: 'Self-Healing Loop',
  subtitle: 'StateGraph v1.0 Active',
  icon: ShieldCheck,
  color: 'text-emerald-400',
}

/**
 * Sidebar - Desktop navigation sidebar
 * Called by: AppLayout.jsx
 */
export function Sidebar({ isCollapsed, sidebarWidth, toggleSidebar }) {
  return (
    <motion.aside
      style={{
        width: sidebarWidth,
        flexShrink: 0,
      }}
      className="flex flex-col justify-between glass-sidebar z-50 shrink-0 hidden md:flex h-full min-h-0"
      transition={SPRING_SNAPPY}
    >
      {/* Navigation Links */}
      <nav className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden py-3 px-2 space-y-1 custom-scrollbar">
        {NAV.map((item, i) =>
          item === null ? (
            <motion.div
              key={`sep-${i}`}
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

      {/* Pinned Footer: Status Widget + Toggle Button */}
      <div className="shrink-0 p-2.5 space-y-2 border-t border-slate-800/80 bg-surface-900/60 backdrop-blur-md">
        <SidebarStatus
          {...STATUS_ITEM}
          isCollapsed={isCollapsed}
        />

        <motion.button
          onClick={toggleSidebar}
          whileTap={{ scale: 0.95 }}
          whileHover={{ scale: 1.01 }}
          className={clsx(
            'w-full flex items-center rounded-xl p-2 text-xs font-medium text-slate-400 hover:text-white hover:bg-surface-800/90 border border-slate-800/80 hover:border-cyan-500/30 transition-all cursor-pointer',
            isCollapsed ? 'justify-center' : 'justify-between px-3'
          )}
          title={isCollapsed ? 'Expand sidebar (⌘B)' : 'Collapse sidebar (⌘B)'}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <PanelLeftOpen size={16} className="text-cyan-400" />
          ) : (
            <>
              <span className="flex items-center gap-2">
                <PanelLeftClose size={15} className="text-slate-400" />
                <span className="text-slate-300">Collapse</span>
              </span>
              <kbd className="text-[10px] font-mono text-slate-400 bg-surface-800 px-1.5 py-0.5 rounded border border-slate-700/60">
                ⌘B
              </kbd>
            </>
          )}
        </motion.button>
      </div>
    </motion.aside>
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
          className={clsx('w-full flex items-center', isCollapsed ? 'justify-center' : 'gap-3')}
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
              aria-hidden="true"
              focusable="false"
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

          {/* Floating Tooltip in Collapsed Mode */}
          {isCollapsed && (
            <div
              role="tooltip"
              className="sidebar-tooltip opacity-0 pointer-events-none group-hover:opacity-100 group-focus-within:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all duration-150"
            >
              {label}
            </div>
          )}
        </motion.div>
      )}
    </NavLink>
  )
}

function SidebarStatus({ label, subtitle, icon: Icon, color, isCollapsed }) {
  return (
    <div
      className={clsx(
        'relative flex items-center rounded-xl group p-2.5 w-full',
        isCollapsed
          ? 'justify-center'
          : 'gap-2.5 px-3.5 py-2',
        'bg-surface-800/40 border border-slate-800 hover:border-slate-700 transition-colors'
      )}
    >
      <Icon
        size={16}
        aria-hidden="true"
        focusable="false"
        className={clsx('shrink-0', color)}
      />

      <AnimatePresence mode="wait">
        {!isCollapsed && (
          <motion.div
            key="expanded"
            initial={{ opacity: 0, width: 0, height: 0 }}
            animate={{ opacity: 1, width: 'auto', height: 'auto' }}
            exit={{ opacity: 0, width: 0, height: 0 }}
            transition={SPRING_SNAPPY}
            className="flex flex-col min-w-0 overflow-hidden"
          >
            <p className="text-[11px] font-semibold text-slate-300 truncate">{label}</p>
            <p className="text-[10px] text-slate-500 truncate">{subtitle}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {isCollapsed && (
        <div
          role="tooltip"
          className="sidebar-tooltip opacity-0 pointer-events-none group-hover:opacity-100 group-focus-within:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all duration-150"
        >
          <div className="text-[11px] font-semibold text-slate-300">{label}</div>
          <div className="text-[10px] text-slate-500">{subtitle}</div>
        </div>
      )}
    </div>
  )
}