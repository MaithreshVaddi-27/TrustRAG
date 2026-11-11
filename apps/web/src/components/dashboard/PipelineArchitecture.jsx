import { motion } from 'motion/react'
import { Layers, Database, Cpu, Brain, ShieldCheck, Sparkles } from 'lucide-react'
import { useReducedMotion } from 'motion/react'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }
const PRESS_TRANSITION = { duration: 0.08, ease: 'easeOut' }

/**
 * PipelineArchitecture - 5-step reliability loop architecture visualization
 * Called by: DashboardPage.jsx (line 205)
 * Public function: PipelineArchitecture
 * Reads: no external data (static PIPELINE_PHASES constant)
 * User instruction: "continue with ultra-premium polish of dashboard page applying same patterns as HeroBanner, ObservabilityBar, MetricsGrid, ReliabilityChart"
 */
const PIPELINE_PHASES = [
  {
    step: '01',
    title: 'Hybrid Retrieval',
    desc: 'Dense embeddings (ONNX BGE, local) + Sparse BM25 fused via Reciprocal Rank Fusion.',
    icon: Database,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
    bg: 'bg-cyan-500/10',
  },
  {
    step: '02',
    title: 'Grounded Reasoning',
    desc: 'Strict evidence-grounded synthesis using Local LLMs (Ollama / llama.cpp) or Cloud.',
    icon: Cpu,
    color: 'text-primary-400',
    border: 'border-primary-500/30',
    bg: 'bg-primary-500/10',
  },
  {
    step: '03',
    title: 'Claim Decomposition',
    desc: 'Automated extraction of atomic, falsifiable claims from synthesized answers.',
    icon: Brain,
    color: 'text-primary-400',
    border: 'border-primary-500/30',
    bg: 'bg-primary-500/10',
  },
  {
    step: '04',
    title: 'Multi-Perspective NLI',
    desc: 'Zero-temperature natural language inference verifying each claim against evidence.',
    icon: ShieldCheck,
    color: 'text-emerald-400',
    border: 'border-emerald-500/30',
    bg: 'bg-emerald-500/10',
  },
  {
    step: '05',
    title: 'Self-Healing Recovery',
    desc: 'Adaptive LangGraph state loop triggers query rewrite or expanded retrieval on failure.',
    icon: Sparkles,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
    bg: 'bg-cyan-500/10',
  },
]

export function PipelineArchitecture() {
  const reduced = useReducedMotion()
  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY
  const pressTransition = reduced ? { duration: 0.01 } : PRESS_TRANSITION

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="space-y-4"
    >
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Layers size={18} className="text-primary-400" aria-hidden="true" />
          The TrustRAG Closed-Loop Reliability Engine
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Deterministic 5-phase pipeline preventing silent hallucinations through active verification
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {PIPELINE_PHASES.map((phase, idx) => {
          const Icon = phase.icon
          return (
            <motion.div
              key={phase.step}
              whileHover={{ scale: 1.02, transition: springTransition }}
              whileTap={{ scale: 0.98, transition: pressTransition }}
              initial={reduced ? { opacity: 1 } : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...springTransition, delay: idx * 0.08 }}
              className={`glass-card glass-card-hover p-4 flex flex-col justify-between border ${phase.border} transition-all duration-300 relative overflow-hidden group`}
              style={{ minHeight: '44px', minWidth: '44px' }}
            >
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-current to-transparent opacity-0 group-hover:opacity-100 transition-opacity" style={{ '--tw-gradient-from': `var(--color-${phase.color.replace('text-', '').replace('-400', '-500')})`, '--tw-gradient-to': `var(--color-${phase.color.replace('text-', '').replace('-400', '-500')})` }} />
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-mono font-bold text-slate-500">{phase.step}</span>
                  <div className={`w-10 h-10 rounded-xl ${phase.bg} border ${phase.border} flex items-center justify-center ${phase.color} group-hover:scale-110 transition-transform`}>
                    <Icon className="w-5 h-5" aria-hidden="true" />
                  </div>
                </div>
                <h4 className="font-bold text-sm text-slate-200 mb-1.5">{phase.title}</h4>
                <p className="text-xs text-slate-400 leading-relaxed">{phase.desc}</p>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}
