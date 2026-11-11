import { useNavigate } from 'react-router-dom'
import { useRef } from 'react'
import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import {
  ArrowRight, Zap, ShieldCheck, RefreshCw, Brain, Lock, Terminal
} from 'lucide-react'

const PIPELINE_STAGES = [
  { id: 'ingest', icon: Terminal, label: 'Ingest', desc: 'Parse & chunk documents', color: 'text-cyan-400', bg: 'bg-cyan-950/30' },
  { id: 'retrieve', icon: RefreshCw, label: 'Hybrid RRF', desc: 'Dense + BM25 retrieval', color: 'text-cyan-400', bg: 'bg-cyan-950/30' },
  { id: 'decompose', icon: Brain, label: 'Decompose', desc: 'Atomic claim extraction', color: 'text-primary-400', bg: 'bg-primary-950/30' },
  { id: 'verify', icon: ShieldCheck, label: 'NLI Audit', desc: 'Cross-encoder entailment', color: 'text-emerald-400', bg: 'bg-emerald-950/30' },
  { id: 'heal', icon: RefreshCw, label: 'Self-Heal', desc: 'LangGraph recovery loop', color: 'text-amber-400', bg: 'bg-amber-950/30' },
  { id: 'ground', icon: Lock, label: 'Grounded', desc: 'Cryptographic provenance', color: 'text-emerald-400', bg: 'bg-emerald-950/30' },
]

