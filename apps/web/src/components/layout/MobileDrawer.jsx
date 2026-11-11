import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import { X, ShieldCheck } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { NAV_GROUPS } from './navigation'

const DRAWER_WIDTH = 288

/**
 * MobileDrawer — the application navigation on small screens.
 *
 * A drawer anchored to the left edge with a scrim behind it, not a
 * full-viewport takeover: the page underneath stays visible, so the user
 * can see what they are navigating away from.
 *
 * Focus moves into the drawer when it opens, is trapped inside it while
 * it is open, and returns to the trigger when it closes.
 */
export function MobileDrawer({ isMobileOpen, setIsMobileOpen }) {
  const panelRef = useRef(null)
  const closeRef = useRef(null)

  useEffect(() => {
    if (!isMobileOpen) return undefined

    const previouslyFocused = document.activeElement
    closeRef.current?.focus()

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsMobileOpen(false)
        return
      }

      // Keep focus inside the drawer while it is open.
      if (event.key === 'Tab' && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll(
          'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
        )
        if (!focusable.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus()
    }
  }, [isMobileOpen, setIsMobileOpen])

  return (
    <>
      <button
        type="button"
        onClick={() => setIsMobileOpen(false)}
        className={clsx(
          'lx-drawer-scrim transition-opacity duration-200 md:hidden',
          isMobileOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
        )}
        tabIndex={-1}
        aria-hidden="true"
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        aria-hidden={!isMobileOpen}
        style={{ width: DRAWER_WIDTH }}
        className={clsx(
          'lx-app-drawer transition-transform duration-300 ease-out md:hidden',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="lx-app-drawer__head">
          <span className="lx-topbar__wordmark">TRUSTRAG</span>
          <button
            ref={closeRef}
            type="button"
            onClick={() => setIsMobileOpen(false)}
            className="lx-icon-btn"
            title="Close navigation"
            aria-label="Close navigation menu"
            tabIndex={isMobileOpen ? 0 : -1}
          >
            <X size={18} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>

        <nav className="lx-app-drawer__nav" aria-label="Primary navigation">
          {NAV_GROUPS.map((group) => (
            <div key={group.id} className="lx-app-drawer__group">
              <p className="lx-app-drawer__group-label" aria-hidden="true">
                {group.label}
              </p>
              {group.items.map((item) => (
                <DrawerLink
                  key={item.to}
                  {...item}
                  onNavigate={setIsMobileOpen}
                  tabIndex={isMobileOpen ? 0 : -1}
                />
              ))}
            </div>
          ))}
        </nav>

        <div className="lx-app-drawer__foot">
          <ShieldCheck
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            className="shrink-0 text-silver-400"
          />
          <div className="min-w-0">
            <p className="lx-sidebar__status-title truncate">Reliability workbench</p>
            <p className="lx-sidebar__status-meta truncate">
              Verify before you answer
            </p>
          </div>
        </div>
      </div>
    </>
  )
}

function DrawerLink({ to, label, icon: Icon, meta, onNavigate, tabIndex }) {
  return (
    <NavLink
      to={to}
      tabIndex={tabIndex}
      onClick={() => onNavigate(false)}
      className={({ isActive }) =>
        clsx('lx-app-drawer__link', isActive && 'lx-app-drawer__link--active')
      }
    >
      <Icon
        size={17}
        strokeWidth={1.5}
        aria-hidden="true"
        focusable="false"
        className="lx-navlink__icon"
      />
      <span className="flex-1">{label}</span>
      {meta && (
        <span className="lx-navlink__meta flex items-center gap-1.5">
          <span className="lx-dot lx-dot--live" aria-hidden="true" />
          {meta}
        </span>
      )}
    </NavLink>
  )
}
