import {
  RefreshCw, Brain, Lock, Terminal, Cpu
} from 'lucide-react'
import { motion } from 'motion/react'
import { clsx } from 'clsx'

const HEALING_STEPS = [
  { id: 'ingest', label: 'Ingest', accent: 'slate' },
  { id: 'rrf', label: 'RRF Hybrid', accent: 'emerald' },
  { id: 'nli', label: 'NLI Audit', accent: 'amber' },
  { id: 'diagnose', label: 'Diagnose', accent: 'cyan', highlight: true },
  { id: 'ground', label: 'Ground', accent: 'emerald', final: true },
]

const ACCENT_CLASSES = {
  slate: 'bg-slate-950/80 border-slate-800/60 text-slate-400',
  emerald: 'bg-emerald-950/80 border-emerald-800/60 text-emerald-400',
  amber: 'bg-amber-950/80 border-amber-800/60 text-amber-400',
  cyan: 'bg-cyan-950/80 border-cyan-800/60 text-cyan-400',
}

function BentoPipelineStep({ step, index, reducedMotion }) {
  const accentClass = ACCENT_CLASSES[step.accent] || ACCENT_CLASSES.slate

  return (
    <motion.div
      className="flex flex-col items-center gap-1.5"
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reducedMotion ? { duration: 0.01 } : { delay: index * 0.06, type: 'spring', damping: 28, stiffness: 220 }}
    >
      <div className={clsx(
        'w-8 h-8 rounded-xl flex items-center justify-center border text-xs font-mono font-medium transition-all duration-300',
        accentClass,
        step.highlight && 'ring-2 ring-cyan-500/50 shadow-lg shadow-cyan-950/40',
        step.final && 'ring-2 ring-emerald-500/50 shadow-lg shadow-emerald-950/40'
      )}>
        {step.label}
      </div>
      {index < HEALING_STEPS.length - 1 && (
        <motion.div
          className="w-px h-4 bg-slate-800/60"
          initial={reducedMotion ? { opacity: 1, scaleY: 1 } : { opacity: 0, scaleY: 0 }}
          animate={{ opacity: 1, scaleY: 1 }}
          transition={reducedMotion ? { duration: 0.01 } : { delay: index * 0.06 + 0.1, type: 'spring', damping: 30, stiffness: 300 }}
        />
      )}
    </motion.div>
  )
}

