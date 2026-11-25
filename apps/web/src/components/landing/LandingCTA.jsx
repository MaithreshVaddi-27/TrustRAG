import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { CTA } from './data/cta'

/**
 * LandingCTA — the close.
 *
 * One primary action and one secondary, nothing stacked under them.
 */
export default function LandingCTA() {
  return (
    <section className="lx-cta" aria-labelledby="cta-heading">
      <div className="lx-cta__statement">
        <h2 id="cta-heading" className="lx-display-sm lx-cta__headline">
          {CTA.headline}
        </h2>

        <p className="lx-lede lx-cta__lede">{CTA.lede}</p>
      </div>

      <div className="lx-cta__actions">
        <Link to="/register" className="lx-btn lx-btn--primary lx-btn--large">
          Start auditing
          <ArrowRight className="lx-btn__icon" size={16} strokeWidth={1.5} aria-hidden="true" />
        </Link>
        <Link to="/login" className="lx-btn lx-btn--secondary lx-btn--large">
          Sign in
        </Link>
      </div>
    </section>
  )
}
