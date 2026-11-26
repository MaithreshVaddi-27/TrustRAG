/**
 * ExplainerList — a set of definitions, not a grid of cards.
 *
 * The pages used to explain their own concepts with three equal cards, each
 * holding an icon, a title and a paragraph. That is the template default.
 * This is the specification version: ruled rows, each with a marker, a term
 * and its definition. It reads like a manual, which is what it is.
 */
export default function ExplainerList({
  title,
  icon: Icon = null,
  items = [],
  className = '',
}) {
  if (!items.length) return null

  return (
    <section className={`lx-panel-block ${className}`.trim()}>
      <div className="lx-panel-block__head">
        <h2 className="lx-panel-block__title flex items-center gap-2">
          {Icon && <Icon size={15} strokeWidth={1.5} aria-hidden="true" />}
          {title}
        </h2>
      </div>

      <dl className="lx-list">
        {items.map((item) => {
          const Marker = item.icon
          return (
            <div key={item.title} className="lx-list__item">
              <dt className="flex items-center gap-2">
                {Marker && (
                  <Marker
                    size={14}
                    strokeWidth={1.75}
                    aria-hidden="true"
                    className={
                      item.tone === 'alarm'
                        ? 'text-crimson-400'
                        : item.tone === 'quiet'
                          ? 'text-silver-500'
                          : 'text-silver-300'
                    }
                  />
                )}
                <span className="lx-list__title">{item.title}</span>
              </dt>
              <dd className="lx-body-sm mt-1.5 max-w-[68ch]">{item.body}</dd>
            </div>
          )
        })}
      </dl>
    </section>
  )
}
