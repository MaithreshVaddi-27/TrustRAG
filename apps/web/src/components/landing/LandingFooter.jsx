import { Link } from 'react-router-dom'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'
import { FOOTER } from './data/footer'

/**
 * LandingFooter — a ruled index.
 *
 * Links grouped by area, separated by hairlines, with the build identity in
 * mono at the bottom.
 */
export default function LandingFooter() {
  return (
    <footer className="lx-footer">
      <div className="lx-container">
        <div className="lx-footer__grid">
          <div className="lx-footer__brand">
            <div className="flex items-center gap-3">
              <TrustRagEmblem size={28} framed />
              <span className="lx-nav__wordmark">TRUSTRAG</span>
            </div>
            <p className="lx-footer__tagline">{FOOTER.tagline}</p>
          </div>

          {FOOTER.groups.map((group) => (
            <nav key={group.title} aria-label={group.title}>
              <p className="lx-footer__col-title">{group.title}</p>
              <ul className="lx-footer__list">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <Link to={link.to} className="lx-footer__link">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="lx-footer__bar">
          <span className="lx-micro">TrustRAG · open reliability workbench</span>

          <ul className="flex flex-wrap items-center gap-x-6 gap-y-2 list-none">
            {FOOTER.legal.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="lx-footer__link"
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          <span className="lx-micro">MIT</span>
        </div>
      </div>
    </footer>
  )
}
