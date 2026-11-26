import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Settings, LogOut, ChevronUp } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/auth'
import { accountInitials, accountLabel } from './navigation'

/**
 * AccountMenu — the account control in the header.
 *
 * The avatar used to sign you out on click: one stray click ended the
 * session, and nothing in the header told you who you were signed in as.
 * It is now a menu — the identity is shown, Settings is one step away, and
 * signing out is an explicit item.
 *
 * Escape closes it, a click outside closes it, and focus returns to the
 * trigger.
 */
export function AccountMenu() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [isOpen, setIsOpen] = useState(false)
  const triggerRef = useRef(null)
  const panelRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return undefined

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
        triggerRef.current?.focus()
      }
    }

    const onPointerDown = (event) => {
      if (panelRef.current?.contains(event.target)) return
      if (triggerRef.current?.contains(event.target)) return
      setIsOpen(false)
    }

    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('mousedown', onPointerDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('mousedown', onPointerDown)
    }
  }, [isOpen])

  const handleSignOut = async () => {
    setIsOpen(false)
    await authService.logout()
    navigate('/login')
  }

  return (
    <div className="lx-account">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="lx-userchip__avatar"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        title={accountLabel(user)}
      >
        <span aria-hidden="true">{accountInitials(user)}</span>
        <span className="lx-sr-only">Account menu — {accountLabel(user)}</span>
      </button>

      {isOpen && (
        <div ref={panelRef} role="menu" className="lx-account__panel">
          <div className="lx-account__identity">
            <p className="lx-account__name truncate">{accountLabel(user)}</p>
            {user?.email && user.email !== accountLabel(user) && (
              <p className="lx-micro truncate">{user.email}</p>
            )}
          </div>

          <div className="lx-account__rule" />

          <Link
            to="/settings"
            role="menuitem"
            className="lx-account__item"
            onClick={() => setIsOpen(false)}
          >
            <Settings size={14} strokeWidth={1.5} aria-hidden="true" />
            <span>Settings</span>
          </Link>

          <button
            type="button"
            role="menuitem"
            onClick={handleSignOut}
            className="lx-account__item lx-account__item--alarm"
          >
            <LogOut size={14} strokeWidth={1.5} aria-hidden="true" />
            <span>Sign out</span>
          </button>

          <ChevronUp
            size={12}
            strokeWidth={1.5}
            aria-hidden="true"
            className="lx-account__caret"
          />
        </div>
      )}
    </div>
  )
}
