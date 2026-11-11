import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { NAV_GROUPS } from './navigation'
import { EngineStatus } from './EngineStatus'

/**
 * Sidebar — the primary navigation.
 *
 * Rows are 36px, the icon column is fixed, and the label never wraps. The
 * active row is marked with a Laser Crimson rule on its left edge, because
 * crimson is the selection colour in this system.
 *
 * The groups are named. A separator says "something changes here"; a label
 * says what.
 */
export function Sidebar({
  isCollapsed,
  sidebarWidth,
  toggleSidebar,
  isOnline,
  isChecking,
  providersData,
}) {
  return (
    <aside
      style={{ width: sidebarWidth }}
      className="lx-sidebar"
      aria-label="Primary navigation"
    >
      <nav className="lx-sidebar__nav">
        {NAV_GROUPS.map((group) => (
          <div key={group.id} className="lx-sidebar__group">
            {!isCollapsed && (
              <p className="lx-sidebar__group-label" aria-hidden="true">
                {group.label}
              </p>
            )}
            {group.items.map((item) => (
              <SidebarLink key={item.to} {...item} isCollapsed={isCollapsed} />
            ))}
          </div>
        ))}
      </nav>

      <div className="lx-sidebar__footer">
        {!isCollapsed && (
          <EngineStatus
            isOnline={isOnline}
            isChecking={isChecking}
            providersData={providersData}
          />
        )}

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