export default function HeroSection() {
  const navigate = useNavigate()
  const reduced = useReducedMotion()
  const containerRef = useRef(null)

  const springTransition = { type: 'spring', damping: 25, stiffness: 200 }
  const springTransitionGentle = { type: 'spring', damping: 30, stiffness: 180 }
  const pressTransition = { duration: 0.08, ease: 'easeOut' }

  const telemetryVariants = {
    hidden: { opacity: 0, scale: 0.9 },
    visible: { opacity: 1, scale: 1, transition: springTransition },
  }

  const headingVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: { opacity: 1, y: 0, transition: { ...springTransitionGentle, delay: 0.1 } },
  }

  const paragraphVariants = {
    hidden: { opacity: 0, y: 12 },
    visible: { opacity: 1, y: 0, transition: { ...springTransitionGentle, delay: 0.2 } },
  }

  const buttonVariants = {
    hidden: { opacity: 0, y: 12, scale: 0.98 },
    visible: (i) => ({ opacity: 1, y: 0, scale: 1, transition: { ...springTransitionGentle, delay: 0.3 + i * 0.08 } }),
  }

  const statVariants = {
    hidden: { opacity: 0, y: 16, scale: 0.95 },
    visible: (i) => ({ opacity: 1, y: 0, scale: 1, transition: { ...springTransitionGentle, delay: 0.4 + i * 0.06 } }),
  }

  const pipelineVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: (i) => ({ opacity: 1, y: 0, scale: 1, transition: { ...springTransitionGentle, delay: 0.5 + i * 0.08 } }),
  }

  const arrowVariants = {
    hidden: { opacity: 0, scaleX: 0 },
    visible: (i) => ({ opacity: 1, scaleX: 1, transition: { ...springTransitionGentle, delay: 0.6 + i * 0.08 } }),
  }

  return (
    <section ref={containerRef} className="relative z-20 pt-20 pb-16 sm:pt-28 sm:pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center" aria-labelledby="hero-heading">
      {/* Floating Card Left */}
      <motion.div
        className="hidden 2xl:flex absolute left-0 top-20 items-center gap-3 p-3.5 rounded-2xl glass-card-elevated border border-cyan-500/20 shadow-lift group cursor-default z-10 pointer-events-none animate-float"
        style={{ animationDelay: '0s' }}
        initial={false}
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 5, ease: 'easeInOut', repeat: Infinity }}
      >
        <motion.div
          className="w-10 h-10 rounded-xl bg-emerald-950/80 border border-emerald-500/40 flex items-center justify-center text-emerald-400"
          whileHover={{ rotate: 6, transition: springTransition }}
          aria-hidden="true"
        >
          <ShieldCheck size={20} />
        </motion.div>
        <div className="text-left font-mono">
          <div className="text-white text-xs font-bold flex items-center gap-1.5">
            <span>Entailment Guard</span>
            <motion.span
              className="w-1.5 h-1.5 rounded-full bg-emerald-400"
              animate={reduced ? false : { scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
              aria-hidden="true"
            />
          </div>
          <div className="text-emerald-400 text-[10px]">99.4% Claim Precision</div>
        </div>
      </motion.div>

      {/* Floating Card Right */}
      <motion.div
        className="hidden 2xl:flex absolute right-0 top-24 items-center gap-3 p-3.5 rounded-2xl glass-card-elevated border border-cyan-500/20 shadow-lift group cursor-default z-10 pointer-events-none animate-float"
        style={{ animationDelay: '2.5s' }}
        initial={false}
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 5, ease: 'easeInOut', repeat: Infinity, delay: 2.5 }}
      >
        <motion.div
          className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400"
          whileHover={{ rotate: 180, transition: { duration: 0.7, ease: 'easeOut' } }}
          aria-hidden="true"
        >
          <RefreshCw size={18} className="animate-spin-slow" />
        </motion.div>
        <div className="text-left font-mono">
          <div className="text-white text-xs font-bold flex items-center gap-1.5">
            <span>Self-Healing Loop</span>
            <motion.span
              className="w-1.5 h-1.5 rounded-full bg-cyan-400"
              animate={reduced ? false : { scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
              transition={{ duration: 2, ease: 'easeInOut', repeat: Infinity }}
              aria-hidden="true"
            />
          </div>
          <div className="text-cyan-400 text-[10px]">LangGraph Active</div>
        </div>
      </motion.div>

      {/* Floating Telemetry Badge */}
      <motion.div
        variants={telemetryVariants}
        initial="hidden"
        animate="visible"
        className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full glass-card border border-cyan-500/40 text-xs font-mono text-cyan-300 shadow-xl shadow-cyan-950/50 mb-8 backdrop-blur-md hover:border-cyan-400 hover:scale-105 transition-all cursor-default spring-critical"
      >
        <span className="relative flex h-2 w-2" aria-hidden="true">
          <motion.span
            className="absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"
            animate={reduced ? false : { scale: [1, 2.5], opacity: [0.75, 0] }}
            transition={{ duration: 1.5, ease: 'easeOut', repeat: Infinity }}
          />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
        </span>
        <span className="font-semibold tracking-wide">AUTONOMOUS AGENTIC RELIABILITY</span>
        <span className="text-slate-500" aria-hidden="true">|</span>
        <span className="text-slate-400">Zero Hallucination Tolerance</span>
      </motion.div>

      <motion.h1
        id="hero-heading"
        variants={headingVariants}
        initial="hidden"
        animate="visible"
        className="font-display text-display tracking-tight text-white max-w-5xl mx-auto leading-[1.08] mb-6"
      >
        Trust Every Token With{' '}
        <span className="shimmer-text">
          Closed-Loop Self-Healing RAG
        </span>
      </motion.h1>

      <motion.p
        variants={paragraphVariants}
        initial="hidden"
        animate="visible"
        className="text-slate-400 text-base sm:text-lg max-w-3xl mx-auto leading-relaxed mb-10 font-normal"
      >
        Break LLM responses into atomic claims, verify each against cited evidence with hybrid RRF retrieval, and trigger LangGraph self-healing loops when confidence drops below 70% — before hallucinations reach users.
      </motion.p>

      <motion.div
        className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
        role="group"
        aria-label="Primary actions"
      >
        <motion.button
          variants={buttonVariants}
          initial="hidden"
          animate="visible"
          custom={0}
          onClick={() => navigate('/register')}
          className="w-full sm:w-auto px-9 py-4 rounded-xl text-white font-bold text-sm shadow-2xl shadow-primary-950/80 border border-cyan-400/50 flex items-center justify-center gap-2.5 group cursor-pointer relative overflow-hidden btn-primary spring-interactive action-feedback"
          style={{
            background: 'linear-gradient(to right, var(--color-primary-600), var(--color-cyber-600))',
          }}
          whileHover={{ scale: 1.04, transition: springTransition }}
          whileTap={{ scale: 0.98, transition: pressTransition }}
        >
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 pointer-events-none"
            aria-hidden="true"
          />
          <span>Get Started Free</span>
          <motion.span
            className="group-hover:translate-x-1.5 transition-transform"
            whileHover={{ x: 4, transition: springTransition }}
            aria-hidden="true"
          >
            <ArrowRight size={16} />
          </motion.span>
        </motion.button>
        <motion.a
          variants={buttonVariants}
          initial="hidden"
          animate="visible"
          custom={1}
          href="#simulation"
          className="w-full sm:w-auto px-8 py-4 rounded-xl text-slate-300 hover:text-white font-semibold text-sm border border-slate-700/80 hover:border-cyan-400/60 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98] backdrop-blur-md shadow-lg group spring-interactive action-feedback"
          style={{
            backgroundColor: 'rgba(8, 12, 22, 0.9)',
            backdropFilter: 'blur(16px) saturate(160%)',
          }}
          whileHover={{ scale: 1.02, transition: springTransition }}
          whileTap={{ scale: 0.98, transition: pressTransition }}
        >
          <motion.span
            className="text-cyan-400 group-hover:scale-125 transition-transform"
            whileHover={{ scale: 1.25, transition: springTransition }}
            aria-hidden="true"
          >
            <Zap size={16} />
          </motion.span>
          <span>Launch Interactive Sandbox</span>
        </motion.a>
      </motion.div>

      {/* Interactive Pipeline Visualization */}
      <motion.div
        className="relative mb-16 overflow-x-auto px-2"
        role="region"
        aria-label="TrustRAG verification pipeline"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <motion.div
          className="relative flex items-center justify-center min-w-max px-4 py-8"
          initial={{ scale: 0.98 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.6, ease: 'easeOut', delay: 0.3 }}
        >
          {/* Pipeline flow path */}
          <motion.div
            className="absolute top-1/2 left-12 right-12 h-0.5 bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent -translate-y-1/2"
            initial={{ opacity: 0, scaleX: 0 }}
            animate={{ opacity: 1, scaleX: 1 }}
            transition={{ duration: 1.2, ease: 'easeOut', delay: 0.5 }}
            style={{ transformOrigin: 'center center' }}
            aria-hidden="true"
          />

          {/* Pipeline stages */}
          <div className="relative flex items-start gap-0" style={{ minWidth: '960px' }}>
            {PIPELINE_STAGES.map((stage, i) => (
              <motion.div
                key={stage.id}
                variants={pipelineVariants}
                initial="hidden"
                animate="visible"
                custom={i}
                className="relative flex flex-col items-center group cursor-pointer spring-interactive"
                whileHover={{ y: -4, transition: springTransition }}
                tabIndex={0}
                role="button"
                aria-label={`Pipeline stage: ${stage.label} - ${stage.desc}`}
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                {/* Connection arrow (except last) */}
                {i < PIPELINE_STAGES.length - 1 && (
                  <motion.div
                    variants={arrowVariants}
                    initial="hidden"
                    animate="visible"
                    custom={i}
                    className="absolute top-[62px] left-[52px] w-12 h-0.5 bg-gradient-to-r from-cyan-500/60 to-transparent flex items-center justify-end pointer-events-none"
                    style={{ zIndex: 1 }}
                    aria-hidden="true"
                  >
                    <motion.span
                      className="w-3 h-3 -translate-x-1.5 translate-y-0.5 border-2 border-r-cyan-400 border-b-cyan-400 rotate-45"
                      animate={reduced ? false : { x: [0, 4, 0] }}
                      transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
                    />
                  </motion.div>
                )}

                {/* Stage node */}
                <motion.div
                  className={`w-20 h-20 rounded-2xl border-2 flex flex-col items-center justify-center p-3 ${stage.bg} border-slate-700/60 group-hover:border-cyan-500/80 group-hover:shadow-xl group-hover:shadow-cyan-950/40 transition-all duration-300 relative`}
                  whileTap={{ scale: 0.95, transition: pressTransition }}
                >
                  <div className="relative mb-1">
                    <stage.icon size={24} className={stage.color} aria-hidden="true" />
                    {!reduced && (
                      <motion.span
                        className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-400/80"
                        animate={{ scale: [1, 1.4, 1], opacity: [0.8, 0, 0.8] }}
                        transition={{ duration: 2, ease: 'easeInOut', repeat: Infinity, delay: i * 0.2 }}
                        aria-hidden="true"
                      />
                    )}
                  </div>
                  <span className="text-xs font-semibold text-white text-center leading-tight">{stage.label}</span>
                </motion.div>

                {/* Stage description tooltip */}
                <motion.div
                  className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 px-3 py-2 rounded-lg glass-card border border-slate-700/60 text-[11px] text-slate-300 font-mono whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 group-hover:translate-y-1 transition-all duration-300 z-20"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 0, y: 8 }}
                  style={{ transformOrigin: 'center bottom' }}
                >
                  {stage.desc}
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-b-0 border-transparent border-t-slate-700" aria-hidden="true" />
                </motion.div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </motion.div>

      <motion.div
        className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto pt-6 border-t border-slate-800/80"
        role="list"
        aria-label="Key metrics"
      >
        {[
          {
            value: '99.4%',
            label: 'Claim Grounding Precision',
            color: 'text-white',
            borderColor: 'border-cyan-400/60',
            shadowColor: 'shadow-cyan-950/50',
            gradient: 'from-transparent via-cyan-400 to-transparent',
          },
          {
            value: 'Abstain-safe',
            label: 'Unverified answers withheld',
            color: 'text-emerald-400',
            borderColor: 'border-emerald-400/60',
            shadowColor: 'shadow-emerald-950/50',
            gradient: 'from-transparent via-emerald-400 to-transparent',
          },
          {
            value: '<120ms',
            label: 'Hybrid RRF Retrieval',
            color: 'text-cyan-400',
            borderColor: 'border-cyan-400/60',
            shadowColor: 'shadow-cyan-950/50',
            gradient: 'from-transparent via-cyan-400 to-transparent',
          },
          {
            value: '0 bytes',
            label: 'Leave your network (local-first)',
            color: 'text-cyan-400',
            borderColor: 'border-cyan-400/60',
            shadowColor: 'shadow-cyan-950/50',
            gradient: 'from-transparent via-cyan-400 to-transparent',
          },
        ].map((stat, i) => (
          <motion.div
            key={stat.value}
            variants={statVariants}
            initial="hidden"
            animate="visible"
            custom={i}
            className="p-5 rounded-2xl glass-card border border-slate-800/80 backdrop-blur-md hover:border-cyan-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl transition-all duration-300 group cursor-default relative overflow-hidden spring-interactive"
            whileHover={{ y: -4, boxShadow: stat.shadowColor, borderColor: stat.borderColor, transition: springTransition }}
            role="listitem"
          >
            <motion.div
              className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ background: stat.gradient }}
              aria-hidden="true"
            />
            <motion.div
              className={`text-2xl sm:text-3xl font-extrabold font-mono group-hover:scale-105 transition-transform origin-left ${stat.color}`}
              whileHover={{ scale: 1.05, transition: springTransition }}
            >
              {stat.value}
            </motion.div>
            <div className="text-xs text-slate-400 mt-1">{stat.label}</div>
          </motion.div>
        ))}
      </motion.div>
    </section>
  )
}