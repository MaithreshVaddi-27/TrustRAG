import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import EvidenceRecord from './EvidenceRecord'
import { HERO, HERO_RECORDS } from './landingData'

/**
 * HeroSection — the entry point.
 *
 * An asymmetric split: the copy on the left, the product on the right. The
 * right column is a real evidence record from the workbench, not an
 * illustration of one. It is the only element on the page that reads as an
 * object, and it earns the single shadow in the system.
 */
export default function HeroSection() {
  return (
    <section className="lx-hero" aria-labelledby="hero-heading">
      <div className="lx-container lx-hero__grid">
        <div className="lx-hero__copy">
          <h1 id="hero-heading" className="lx-display lx-hero__headline lx-enter">
            {HERO.headline.map((line) => (
              <span key={line} className="block">
                {line}
              </span>
            ))}
          </h1>

          <p className="lx-lede lx-hero__lede lx-enter">{HERO.lede}</p>

          <div className="lx-hero__actions lx-enter">
            <Link to="/register" className="lx-btn lx-btn--primary lx-btn--large">
              Start auditing
              <ArrowRight className="lx-btn__icon" size={16} strokeWidth={1.5} aria-hidden="true" />
            </Link>
            <a href="#simulation" className="lx-btn lx-btn--secondary lx-btn--large">
              See a verification run
            </a>
          </div>

          <p className="lx-micro lx-hero__note lx-enter">
            <span>{HERO.note.text}</span>
            <a href={HERO.note.href}>{HERO.note.linkText}</a>
          </p>
        </div>

        <div className="lx-preview lx-enter" aria-label="An example verification record">
          <div className="lx-preview__chrome">
            <span className="lx-preview__title">verification run · 4a71c2</span>
            <span className="lx-micro">
              2 claims · <span className="lx-signal">1 contradicted</span>
            </span>
          </div>

          <div className="lx-preview__body">
            {HERO_RECORDS.map((record) => (
              <EvidenceRecord key={record.index} {...record} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
