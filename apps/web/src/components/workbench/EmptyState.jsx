import { motion } from 'motion/react'
import {
  Database, Cpu, Brain,
  ShieldCheck, Sparkles, Globe,
  Terminal, CornerDownLeft, Layers
} from 'lucide-react'
import { SPRING_GENTLE } from '@/lib/motionConfig'

const PIPELINE_PREVIEW = [
  {
    step: '01',
    title: 'Hybrid Retrieval',
    tag: 'Dense + BM25',
    desc: 'Dense ONNX 384d vector similarity fused with sparse BM25 keyword rankings.',
    icon: Database,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
  },
  {
    step: '02',
    title: 'Evidence Synthesis',
    tag: 'Strict Grounding',
    desc: 'Zero-temperature local LLM generation conditioned strictly on retrieved chunks.',
    icon: Cpu,
    color: 'text-primary-400',
    border: 'border-primary-500/30',
  },
  {
    step: '03',
    title: 'Claim Extraction',
    tag: 'Subject-Predicate-Object',
    desc: 'Decomposes generated answers into atomic, falsifiable factual claims.',
    icon: Brain,
    color: 'text-primary-400',
    border: 'border-primary-500/30',
  },
  {
    step: '04',
    title: 'NLI Entailment',
    tag: 'Fact Verification',
    desc: 'Cross-checks every claim against cited evidence: Supported, Contradicted, or Neutral.',
    icon: ShieldCheck,
    color: 'text-emerald-400',
    border: 'border-emerald-500/30',
  },
  {
    step: '05',
    title: 'Closed-Loop Heal',
    tag: 'LangGraph StateGraph',
    desc: 'Triggers query rewrites and context expansions when reliability drops below 75%.',
    icon: Sparkles,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
  },
]

export function EmptyState({ enableWebSearch = false }) {
  return (
    <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-6 sm:p-10 overflow-y-auto custom-scrollbar">
      <div className="max-w-3xl w-full space-y-6">
        {/* Header telemetry badge */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={SPRING_GENTLE}
          className="text-center space-y-2.5"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-900 border border-slate-800 text-slate-300 text-xs font-mono shadow-sm">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>Interactive Verification Workbench</span>
            <span className="text-slate-600">·</span>
            <span className="text-cyan-400 font-semibold">StateGraph v1.0</span>
          </div>

          <h3 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
            Awaiting Pipeline Query
          </h3>
          <p className="text-slate-400 text-xs sm:text-sm max-w-lg mx-auto leading-relaxed">
            Enter a prompt and execute the reliability pipeline to inspect real-time claim decomposition, NLI verification, and self-healing recovery.
          </p>
        </motion.div>

        {/* 5-Phase Architecture Visual Preview */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...SPRING_GENTLE, delay: 0.1 }}
          className="space-y-2.5"
        >
          <div className="flex items-center justify-between text-xs text-slate-400 px-1 font-mono">
            <span className="flex items-center gap-1.5 font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
              <Layers size={13} className="text-cyan-400" />
              <span>Reliability Pipeline Stages</span>
            </span>
            <span className="text-[10px] text-slate-500">Autonomous Orchestration</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
            {PIPELINE_PREVIEW.map((phase) => {
              const Icon = phase.icon
              return (
                <div
                  key={phase.step}
                  className={`p-3.5 rounded-xl bg-surface-900/80 border ${phase.border} flex flex-col justify-between hover:bg-surface-850 transition-colors shadow-sm`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono font-bold text-slate-500">{phase.step}</span>
                      <Icon className={`${phase.color} w-4 h-4`} />
                    </div>
                    <div className="font-semibold text-xs text-slate-200 mb-0.5">{phase.title}</div>
                    <span className="inline-block text-[9px] font-mono text-slate-400 bg-surface-950 px-1.5 py-0.5 rounded border border-slate-800 mb-2">
                      {phase.tag}
                    </span>
                    <p className="text-[10px] text-slate-400 leading-relaxed">{phase.desc}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </motion.div>

        {/* Grounding & Developer Info Footer */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...SPRING_GENTLE, delay: 0.2 }}
          className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 rounded-xl bg-surface-900/50 border border-slate-800 text-xs text-slate-400"
        >
          <div className="flex items-center gap-2">
            <Terminal size={14} className="text-cyan-400 shrink-0" />
            <span className="text-[11px]">
              Ready to verify · Press <kbd className="px-1.5 py-0.5 rounded bg-surface-800 border border-slate-700 text-slate-200 font-mono text-[10px] inline-flex items-center gap-0.5"><CornerDownLeft size={10} /> ⌘Enter</kbd> to run
            </span>
          </div>

          {enableWebSearch && (
            <div className="flex items-center gap-1.5 text-cyan-300 font-mono text-[11px] bg-cyan-950/60 px-2 py-0.5 rounded-md border border-cyan-800/40">
              <Globe size={11} className="text-cyan-400" />
              <span>MCP Web Grounding Enabled</span>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
