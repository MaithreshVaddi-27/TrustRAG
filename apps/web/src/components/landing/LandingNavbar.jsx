import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'
import { NAV_LINKS } from './landingData'

/**
 * LandingNavbar — quiet chrome.
 *
 * A logo, the section links, one button. "Sign in" is a text link, not a
 * second button. The hairline under the bar appears only once the page has
 * scrolled past it.
 */
export default function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Escape closes the drawer; the page behind it must not scroll.
  useEffect(() => {
    if (!drawerOpen) return undefined
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setDrawerOpen(false)
    }
    document.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [drawerOpen])

  const closeDrawer = useCallback(() => setDrawerOpen(false), [])

  return (
    <>
      <header className="lx-nav" data-scrolled={scrolled}>
        <div className="lx-container lx-nav__inner">
          <Link to="/" className="lx-nav__brand" aria-label="TrustRAG home">
            <TrustRagEmblem size={30} framed />
            <span className="lx-nav__wordmark">TRUSTRAG</span>
          </Link>

          <nav className="lx-nav__links" aria-label="Sections">
            {NAV_LINKS.map((link) => (
              <a key={link.id} href={`#${link.id}`} className="lx-nav__link">
                {link.label}
              </a>
            ))}
          </nav>

          <div className="lx-nav__actions">
            <Link to="/login" className="lx-nav__signin">
              Sign in
            </Link>
            <Link to="/register" className="lx-btn lx-btn--primary">
              Get started
            </Link>
            <button
              type="button"
              className="lx-nav__toggle"
              aria-label={drawerOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={drawerOpen}
              onClick={() => setDrawerOpen((open) => !open)}
            >
              {drawerOpen ? (
                <X size={18} strokeWidth={1.5} aria-hidden="true" />
              ) : (
                <Menu size={18} strokeWidth={1.5} aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </header>

      {drawerOpen && (
        <div className="lx-drawer" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="lx-drawer__top">
            <span className="lx-nav__wordmark">TRUSTRAG</span>
            <button
              type="button"
              className="lx-nav__toggle"
              aria-label="Close menu"
              onClick={closeDrawer}
            >
              <X size={18} strokeWidth={1.5} aria-hidden="true" />
            </button>
          </div>

          <nav className="lx-drawer__nav" aria-label="Sections">
            {NAV_LINKS.map((link, index) => (
              <a
                key={link.id}
                href={`#${link.id}`}
                className="lx-drawer__link"
                onClick={closeDrawer}
              >
                <span>{link.label}</span>
                <span className="lx-drawer__index">
                  {String(index + 1).padStart(2, '0')}
                </span>
              </a>
            ))}
          </nav>

          <div className="lx-drawer__actions">
            <Link to="/register" className="lx-btn lx-btn--primary lx-btn--block" onClick={closeDrawer}>
              Get started
            </Link>
            <Link to="/login" className="lx-btn lx-btn--secondary lx-btn--block" onClick={closeDrawer}>
              Sign in
            </Link>
          </div>
        </div>
      )}
    </>
  )
}
