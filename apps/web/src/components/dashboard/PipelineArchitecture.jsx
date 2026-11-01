import { motion } from 'motion/react'
import { Layers } from 'lucide-react'

/**
 * PipelineArchitecture - 5-step reliability loop architecture visualization
 * Called by: DashboardPage.jsx (line 692-724 in current implementation)
 * No existing file serves this purpose - extracted from DashboardPage
 * Reads/writes: No external data, purely presentational
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
const PIPELINE_PHASES = [
  {
    step: '01',
    title: 'Hybrid Retrieval',
    desc: 'Dense embeddings (ONNX BGE, local) + Sparse BM25 fused via Reciprocal Rank Fusion.',
    icon: 'database',
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
  },
  {
    step: '02',
    title: 'Grounded Reasoning',
    desc: 'Strict evidence-grounded synthesis using Local LLMs (Ollama / llama.cpp) or Cloud.',
    icon: 'cpu',
    color: 'text-sky-400',
    border: 'border-sky-500/30',
  },
  {
    step: '03',
    title: 'Claim Decomposition',
    desc: 'Automated extraction of atomic, falsifiable claims from synthesized answers.',
    icon: 'brain',
    color: 'text-primary-400',
    border: 'border-primary-500/30',
  },
  {
    step: '04',
    title: 'Multi-Perspective NLI',
    desc: 'Zero-temperature natural language inference verifying each claim against evidence.',
    icon: 'shield-check',
    color: 'text-emerald-400',
    border: 'border-emerald-500/30',
  },
  {
    step: '05',
    title: 'Self-Healing Recovery',
    desc: 'Adaptive LangGraph state loop triggers query rewrite or expanded retrieval on failure.',
    icon: 'sparkles',
    color: 'text-teal-400',
    border: 'border-teal-500/30',
  },
]

const ICONS = {
  database: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4',
  cpu: 'M6 7H4a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h2M6 17H4a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h2M18 7h2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-2M18 17h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-2M10 7V5a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2v2M14 7v2a2 2 0 0 1-2 2h0a2 2 0 0 1-2-2V7',
  brain: 'M12 5a3 3 0 1 0-5.996-1.65 3 3 0 0 0-3.004 5.02A3 3 0 0 0 3.34 17.34a3 3 0 0 0 3.32 2.32 3 3 0 0 0 3.34-2.32 3 3 0 0 0 3.34 2.32 3 3 0 0 0 3.004-5.02 3 3 0 0 0 5.996-1.65 3 3 0 1 0-5.996 1.65 3 3 0 0 0-3.004-5.02 3 3 0 0 0-3.34-2.32 3 3 0 0 0-3.32 2.32 3 3 0 0 0 3.32 2.32 3 3 0 0 0 3.34-2.32 3 3 0 0 0-3.34-2.32 3 3 0 0 0 3.004 5.02 3 3 0 1 0 5.996 1.65 3 3 0 0 0 3.004-5.02 3 3 0 0 0 3.34 2.32 3 3 0 0 0 3.32-2.32 3 3 0 0 0-3.32-2.32 3 3 0 0 0-3.004-5.02Z',
  'shield-check': 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
  sparkles: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
}

function PhaseIcon({ name, className }) {
  const path = ICONS[name] || ICONS.database
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={path} /></svg>
}

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
        {PIPELINE_PHASES.map((phase) => (
          <motion.div
            key={phase.step}
            whileHover={{ scale: 1.02 }}
            transition={{ type: 'spring', damping: 20, stiffness: 200 }}
            className={`glass-card p-4 flex flex-col justify-between border ${phase.border} hover:border-opacity-60 transition-transform duration-200`}
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-mono font-bold text-slate-500">{phase.step}</span>
                <PhaseIcon name={phase.icon} className={`${phase.color} w-5 h-5`} />
              </div>
              <h4 className="font-bold text-sm text-slate-200 mb-1.5">{phase.title}</h4>
              <p className="text-xs text-slate-400 leading-relaxed">{phase.desc}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}