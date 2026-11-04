import { motion } from 'motion/react'
import { Layers, Database, Cpu, Brain, ShieldCheck, Sparkles } from 'lucide-react'

/**
 * PipelineArchitecture - 5-step reliability loop architecture visualization
 * Called by: DashboardPage.jsx
 */
const PIPELINE_PHASES = [
  {
    step: '01',
    title: 'Hybrid Retrieval',
    desc: 'Dense embeddings (ONNX BGE, local) + Sparse BM25 fused via Reciprocal Rank Fusion.',
    icon: Database,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
  },
  {
    step: '02',
    title: 'Grounded Reasoning',
    desc: 'Strict evidence-grounded synthesis using Local LLMs (Ollama / llama.cpp) or Cloud.',
    icon: Cpu,
    color: 'text-primary-400',
    border: 'border-primary-500/30',
  },
  {
    step: '03',
    title: 'Claim Decomposition',
    desc: 'Automated extraction of atomic, falsifiable claims from synthesized answers.',
    icon: Brain,
    color: 'text-primary-400',
    border: 'border-primary-500/30',
  },
  {
    step: '04',
    title: 'Multi-Perspective NLI',
    desc: 'Zero-temperature natural language inference verifying each claim against evidence.',
    icon: ShieldCheck,
    color: 'text-emerald-400',
    border: 'border-emerald-500/30',
  },
  {
    step: '05',
    title: 'Self-Healing Recovery',
    desc: 'Adaptive LangGraph state loop triggers query rewrite or expanded retrieval on failure.',
    icon: Sparkles,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
  },
]

export function PipelineArchitecture() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200, delay: 0.3 }}
      className="space-y-4"
    >
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Layers size={18} className="text-primary-400" />
          The TrustRAG Closed-Loop Reliability Engine
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Deterministic 5-phase pipeline preventing silent hallucinations through active verification
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {PIPELINE_PHASES.map((phase) => {
          const Icon = phase.icon
          return (
            <motion.div
              key={phase.step}
              whileHover={{ scale: 1.02 }}
              transition={{ type: 'spring', damping: 20, stiffness: 200 }}
              className={`glass-card p-4 flex flex-col justify-between border ${phase.border} hover:border-opacity-60 transition-transform duration-200`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-mono font-bold text-slate-500">{phase.step}</span>
                  <Icon className={`${phase.color} w-5 h-5`} />
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
