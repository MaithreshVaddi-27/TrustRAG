/**
 * SectionBand — the shared rhythm for every landing section.
 *
 * A rule at the top, a heading that carries its own weight, a lede beside
 * it on wide screens, then the content. There is no eyebrow label above the
 * heading and no section number — the heading is the label.
 */
export default function SectionBand({
  id,
  title,
  lede,
  aside = null,
  children,
  className = '',
}) {
  return (
    <section id={id} className={`lx-section lx-band ${className}`.trim()}>
      <div className="lx-container">
        <div className="lx-band__head">
          <h2 className="lx-h1">{title}</h2>
          <div>
            {lede && <p className="lx-lede lx-band__lede">{lede}</p>}
            {aside}
          </div>
        </div>
        {children}
      </div>
    </section>
  )
}
