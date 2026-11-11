import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import { X, LayoutDashboard, Zap, Database, FileSearch, Brain, GitMerge, Settings, ShieldCheck } from 'lucide-react'
import { NavLink } from 'react-router-dom'

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
 * MobileDrawer — the application navigation on small screens.
 *
 * A CSS transition rather than a JavaScript animation library: the drawer
 * slides in, closes on Escape or a tap outside, and moves focus to the
 * close button when it opens. The panel stays mounted so the exit
 * transition can play.
 */
export function MobileDrawer({ isMobileOpen, setIsMobileOpen }) {
  const closeRef = useRef(null)

  useEffect(() => {
    if (!isMobileOpen) return undefined
    closeRef.current?.focus()

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKeyDown = (event) => {
      if (event.key === 'Escape') setIsMobileOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [isMobileOpen, setIsMobileOpen])

  return (
    <>
      <button
        type="button"
        onClick={() => setIsMobileOpen(false)}
        className={clsx(
          'fixed inset-0 z-40 bg-black/70 transition-opacity duration-200 md:hidden',
          isMobileOpen
            ? 'pointer-events-auto opacity-100'
            : 'pointer-events-none opacity-0',
        )}
        tabIndex={-1}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        aria-hidden={!isMobileOpen}
        className={clsx(
          'lx-app-drawer transition-transform duration-300 md:hidden',
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
          {NAV.map((item, index) =>
            item === null ? (
              <div key={`sep-${index}`} className="lx-sidebar__sep" />
            ) : (
              <DrawerLink key={item.to} {...item} onNavigate={setIsMobileOpen} />
            ),
          )}
        </nav>

        <div className="lx-sidebar__status mt-6">
          <ShieldCheck
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            className="shrink-0 text-silver-400"
          />
          <div className="min-w-0">
            <p className="lx-sidebar__status-title truncate">Self-healing loop</p>
            <p className="lx-sidebar__status-meta truncate">StateGraph v1.0 active</p>
          </div>
        </div>
      </div>
    </>
  )
}

function DrawerLink({ to, label, icon: Icon, meta, onNavigate }) {
  return (
    <NavLink
      to={to}
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
