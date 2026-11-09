import React from 'react'
import { motion, useSpring, useTransform } from 'motion/react'
import { Search, Zap, Brain, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { clsx } from 'clsx'
import { useState, useEffect } from 'react'

const PIPELINE_STEPS = [
  {
    id: 'query',
    label: 'User Query',
    icon: Search,
    iconColor: 'text-slate-400',
    bgColor: 'bg-surface-950/80 border-slate-800/80',
    description: 'Natural language question',
    accent: 'cyan',
  },
  {
    id: 'retrieval',
    label: 'Hybrid RRF Retrieval',
    icon: Zap,
    iconColor: 'text-emerald-400',
    bgColor: 'bg-surface-950/80 border-slate-800/80',
    description: 'Dense + BM25 via RRF',
    accent: 'emerald',
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
    bgColor: 'bg-surface-950/80 border-slate-800/80',
    description: 'Claim decomposition + entailment',
    accent: 'amber',
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
    bgColor: 'bg-surface-950/80 border-slate-800/80',
    description: 'Bounded recovery DAG (≤2 attempts)',
    accent: 'cyan',
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
    bgColor: 'bg-gradient-to-br from-cyan-950/40 to-emerald-950/40 border-cyan-500/40',
    description: '100% citation-backed',
    accent: 'emerald',
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

function PipelineStep({ step, index, progress, isActive, isCompleted }) {
  const springProgress = useSpring(progress, { stiffness: 300, damping: 30 })
  const scale = useTransform(springProgress, [0, 1], [0.9, 1])
  const opacity = useTransform(springProgress, [0, 0.3, 1], [0, 0.5, 1])

  const baseClasses = clsx(
    'flex-1 min-w-[180px] p-5 rounded-2xl text-center relative group/card transition-all duration-300',
    step.bgColor,
    isActive && 'ring-2 ring-primary-500/50 shadow-lg shadow-primary-950/40',
    isCompleted && 'shadow-xl shadow-emerald-950/30 border-emerald-500/30'
  )

  return (
    <motion.div
      className={baseClasses}
      style={{ scale, opacity }}
      whileHover={{ y: -4 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      {step.badge && (
        <motion.div
          className={clsx(
            'absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider',
            step.badgeColor
          )}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 + 0.2 }}
        >
          {step.badge}
        </motion.div>
      )}

      <motion.div
        className={clsx(
          'w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3 shrink-0',
          step.accent === 'cyan' && 'bg-cyan-950/80 border border-cyan-800/60 text-cyan-400',
          step.accent === 'emerald' && 'bg-emerald-950/80 border border-emerald-800/60 text-emerald-400',
          step.accent === 'amber' && 'bg-amber-950/80 border border-amber-800/60 text-amber-400',
          step.accent === 'primary' && 'bg-primary-950/80 border border-primary-800/60 text-primary-400'
        )}
        whileHover={{ scale: 1.1, rotate: 3 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      >
        <step.icon size={24} className={step.iconColor} aria-hidden="true" />
      </motion.div>

      <h4 className="font-semibold text-white text-sm mb-1">{step.label}</h4>
      <p className="text-slate-500 text-xs font-mono">{step.description}</p>

      {step.details && (
        <motion.div
          className="mt-3 pt-3 border-t border-slate-800/60"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: isActive || isCompleted ? 1 : 0, height: isActive || isCompleted ? 'auto' : 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
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
                  'p-2 rounded-lg text-center',
                  step.isFinal ? 'flex items-center justify-center gap-2 text-xs' : '',
                  detail.bg || 'bg-surface-900/80 border border-slate-800'
                )}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 + 0.2 + i * 0.05, type: 'spring', stiffness: 300, damping: 25 }}
              >
                {step.isFinal ? (
                  <>
                    <span className={clsx('px-2 py-1 rounded font-mono font-bold', detail.bg)}>{detail.label}</span>
                  </>
                ) : (
                  <>
                    <div className={clsx('font-mono text-xs font-bold', detail.color)}>{detail.label}</div>
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

function PipelineArrow({ progress, index }) {
  const springProgress = useSpring(progress, { stiffness: 300, damping: 30 })
  const opacity = useTransform(springProgress, [0, 0.5, 1], [0, 0.5, 1])

  return (
    <motion.div
      className="flex items-center justify-center text-cyan-400/60 lg:rotate-90 shrink-0"
      style={{ opacity }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.1 + 0.15 }}
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 12h14M12 5l7 7-7 7" />
      </svg>
    </motion.div>
  )
}

export default function AnimatedPipeline({ isVisible = true }) {
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    if (!isVisible) return
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % PIPELINE_STEPS.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [isVisible])

  return (
    <div className="relative max-w-6xl mx-auto">
      <div className="rounded-3xl border border-slate-800/90 bg-gradient-to-b from-surface-900/80 to-surface-950/90 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        {/* Ambient glows */}
        <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-cyan-500/10 blur-[120px] pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-primary-600/10 blur-[120px] pointer-events-none" />

        <div className="relative z-10">
          <div className="flex flex-col lg:flex-row items-center gap-4 lg:gap-6">
            {PIPELINE_STEPS.map((step, index) => (
              <React.Fragment key={step.id}>
                <PipelineStep
                  step={step}
                  index={index}
                  progress={activeStep >= index ? 1 : 0}
                  isActive={activeStep === index}
                  isCompleted={activeStep > index}
                />
                {index < PIPELINE_STEPS.length - 1 && (
                  <PipelineArrow progress={activeStep > index ? 1 : activeStep === index ? 0.5 : 0} index={index} />
                )}
              </React.Fragment>
            ))}

            {/* Latency indicator */}
            <motion.div
              className="mt-8 pt-6 border-t border-slate-800/60 flex flex-wrap items-center justify-center gap-6 text-center w-full"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              {METRICS.map((metric, i) => (
                <motion.div
                  key={metric.label}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.8 + i * 0.1, type: 'spring', stiffness: 300, damping: 25 }}
                  className="flex items-center gap-2"
                >
                  {metric.dot && (
                    <motion.div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: metric.color }}
                      animate={{ scale: [1, 1.2, 1], opacity: [1, 0.4, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                    />
                  )}
                  <span className="font-mono text-xs font-bold" style={{ color: metric.color }}>{metric.value}</span>
                  <span className="text-slate-500 text-[11px] font-mono">{metric.label}</span>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}