export default function BentoArchitecture() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const reducedMotion = prefersReducedMotion

  return (
    <section id="bento" className="scroll-mt-24 relative z-20 py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-16">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3">
          <Cpu size={13} />
          <span>STATE-OF-THE-ART ARCHITECTURE</span>
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
          Six Layers Of Rigorous AI Reliability
        </h2>
        <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
          Built for applications where a hallucinated answer has real consequences — legal, financial, clinical, technical.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Wide 2 cols - LangGraph Healing Loop */}
        <div className="md:col-span-2 p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
          <div className="flex items-center justify-between mb-6">
            <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
              <RefreshCw size={22} />
            </div>
            <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
              LangGraph State Machine
            </span>
          </div>
          <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Autonomous LangGraph Healing Loop</h3>
          <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-6">
            When evidence coverage or contradiction rates breach safety boundaries, TrustRAG does not silently fail. It adaptively rewrites sub-queries, doubles candidate vector density, and cross-examines evidence until 100% groundability is reached.
          </p>

          {/* Redesigned Pipeline Visualization */}
          <div className="pt-4 border-t border-slate-800/80">
            <div className="flex items-center justify-between gap-2 mb-3">
              <span className="text-xs font-mono text-slate-500">Execution Trace</span>
              <span className="text-xs font-mono text-emerald-400">5 stages · ≤2 recovery loops</span>
            </div>
            <div className="flex items-center justify-center gap-1 overflow-x-auto pb-2">
              {HEALING_STEPS.map((step, index) => (
                <BentoPipelineStep key={step.id} step={step} index={index} reducedMotion={reducedMotion} />
              ))}
            </div>
            <div className="flex items-center justify-center gap-4 text-[10px] font-mono pt-3 border-t border-slate-800/60">
              <span className={clsx('px-2 py-1 rounded bg-slate-950 border border-slate-800', 'text-slate-400')}>1. Ingest</span>
              <span className={clsx('px-2 py-1 rounded bg-slate-950 border border-slate-800', 'text-emerald-400')}>2. RRF Hybrid</span>
              <span className={clsx('px-2 py-1 rounded bg-slate-950 border border-slate-800', 'text-amber-400')}>3. NLI Audit</span>
              <span className={clsx('px-2 py-1 rounded bg-cyan-950/60 border border-cyan-800/60', 'text-cyan-300 font-bold')}>4. Diagnose</span>
              <span className={clsx('px-2 py-1 rounded bg-emerald-950/60 border border-emerald-700/60', 'text-emerald-300 font-bold')}>5. Ground</span>
            </div>
          </div>
        </div>

        {/* 1 col - Atomic Claim Decomposition */}
        <div className="p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
          <div className="flex items-center justify-between mb-6">
            <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
              <Brain size={22} />
            </div>
            <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
              Pydantic Batch NLI
            </span>
          </div>
          <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Atomic Claim Decomposition</h3>
          <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4">
            Answers are broken down into granular factual propositions, verified against citations in parallel schemas without sequential API rate-limit bottlenecks.
          </p>
          <div className="p-3 rounded-xl bg-surface-950 border border-slate-800/80 font-mono text-[10px] text-slate-400 group-hover:border-slate-700 transition-colors">
            <span className="text-emerald-400 font-bold">Entailment:</span> 98.2%<br />
            <span className="text-red-400 font-bold">Contradiction:</span> Pruned<br />
            <span className="text-amber-400 font-bold">Neutral:</span> Flagged
          </div>
        </div>

        {/* 1 col - SHA-256 Provenance */}
        <div className="p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
          <div className="flex items-center justify-between mb-6">
            <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
              <Lock size={22} />
            </div>
            <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
              Cryptographic Guard
            </span>
          </div>
          <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">SHA-256 Provenance & Temporal Filter</h3>
          <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4">
            Retrieval chunks are checked against root SHA-256 checksums to detect silent tampering. Outdated documents with expired effective dates are discarded automatically.
          </p>
          <div className="p-2.5 rounded-xl bg-surface-950 border border-slate-800 font-mono text-[10px] text-emerald-400 truncate group-hover:border-slate-700 transition-colors">
            sha256: 4f8b2c91a7... [VALID]
          </div>
        </div>

        {/* Wide 2 cols - MCP Ready */}
        <div className="md:col-span-2 p-8 rounded-3xl bg-surface-900/60 border border-slate-800/80 hover:border-cyan-400/60 hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-cyan-950/40 transition-all duration-300 group relative overflow-hidden backdrop-blur-xl cursor-default">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full group-hover:translate-x-full duration-1000 transition-transform pointer-events-none" />
          <div className="flex items-center justify-between mb-6">
            <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-110 group-hover:rotate-6 group-hover:border-cyan-400/80 group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300">
              <Terminal size={22} />
            </div>
            <span className="px-2.5 py-1 rounded-full bg-surface-850 border border-slate-700/60 text-[11px] font-mono text-slate-400 group-hover:border-cyan-500/40 group-hover:text-cyan-300 transition-colors">
              Open Standard Protocol
            </span>
          </div>
          <h3 className="text-xl font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">Model Context Protocol (MCP) Ready</h3>
          <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-4">
            Exposes TrustRAG as standardized MCP tools (<code className="text-cyan-300 font-mono text-xs">trustrag_search</code>, <code className="text-cyan-300 font-mono text-xs">trustrag_verify_claim</code>). Connect Claude Desktop, Cursor, or your internal agent teams via standard JSON-RPC over stdio.
          </p>
          <div className="p-4 rounded-xl bg-surface-950 border border-slate-800 font-mono text-xs text-slate-300 space-y-1 overflow-x-auto group-hover:border-cyan-800/60 transition-colors">
            <div className="text-slate-500">{'// Terminal: Connect external agent via MCP stdio'}</div>
            <div className="text-cyan-400">$ python -m app.mcp.server</div>
            <div className="text-emerald-400">TrustRAG MCP Server listening on stdio (3 tools registered)</div>
          </div>
        </div>
      </div>
    </section>
  )
}