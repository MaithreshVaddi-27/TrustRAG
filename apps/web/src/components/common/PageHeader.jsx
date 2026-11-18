import { clsx } from 'clsx'

/**
 * PageHeader — the editorial rhythm for every application screen.
 *
 * The heading carries its own weight: there is no eyebrow label above it
 * and no section number. A quiet mono count sits beside the title as
 * metadata, never as a label.
 *
 * One title per screen. One primary action beside it.
 */
export default function PageHeader({
  title,
  accent = null,
  description = null,
  countLabel = null,
  actions = null,
  children = null,
  className = '',
}) {
  return (
    <header
      className={clsx(
        'flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between',
        className,
      )}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="lx-h1">
            {title}
            {accent && <span className="text-silver-500"> {accent}</span>}
          </h1>

          {countLabel && (
            <span className="lx-chip lx-chip--quiet" role="status">
              {countLabel}
            </span>
          )}
        </div>

        {description && (
          <p className="lx-body mt-3 max-w-[68ch]">{description}</p>
        )}

        {children}
      </div>

      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  )
}
