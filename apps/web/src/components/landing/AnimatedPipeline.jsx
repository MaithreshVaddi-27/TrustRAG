import React from 'react'
import { motion } from 'motion/react'
import { Search, Zap, Brain, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { clsx } from 'clsx'

const PIPELINE_STEPS = [
  {
    id: 'query',
    label: 'User Query',
    icon: Search,
    iconColor: 'text-slate-400',
    accent: 'slate',
    description: 'Natural language question',
  },
  {
    id: 'retrieval',
    label: 'Hybrid RRF Retrieval',
    icon: Zap,
    iconColor: 'text-emerald-400',
    accent: 'emerald',
    description: 'Dense + BM25 via RRF',
    badge: 'Hybrid RRF',
    badgeColor: 'bg-cyan-950/90 border-cyan-500/40 text-cyan-300',
    details: [
      { label: 'Top-K', value: 'Candidates', color: 'text-cyan-400' },
      { label: 'RRF', value: 'Fused Rank', color: 'text-emerald-400' },
    ],
  },
  {
    id: 'nli',
    label: 'Atomic NLI Audit',
    icon: Brain,
    iconColor: 'text-amber-400',
    accent: 'amber',
    description: 'Claim decomposition + entailment',
    badge: 'NLI Audit',
    badgeColor: 'bg-emerald-950/90 border-emerald-500/40 text-emerald-300',
    details: [
      { label: '✓', value: 'Supported', color: 'text-emerald-400', bg: 'bg-emerald-950/40 border-emerald-800/60' },
      { label: '✗', value: 'Contradicted', color: 'text-red-400', bg: 'bg-red-950/40 border-red-800/60' },
      { label: '○', value: 'Neutral', color: 'text-amber-400', bg: 'bg-amber-950/40 border-amber-800/60' },
    ],
  },
  {
    id: 'healing',
    label: 'LangGraph Healing',
    icon: ShieldCheck,
    iconColor: 'text-cyan-400',
    accent: 'cyan',
    description: 'Bounded recovery DAG (≤2 attempts)',
    badge: 'Self-Heal',
    badgeColor: 'bg-primary-950/90 border-primary-500/40 text-primary-300',
    details: [
      { label: 'Rewrite', color: 'text-cyan-300', bg: 'bg-cyan-950/60 border-cyan-800/40' },
      { label: 'Re-retrieve', color: 'text-cyan-300', bg: 'bg-cyan-950/60 border-cyan-800/40' },
      { label: 'Ground', color: 'text-emerald-300', bg: 'bg-emerald-950/60 border-emerald-800/40' },
    ],
  },
  {
    id: 'output',
    label: 'Grounded Answer',
    icon: CheckCircle2,
    iconColor: 'text-emerald-300',
    accent: 'emerald',
    description: '100% citation-backed',
    badge: 'Verified Output',
    badgeColor: 'bg-emerald-950/90 border-emerald-500/60 text-emerald-300',
    details: [
      { label: 'VERIFIED', color: 'text-emerald-300', bg: 'bg-emerald-950/60 border-emerald-700/50' },
      { label: 'GROUNDED', color: 'text-cyan-300', bg: 'bg-cyan-950/60 border-cyan-700/50' },
    ],
    isFinal: true,
  },
]

const METRICS = [
  { label: 'end-to-end', value: '~114ms', color: 'text-emerald-400', dot: true },
  { label: 'claim precision', value: '99.4%', color: 'text-cyan-400', dot: false },
  { label: 'leave your network', value: '0 bytes', color: 'text-amber-400', dot: false },
]

const ACCENT_CLASSES = {
  slate: 'bg-slate-950/80 border-slate-800/60 text-slate-400',
  emerald: 'bg-emerald-950/80 border-emerald-800/60 text-emerald-400',
  amber: 'bg-amber-950/80 border-amber-800/60 text-amber-400',
  cyan: 'bg-cyan-950/80 border-cyan-800/60 text-cyan-400',
}

function PipelineStep({ step, index, isActive, reducedMotion }) {
  const iconBgClass = ACCENT_CLASSES[step.accent] || ACCENT_CLASSES.slate
  const baseClasses = clsx(
    'flex-1 min-w-[180px] p-5 rounded-2xl text-center relative group/card transition-all duration-300',
    'bg-surface-950/80 border border-slate-800/80',
    isActive && 'ring-2 ring-primary-500/50 shadow-lg shadow-primary-950/40 scale-[1.02]'
  )

  const springTransition = reducedMotion
    ? { duration: 0.01 }
    : { delay: index * 0.08, type: 'spring', damping: 28, stiffness: 220 }

  return (
    <motion.div
      className={baseClasses}
      whileHover={{ y: reducedMotion ? 0 : -4 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      style={{ outline: 'none' }}
      tabIndex={0}
    >
      {step.badge && (
        <motion.div
          className={clsx(
            'absolute -top-3 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider',
            step.badgeColor
          )}
          initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.08 + 0.15, type: 'spring', damping: 25, stiffness: 200 }}
        >
          {step.badge}
        </motion.div>
      )}

      <motion.div
        className={clsx(
          'w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3 shrink-0 border',
          iconBgClass
        )}
        whileHover={{ scale: reducedMotion ? 1 : 1.1, rotate: reducedMotion ? 0 : 3 }}
        transition={reducedMotion ? { duration: 0.01 } : { type: 'spring', stiffness: 300, damping: 25 }}
        aria-hidden="true"
      >
        <step.icon size={24} className={step.iconColor} />
      </motion.div>

      <h4 className="font-semibold text-white text-sm mb-1">{step.label}</h4>
      <p className="text-slate-500 text-xs font-mono">{step.description}</p>

      {step.details && (
        <motion.div
          className="mt-3 pt-3 border-t border-slate-800/60"
          initial={reducedMotion ? { opacity: 1 } : { opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={reducedMotion ? { duration: 0.01 } : { duration: 0.25, delay: 0.1 }}
        >
          <div className={clsx(
            'gap-2 text-center',
            step.isFinal
              ? 'flex items-center justify-center'
              : step.details.length === 2
                ? 'grid grid-cols-2'
                : 'grid grid-cols-3'
          )}>
            {step.details.map((detail, i) => (
              <motion.div
                key={i}
                className={clsx(
                  'p-2 rounded-lg text-center min-h-[44px] flex flex-col items-center justify-center',
                  step.isFinal ? 'flex-row gap-2 text-xs min-w-[100px]' : '',
                  detail.bg || 'bg-surface-900/80 border border-slate-800'
                )}
                initial={reducedMotion ? { opacity: 1 } : { opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={reducedMotion
                  ? { duration: 0.01 }
                  : { delay: index * 0.08 + 0.15 + i * 0.04, type: 'spring', stiffness: 300, damping: 25 }}
              >
                {step.isFinal ? (
                  <>
                    <span className={clsx('px-2 py-1 rounded font-mono font-bold', detail.bg)}>
                      {detail.label}
                    </span>
                  </>
                ) : (
                  <>
                    <div className={clsx('font-mono text-xs font-bold', detail.color)}>
                      {detail.label}
                    </div>
                    <div className="text-slate-500 text-[10px]">{detail.value}</div>
                  </>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

function PipelineArrow({ index, isActive, isCompleted, reducedMotion }) {
  const baseOpacity = isCompleted ? 1 : isActive ? 0.7 : 0.3

  return (
    <motion.div
      className="flex items-center justify-center text-cyan-400/60 lg:rotate-90 shrink-0 w-12"
      aria-hidden="true"
      initial={reducedMotion ? { opacity: baseOpacity, scaleX: 1 } : { opacity: 0, scaleX: 0 }}
      animate={{ opacity: baseOpacity, scaleX: 1 }}
      transition={reducedMotion
        ? { duration: 0.01 }
        : { delay: index * 0.08 + 0.12, type: 'spring', damping: 30, stiffness: 300 }}
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 12h14M12 5l7 7-7 7" />
      </svg>
    </motion.div>
  )
}

function PipelineMetric({ metric, index, reducedMotion }) {
  return (
    <motion.div
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={reducedMotion
        ? { duration: 0.01 }
        : { delay: 0.6 + index * 0.08, type: 'spring', stiffness: 300, damping: 25 }}
      className="flex items-center gap-2"
    >
      {metric.dot && (
        <motion.div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: metric.color }}
          animate={reducedMotion ? {} : { scale: [1, 1.2, 1], opacity: [1, 0.4, 1] }}
          transition={reducedMotion ? {} : { duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          aria-hidden="true"
        />
      )}
      <span className="font-mono text-xs font-bold" style={{ color: metric.color }}>{metric.value}</span>
      <span className="text-slate-500 text-[11px] font-mono">{metric.label}</span>
    </motion.div>
  )
}

export default function AnimatedPipeline({ isVisible = true }) {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const reducedMotion = !isVisible || prefersReducedMotion

  return (
    <div className="relative max-w-6xl mx-auto" role="region" aria-label="Verification pipeline visualization">
      <div className="rounded-3xl border border-slate-800/90 bg-gradient-to-b from-surface-900/80 to-surface-950/90 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        {/* Ambient glows - subtle and blended */}
        <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-cyan-500/10 blur-[120px] pointer-events-none" aria-hidden="true" />
        <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-primary-600/10 blur-[120px] pointer-events-none" aria-hidden="true" />

        <div className="relative z-10">
          <div className="flex flex-col lg:flex-row items-center gap-4 lg:gap-6">
            {PIPELINE_STEPS.map((step, index) => (
              <React.Fragment key={step.id}>
                <PipelineStep
                  step={step}
                  index={index}
                  isActive={false}
                  reducedMotion={reducedMotion}
                />
                {index < PIPELINE_STEPS.length - 1 && (
                  <PipelineArrow
                    index={index}
                    isActive={false}
                    isCompleted={true}
                    reducedMotion={reducedMotion}
                  />
                )}
              </React.Fragment>
            ))}

            {/* Latency indicator */}
            <motion.div
              className="mt-8 pt-6 border-t border-slate-800/60 flex flex-wrap items-center justify-center gap-6 text-center w-full"
              initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reducedMotion ? { duration: 0.01 } : { delay: 0.5, type: 'spring', damping: 28, stiffness: 200 }}
            >
              {METRICS.map((metric, i) => (
                <PipelineMetric key={metric.label} metric={metric} index={i} reducedMotion={reducedMotion} />
              ))}
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}