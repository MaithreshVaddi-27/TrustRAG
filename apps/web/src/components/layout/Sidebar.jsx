import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Brain, Database, FileSearch,
  GitMerge, LayoutDashboard,
  Settings, Zap, ShieldCheck,
  PanelLeftClose, PanelLeftOpen,
} from 'lucide-react'

const NAV = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Playground', to: '/playground', icon: Zap, meta: 'Live' },
  null,
  { label: 'Knowledge Bases', to: '/knowledge-bases', icon: Database },
  { label: 'Evidence', to: '/evidence', icon: FileSearch },
  { label: 'Claims', to: '/claims', icon: Brain },
  { label: 'Conflicts', to: '/conflicts', icon: GitMerge },
  null,
  { label: 'Settings', to: '/settings', icon: Settings },
]

/**
 * Sidebar — the primary navigation.
 *
 * Rows are 36px, the icon column is fixed, and the label never wraps. The
 * active row is marked with a Laser Crimson rule on its left edge, because
 * crimson is the selection colour in this system.
 */
export function Sidebar({ isCollapsed, sidebarWidth, toggleSidebar }) {
  return (
    <aside
      style={{ width: sidebarWidth }}
      className="lx-sidebar"
      aria-label="Primary navigation"
    >
      <nav className="lx-sidebar__nav">
        {NAV.map((item, index) =>
          item === null ? (
            <div key={`sep-${index}`} className="lx-sidebar__sep" />
          ) : (
            <SidebarLink key={item.to} {...item} isCollapsed={isCollapsed} />
          ),
        )}
      </nav>

      <div className="lx-sidebar__footer">
        <SidebarStatus isCollapsed={isCollapsed} />

        <button
          type="button"
          onClick={toggleSidebar}
          className="lx-collapse-btn"
          title={isCollapsed ? 'Expand sidebar (⌘B)' : 'Collapse sidebar (⌘B)'}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <PanelLeftOpen size={15} aria-hidden="true" />
          ) : (
            <>
              <span className="flex items-center gap-2">
                <PanelLeftClose size={15} aria-hidden="true" />
                <span>Collapse</span>
              </span>
              <kbd className="lx-kbd">⌘B</kbd>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}

function SidebarLink({ to, label, icon: Icon, meta, isCollapsed }) {
  return (
    <NavLink
      to={to}
      title={isCollapsed ? label : undefined}
      className={({ isActive }) =>
        clsx(
          'lx-navlink',
          isActive && 'lx-navlink--active',
          isCollapsed && 'justify-center px-0',
        )
      }
    >
      {() => (
        <>
          <Icon
            size={16}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
            className="lx-navlink__icon"
          />

          {!isCollapsed && (
            <>
              <span className="lx-navlink__label">{label}</span>
              {meta && (
                <span className="lx-navlink__meta flex items-center gap-1.5">
                  <span className="lx-dot lx-dot--live" aria-hidden="true" />
                  {meta}
                </span>
              )}
            </>
          )}
        </>
      )}
    </NavLink>
  )
}

function SidebarStatus({ isCollapsed }) {
  return (
    <div className={clsx('lx-sidebar__status', isCollapsed && 'justify-center px-2')}>
      <ShieldCheck
        size={15}
        strokeWidth={1.5}
        aria-hidden="true"
        focusable="false"
        className="shrink-0 text-silver-400"
      />

      {!isCollapsed && (
        <div className="min-w-0">
          <p className="lx-sidebar__status-title truncate">Self-healing loop</p>
          <p className="lx-sidebar__status-meta truncate">StateGraph v1.0 active</p>
        </div>
      )}

      {isCollapsed && (
        <span className="lx-sr-only">Self-healing loop, StateGraph v1.0 active</span>
      )}
    </div>
  )
}
