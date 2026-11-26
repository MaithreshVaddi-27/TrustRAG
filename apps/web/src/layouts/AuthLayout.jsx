import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'
import VerificationSeal from '@/components/landing/VerificationSeal'

/**
 * AuthLayout — the authentication surface.
 *
 * A centred column on obsidian with one hairline card. The card borrows the
 * ledger's chrome — a mono header strip and the registration seal — so the
 * credential form reads as another record in the same instrument, not as a
 * generic sign-in card. No ambient colour wash.
 */
export default function AuthLayout({ children, title, subtitle }) {
  return (
    <main id="main-content" className="lx-auth" aria-label="Main content">
      <div className="lx-auth__column">
        <Link to="/" className="lx-auth__back">
          <ArrowLeft size={14} strokeWidth={1.5} aria-hidden="true" />
          <span>Back to overview</span>
        </Link>

        <div className="lx-auth__brand lx-enter">
          <Link to="/" aria-label="TrustRAG home">
            <TrustRagEmblem size={52} framed />
          </Link>
          <div>
            <p className="lx-auth__wordmark">TRUSTRAG</p>
            <p className="lx-auth__tagline">Reliability workbench</p>
          </div>
        </div>

        <div className="lx-auth__card lx-enter">
          {title && (
            <>
              <div className="lx-auth__card-head">
                <span className="lx-auth__card-ref">credential check</span>
                <VerificationSeal size={14} className="lx-auth__seal" />
              </div>
              <div className="lx-auth__title-block">
                {/* The page's heading is its first-level heading. Every other
                    route opens with one <h1>; the auth surface opened with an
                    <h2> and had none. */}
                <h1 className="lx-auth__title">{title}</h1>
                {subtitle && <p className="lx-auth__subtitle">{subtitle}</p>}
              </div>
            </>
          )}
          {children}
        </div>
      </div>
    </main>
  )
}
