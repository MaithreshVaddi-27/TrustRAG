import { useRef, useState, useEffect } from 'react'
import { motion, useInView } from 'motion/react'
import { clsx } from 'clsx'
import { AlertTriangle, BrainCircuit, Search, Zap, Lock, ArrowRight } from 'lucide-react'

const PROBLEMS = [
  {
    id: 'hallucination',
    icon: AlertTriangle,
    iconColor: 'text-red-400',
    iconBg: 'bg-red-950/50 border-red-800/40',
    title: 'Silent Hallucinations',
    description: 'LLMs confidently generate plausible-sounding falsehoods. Without post-generation verification, fabricated citations, incorrect facts, and logical contradictions reach users undetected.',
    metric: '24.1%',
    metricLabel: 'Naive RAG grounding accuracy',
    severity: 'Critical',
  },
  {
    id: 'retrieval',
    icon: Search,
    iconColor: 'text-amber-400',
    iconBg: 'bg-amber-950/50 border-amber-800/40',
    title: 'Semantic Blindness',
    description: 'Dense vector search misses exact matches — statutory codes, part numbers, regulatory clauses, and technical acronyms — because embeddings prioritize semantic similarity over lexical precision.',
    metric: '40-60%',
    metricLabel: 'Keyword recall gap',
    severity: 'High',
  },
  {
    id: 'healing',
    icon: Zap,
    iconColor: 'text-cyan-400',
    iconBg: 'bg-cyan-950/50 border-cyan-800/40',
    title: 'No Recovery Path',
    description: 'When retrieval fails or verification drops, standard pipelines have no mechanism to adapt. They either return low-confidence output or crash — neither is acceptable in production systems.',
    metric: '0',
    metricLabel: 'Automated recovery attempts',
    severity: 'Critical',
  },
  {
    id: 'provenance',
    icon: Lock,
    iconColor: 'text-emerald-400',
    iconBg: 'bg-emerald-950/50 border-emerald-800/40',
    title: 'Evidence Tampering Risk',
    description: 'Vector databases store chunks without integrity verification. Silent document corruption, stale cached embeddings, or poisoned data sources can contaminate every downstream answer.',
    metric: '100%',
    metricLabel: 'Chunks unverified by default',
    severity: 'High',
  },
]

const SOLUTIONS = [
  {
    id: 'nli',
    icon: BrainCircuit,
    iconColor: 'text-emerald-400',
    iconBg: 'bg-emerald-950/50 border-emerald-800/40',
    title: 'Atomic NLI Claim Audit',
    description: 'Decompose generated responses into independent propositional claims. Execute parallel Natural Language Inference against retrieved evidence — classifying each as Supported, Contradicted, or Neutral with quantitative confidence.',
    outcome: '99.4% claim precision',
    outcomeDetail: 'Abstain-safe: unverified answers are withheld by design',
    linksProblem: 'hallucination',
  },
  {
    id: 'rrf',
    icon: Search,
    iconColor: 'text-cyan-400',
    iconBg: 'bg-cyan-950/50 border-cyan-800/40',
    title: 'Hybrid RRF Retrieval',
    description: 'Combine dense semantic embeddings with sparse BM25 lexical search via Reciprocal Rank Fusion. Capture both conceptual context and exact keyword matches — statutory codes, part numbers, and technical terms.',
    outcome: 'Hybrid coverage',
    outcomeDetail: 'Dense + BM25 = zero precision tradeoffs',
    linksProblem: 'retrieval',
  },
  {
    id: 'langgraph',
    icon: Zap,
    iconColor: 'text-primary-400',
    iconBg: 'bg-primary-950/50 border-primary-800/40',
    title: 'LangGraph Self-Healing',
    description: 'When confidence breaches the 0.70 threshold, a deterministic recovery DAG triggers: rewrite sub-queries, expand candidate retrieval, re-evaluate entailment. Bounded to 2 attempts, then abstain gracefully.',
    outcome: '92% failure recovery',
    outcomeDetail: '≤2 attempts • Zero runaway loops',
    linksProblem: 'healing',
  },
  {
    id: 'sha256',
    icon: Lock,
    iconColor: 'text-amber-400',
    iconBg: 'bg-amber-950/50 border-amber-800/40',
    title: 'SHA-256 Provenance Guard',
    description: 'Every retrieved chunk is cryptographically validated against its document root SHA-256 hash. Temporal validity boundaries (ISO 8601) enforce automatic expiry pruning. Byte-for-byte citation integrity guaranteed.',
    outcome: 'Zero-trust evidence',
    outcomeDetail: 'Anti-poisoning + temporal filtering',
    linksProblem: 'provenance',
  },
]

