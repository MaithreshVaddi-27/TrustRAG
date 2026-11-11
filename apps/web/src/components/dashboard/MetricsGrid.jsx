import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { Brain, Database, Zap, ArrowRight, ShieldCheck } from 'lucide-react'
import { useReducedMotion } from 'motion/react'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

/**
 * MetricsGrid - 4 hero metric cards
 * Called by: DashboardPage.jsx (line 184-190)
 * Reads: stats, kbs, analyses, claims, conflicts from props
 */
const MetricCard = ({
  icon: Icon,
  iconBgColor,
  iconColor,
  accentColor,
  title,
  value,
  meta,
  toLink,
  springTransition,
  pressTransition,
}) => {
  const CardComponent = toLink ? motion.button : motion.div
  const isLink = !!toLink

  return (
    <CardComponent
      as={toLink ? Link : undefined}
      to={toLink}
      whileHover={{ scale: 1.015, transition: springTransition }}
      whileTap={isLink ? { scale: 0.985, transition: pressTransition } : undefined}
      className={`glass-card glass-card-hover p-5 flex flex-col justify-between group relative overflow-hidden transition-all duration-300 ${isLink ? 'cursor-pointer' : ''}`}
      style={{ minHeight: '44px', minWidth: '44px' }}
    >
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-current to-transparent opacity-0 group-hover:opacity-100 transition-opacity" style={{ '--tw-gradient-from': `var(--color-${accentColor}-500)`, '--tw-gradient-to': `var(--color-${accentColor}-500)` }} />
      <div className="flex items-center justify-between">
        <div className={`w-10 h-10 rounded-xl ${iconBgColor} border border-${accentColor}-500/20 flex items-center justify-center ${iconColor} group-hover:scale-110 transition-transform`}>
          <Icon size={18} aria-hidden="true" />
        </div>
        <div className="w-6 h-6 rounded-lg bg-surface-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 group-hover:text-white group-hover:border-slate-600 transition-all">
          <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-4">
        <p className="text-3xl font-extrabold text-white tracking-tight tabular-nums">{value}</p>
        <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
          <span className="font-medium">{title}</span>
          <span className="font-mono text-[11px]">{meta}</span>
        </div>
      </div>
    </CardComponent>
  )
}

export function MetricsGrid({ stats, kbs, analyses, claims, conflicts }) {
  const reduced = useReducedMotion()
  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        icon={Database}
        iconBgColor="bg-cyan-500/10"
        iconColor="text-cyan-400"
        accentColor="cyan"
        title="Knowledge Bases"
        value={kbs.length}
        meta={`${stats.totalDocs} docs`}
        toLink="/knowledge-bases"
        springTransition={springTransition}
        pressTransition={pressTransition}
      />

      <MetricCard
        icon={Zap}
        iconBgColor="bg-primary-500/10"
        iconColor="text-primary-400"
        accentColor="primary"
        title="Analyses Executed"
        value={analyses.length}
        meta="Evidence-linked"
        toLink="/playground"
        springTransition={springTransition}
        pressTransition={pressTransition}
      />

      <MetricCard
        icon={ShieldCheck}
        iconBgColor="bg-emerald-500/10"
        iconColor="text-emerald-400"
        accentColor="emerald"
        title="Mean Reliability"
        value={stats.avgReliabilityDisplay}
        meta="Threshold: 75%"
        springTransition={springTransition}
        pressTransition={pressTransition}
      />

      <MetricCard
        icon={Brain}
        iconBgColor="bg-primary-500/10"
        iconColor="text-primary-400"
        accentColor="primary"
        title="Claims Decomposed"
        value={stats.totalClaimsCount || claims.length}
        meta={`${stats.supportedClaims} verified${conflicts?.length ? ` · ${conflicts.length} flagged` : ''}`}
        toLink="/claims"
        springTransition={springTransition}
        pressTransition={pressTransition}
      />
    </div>
  )
}