import { clsx } from 'clsx'

/**
 * PageHeader — the editorial rhythm for every application screen.
 *
 * The heading carries its own weight: no eyebrow label above it, no section
 * number. A mono line of metadata sits under the title, and the actions
 * slot sits to the right.
 */
export default function PageHeader({
  eyebrow = null,
  title,
  accent = null,
  description = null,
  countLabel = null,
  actions = null,
  children = null,
  className = '',
}) {
  return (
    <header className={clsx('flex flex-wrap items-end justify-between gap-4', className)}>
      <div className="min-w-0">
        {eyebrow && <p className="lx-micro mb-2">{eyebrow}</p>}

        <h1 className="lx-h1">
          {title}
          {accent && <span className="text-silver-500"> {accent}</span>}
        </h1>

        {description && <p className="lx-body mt-3 max-w-[68ch]">{description}</p>}

        {countLabel && <p className="lx-micro mt-2">{countLabel}</p>}

        {children}
      </div>

      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  )
}