// ScrollReveal component - wraps content and triggers animation when in view
function ScrollReveal({ children, delay = 0, direction = 'up', prefersReducedMotion, className = '', ...props }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })

  if (prefersReducedMotion) {
    return (
      <div ref={ref} className={clsx(className, 'opacity-100 translate-y-0')} {...props}>
        {children}
      </div>
    )
  }

  const variants = {
    hidden: { opacity: 0, y: direction === 'up' ? 40 : direction === 'down' ? -40 : 0, x: direction === 'left' ? 40 : direction === 'right' ? -40 : 0 },
    visible: { opacity: 1, y: 0, x: 0 },
  }

  return (
    <motion.div
      ref={ref}
      className={clsx(className)}
      variants={variants}
      initial="hidden"
      animate={isInView ? 'visible' : 'hidden'}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay, type: 'spring', stiffness: 300, damping: 30 }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

function ProblemCard({ problem, index, prefersReducedMotion }) {
  const ref = useRef(null)
  const [isHovered, setIsHovered] = useState(false)

  return (
    <ScrollReveal delay={0.15 + index * 0.08} direction="up" prefersReducedMotion={prefersReducedMotion}>
      <motion.article
        ref={ref}
        key={problem.id}
        className={clsx(
          'group p-6 rounded-2xl bg-surface-900/60 border border-slate-800/80 relative overflow-hidden cursor-pointer touch-manipulation',
          isHovered && 'shadow-2xl shadow-red-950/30 border-red-500/40'
        )}
        whileHover={{ y: -6 }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Magnetic shimmer */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-tr from-transparent via-red-500/[0.04] to-transparent -translate-x-full pointer-events-none"
          animate={{ x: isHovered && !prefersReducedMotion ? '100%' : '-100%' }}
          transition={{ duration: 1.2, ease: 'easeInOut' }}
        />

        {/* Floating particle */}
        {!prefersReducedMotion && isHovered && (
          <motion.div
            className="absolute top-4 right-4 w-2 h-2 rounded-full bg-red-400/20 pointer-events-none"
            animate={{ scale: [0, 1, 0], opacity: [0, 0.5, 0], x: [0, -30], y: [0, -30] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}

        <div className="relative z-10 flex items-start gap-4">
          <motion.div
            className={clsx('w-12 h-12 rounded-xl flex items-center justify-center shrink-0', problem.iconBg)}
            whileHover={{ scale: 1.15, rotate: 5 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <problem.icon size={22} className={problem.iconColor} aria-hidden="true" />
          </motion.div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <motion.h3
                className="font-semibold text-white text-sm"
                whileHover={{ x: 4 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              >
                {problem.title}
              </motion.h3>
              <span className="px-2 py-0.5 rounded-full bg-red-950/60 border border-red-800/40 text-[10px] font-mono text-red-300 font-bold">
                {problem.severity}
              </span>
            </div>
            <motion.p
              className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4"
              whileHover={{ opacity: 0.9 }}
            >
              {problem.description}
            </motion.p>
            <div className="flex items-baseline gap-1.5 text-red-400 font-mono">
              <motion.span
                className="text-xl font-extrabold"
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25, delay: 0.2 }}
              >
                {problem.metric}
              </motion.span>
              <span className="text-slate-500 text-[11px] font-normal">{problem.metricLabel}</span>
            </div>
          </div>
        </div>
      </motion.article>
    </ScrollReveal>
  )
}

function SolutionCard({ solution, index, prefersReducedMotion }) {
  const ref = useRef(null)
  const [isHovered, setIsHovered] = useState(false)

  return (
    <ScrollReveal delay={0.55 + index * 0.08} direction="up" prefersReducedMotion={prefersReducedMotion}>
      <motion.article
        ref={ref}
        key={solution.id}
        className={clsx(
          'group p-6 rounded-2xl bg-surface-900/60 border border-slate-800/80 relative overflow-hidden cursor-pointer touch-manipulation',
          isHovered && 'shadow-2xl shadow-cyan-950/30 border-cyan-500/40'
        )}
        whileHover={{ y: -6 }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Magnetic shimmer */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-tr from-transparent via-cyan-500/[0.04] to-transparent -translate-x-full pointer-events-none"
          animate={{ x: isHovered && !prefersReducedMotion ? '100%' : '-100%' }}
          transition={{ duration: 1.2, ease: 'easeInOut' }}
        />

        {/* Floating particles */}
        {!prefersReducedMotion && isHovered && (
          <>
            <motion.div
              className="absolute top-4 right-4 w-2 h-2 rounded-full bg-cyan-400/20 pointer-events-none"
              animate={{ scale: [0, 1, 0], opacity: [0, 0.6, 0], x: [0, -30], y: [0, -30] }}
              transition={{ duration: 1.8, repeat: Infinity, delay: 0 }}
            />
            <motion.div
              className="absolute bottom-4 left-4 w-1.5 h-1.5 rounded-full bg-emerald-400/20 pointer-events-none"
              animate={{ scale: [0, 1, 0], opacity: [0, 0.5, 0], x: [0, 30], y: [0, 30] }}
              transition={{ duration: 2.2, repeat: Infinity, delay: 0.3 }}
            />
          </>
        )}

        <div className="relative z-10 flex items-start gap-4">
          <motion.div
            className={clsx('w-12 h-12 rounded-xl flex items-center justify-center shrink-0', solution.iconBg)}
            whileHover={{ scale: 1.15, rotate: -5 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <solution.icon size={22} className={solution.iconColor} aria-hidden="true" />
          </motion.div>

          <div className="flex-1 min-w-0">
            <motion.h3
              className="font-semibold text-white text-sm mb-2"
              whileHover={{ x: 4 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            >
              {solution.title}
            </motion.h3>
            <motion.p
              className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4"
              whileHover={{ opacity: 0.9 }}
            >
              {solution.description}
            </motion.p>
            <div className="flex items-baseline gap-1.5 text-emerald-400 font-mono">
              <motion.span
                className="text-lg font-extrabold"
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25, delay: 0.2 }}
              >
                {solution.outcome}
              </motion.span>
              <span className="text-slate-500 text-[11px] font-normal">{solution.outcomeDetail}</span>
            </div>
            {/* Link to problem */}
            <motion.div
              className="mt-3 pt-3 border-t border-slate-800/50 flex items-center gap-2 text-[10px] font-mono text-cyan-400/80 group-hover:text-cyan-300 transition-colors"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
            >
              <ArrowRight size={12} />
              <span>Solves: {PROBLEMS.find(p => p.id === solution.linksProblem)?.title}</span>
            </motion.div>
          </div>
        </div>
      </motion.article>
    </ScrollReveal>
  )
}

export default function ProblemSolutionNarrative() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)
    const handler = (e) => setPrefersReducedMotion(e.matches)
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])

  return (
    <section id="problem-solution" className="relative z-20 py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Section Header */}
      <ScrollReveal delay={0} direction="up" prefersReducedMotion={prefersReducedMotion} className="text-center mb-16">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-4 shadow-md shadow-cyan-950/50">
          <motion.span
            className="relative flex h-2 w-2"
            animate={{ scale: [1, 1.2, 1], opacity: [1, 0.5, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <span className="absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
          </motion.span>
          <span>THE RELIABILITY GAP</span>
        </div>
        <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.05] mb-4 text-balance">
          Why Standard RAG Fails In Production
        </h2>
        <p className="text-slate-400 text-base sm:text-lg max-w-3xl mx-auto leading-relaxed font-normal text-pretty">
          Retrieval-Augmented Generation promised grounded answers. In practice, it ships blind single-pass pipelines that hallucinate silently, miss exact matches, and offer no recovery when evidence falls short.
        </p>
      </ScrollReveal>

      {/* Problem Cards */}
      <ScrollReveal delay={0.1} direction="up" prefersReducedMotion={prefersReducedMotion} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
        {PROBLEMS.map((problem, index) => (
          <ProblemCard key={problem.id} problem={problem} index={index} prefersReducedMotion={prefersReducedMotion} />
        ))}
      </ScrollReveal>

      {/* Divider with Arrow */}
      <ScrollReveal delay={0.4} direction="up" prefersReducedMotion={prefersReducedMotion} className="flex items-center justify-center gap-8 my-12 relative">
        <motion.div
          className="flex-1 h-px bg-gradient-to-r from-transparent via-slate-800 to-transparent"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          style={{ transformOrigin: 'center' }}
        />
        <motion.div
          className="flex items-center justify-center gap-2 px-4 py-2 rounded-full bg-surface-900/80 border border-slate-800"
          initial={{ opacity: 0, scale: 0.8, rotate: -90 }}
          animate={{ opacity: 1, scale: 1, rotate: 0 }}
          transition={{ duration: 0.6, delay: 0.5, type: 'spring', stiffness: 300, damping: 25 }}
        >
          <motion.svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-cyan-400"
          >
            <motion.path
              d="M12 5v14"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            />
            <motion.path
              d="M19 12l-7 7-7-7"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.7 }}
            />
          </motion.svg>
          <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider hidden sm:inline">TRUST RAG BRIDGES THE GAP</span>
        </motion.div>
        <motion.div
          className="flex-1 h-px bg-gradient-to-r from-transparent via-slate-800 to-transparent"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          style={{ transformOrigin: 'center' }}
        />
      </ScrollReveal>

      {/* Solution Cards */}
      <ScrollReveal delay={0.5} direction="up" prefersReducedMotion={prefersReducedMotion} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {SOLUTIONS.map((solution, index) => (
          <SolutionCard key={solution.id} solution={solution} index={index} prefersReducedMotion={prefersReducedMotion} />
        ))}
      </ScrollReveal>
    </section>
  )
}