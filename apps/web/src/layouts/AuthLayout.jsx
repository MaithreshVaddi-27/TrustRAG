import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'

/**
 * AuthLayout — the authentication surface.
 *
 * A centred column on obsidian with one hairline card. No ambient colour
 * wash: the page is quiet so the form is the only thing on it.
 */
export default function AuthLayout({ children, title, subtitle }) {
  return (
    <main id="main-content" className="lx-auth" aria-label="Main content">
      <div className="lx-auth__column">
        <Link to="/" className="lx-auth__back">
          <ArrowLeft size={14} strokeWidth={1.5} aria-hidden="true" />
          <span>Back to overview</span>
        </Link>

        <div className="lx-auth__brand">
          <Link to="/" aria-label="TrustRAG home">
            <TrustRagEmblem size={52} framed />
          </Link>
          <div>
            <p className="lx-auth__wordmark">TRUSTRAG</p>
            <p className="lx-auth__tagline">Reliability workbench</p>
          </div>
        </div>

        <div className="lx-auth__card">
          {title && (
            <div className="mb-6">
              <h2 className="lx-auth__title">{title}</h2>
              {subtitle && <p className="lx-auth__subtitle">{subtitle}</p>}
            </div>
          )}
          {children}
        </div>
      </div>
    </main>
  )
}
