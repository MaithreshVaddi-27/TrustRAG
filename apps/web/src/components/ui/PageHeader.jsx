import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'

/**
 * PageHeader — shared editorial page header (Ledger v2).
 * Kicker with hairline rule → serif title (gradient accent) →
 * supporting copy → actions. One rhythm for every app screen.
 *
 * Props:
 *   eyebrow    — kicker label (ReactNode; icon + text) or null
 *   title      — string | ReactNode
 *   accent     — word highlighted with .text-gradient (rendered inside title)
 *   description— supporting copy
 *   countLabel — mono count pill next to title (e.g. "12 Claims")
 *   actions    — right-side slot (buttons/links)
 *   children   — extra content under description (meta rows, tabs, …)
 */
export default function PageHeader({ eyebrow, title, accent, description, countLabel, actions, children }) {
  const reduced = useReducedMotion()
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5 pb-1"
    >
      <div className="space-y-2.5 min-w-0 max-w-2xl">
        {eyebrow && (
          <p className="kicker">
            <span className="inline-flex items-center gap-2">{eyebrow}</span>
          </p>
        )}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h1 className="font-display text-heading-1 text-parchment tracking-tight text-balance">
            {title}
            {accent && <span className="text-gradient"> {accent}</span>}
          </h1>
          {countLabel && (
            <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-primary-950/80 text-primary-300 border border-primary-800/60 font-mono tabular-nums">
              {countLabel}
            </span>
          )}
        </div>
        {description && <p className="text-slate-300/90 text-[15px] leading-relaxed max-w-xl">{description}</p>}
        {children}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5 shrink-0 self-start lg:self-auto">{actions}</div>}
    </motion.div>
  )
}
