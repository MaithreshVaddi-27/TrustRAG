import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import {
  ShieldCheck, XCircle, CheckCircle2, Check,
  LayoutGrid, Table, Info
} from 'lucide-react'
import { COMPARISON_CATEGORIES, COMPARISON_ROWS } from './landingData'

export default function ComparisonMatrix() {
  const [activeCompareCategory, setActiveCompareCategory] = useState('all')
  const [compareViewMode, setCompareViewMode] = useState('cards')
  const [expandedRowIndex, setExpandedRowIndex] = useState(null)
  const reduced = useReducedMotion()

  const springTransition = { type: 'spring', damping: 25, stiffness: 200 }
  const springTransitionGentle = { type: 'spring', damping: 30, stiffness: 180 }
  const pressTransition = { duration: 0.08, ease: 'easeOut' }

  const filteredComparisonRows = activeCompareCategory === 'all'
    ? COMPARISON_ROWS
    : COMPARISON_ROWS.filter(r => r.category === activeCompareCategory)

  const categoryVariants = {
    hidden: { opacity: 0, scale: 0.95, y: 8 },
    visible: { opacity: 1, scale: 1, y: 0, transition: springTransitionGentle },
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 16, scale: 0.98 },
    visible: { opacity: 1, y: 0, scale: 1, transition: springTransitionGentle },
  }

  const headerVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: { opacity: 1, y: 0, transition: springTransitionGentle },
  }

  const sectionVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: { opacity: 1, y: 0, transition: springTransitionGentle },
    exit: { opacity: 0, y: -16, transition: { duration: 0.15, ease: 'easeInOut' } },
  }

  return (
    <section id="compare" className="scroll-mt-24 relative z-20 py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8" aria-labelledby="compare-heading">
      <motion.div
        className="text-center mb-10"
        variants={headerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div
          className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full glass-card border border-cyan-500/20 text-xs font-mono text-cyan-400 mb-3 shadow-md spring-critical"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ ...springTransition, delay: 0.1 }}
        >
          <ShieldCheck size={13} aria-hidden="true" />
          <span>ARCHITECTURAL SUPERIORITY</span>
        </motion.div>
        <motion.h2
          id="compare-heading"
          className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.15 }}
        >
          Why Teams Upgrade To TrustRAG
        </motion.h2>
        <motion.p
          className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.2 }}
        >
          Compare standard single-pass RAG against our deterministic, closed-loop verification architecture.
        </motion.p>

        <motion.div
          className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 pt-4 border-t border-slate-800/80"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.25 }}
        >
          <motion.div
            className="flex flex-wrap items-center justify-center gap-2"
            role="group"
            aria-label="Comparison categories"
          >
            {COMPARISON_CATEGORIES.map((cat, i) => {
              const isSelected = activeCompareCategory === cat.id
              return (
                <motion.button
                  key={cat.id}
                  onClick={() => setActiveCompareCategory(cat.id)}
                  className={`px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer border spring-interactive ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-950/50'
                      : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700'
                  }`}
                  variants={categoryVariants}
                  initial="hidden"
                  animate="visible"
                  custom={i}
                  whileHover={{ scale: 1.05, transition: springTransition }}
                  whileTap={{ scale: 0.97, transition: pressTransition }}
                  aria-pressed={isSelected}
                  style={{ minWidth: '44px', minHeight: '44px' }}
                >
                  {cat.label}
                </motion.button>
              )
            })}
          </motion.div>

          <motion.div
            className="inline-flex items-center p-1 rounded-xl glass-card border border-slate-800/80 spring-interactive"
            role="group"
            aria-label="View mode"
          >
            <motion.button
              onClick={() => setCompareViewMode('cards')}
              className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer spring-interactive ${
                compareViewMode === 'cards'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
              whileHover={{ scale: 1.05, transition: springTransition }}
              whileTap={{ scale: 0.97, transition: pressTransition }}
              aria-pressed={compareViewMode === 'cards'}
              style={{ minWidth: '44px', minHeight: '44px' }}
            >
              <LayoutGrid size={13} aria-hidden="true" />
              <span>Side-by-Side</span>
            </motion.button>
            <motion.button
              onClick={() => setCompareViewMode('matrix')}
              className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer spring-interactive ${
                compareViewMode === 'matrix'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
              whileHover={{ scale: 1.05, transition: springTransition }}
              whileTap={{ scale: 0.97, transition: pressTransition }}
              aria-pressed={compareViewMode === 'matrix'}
              style={{ minWidth: '44px', minHeight: '44px' }}
            >
              <Table size={13} aria-hidden="true" />
              <span>Matrix Table</span>
            </motion.button>
          </motion.div>
        </motion.div>
      </motion.div>

      <AnimatePresence mode="wait">
        <motion.div
          key={compareViewMode}
          variants={sectionVariants}
          initial="hidden"
          animate="visible"
          exit="hidden"
          transition={{ duration: 0.2, ease: 'easeInOut' }}
        >
          {compareViewMode === 'cards' && (
          <motion.div
            className="grid grid-cols-1 lg:grid-cols-2 gap-8"
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            custom={0}
          >
            <motion.div
              className="p-7 sm:p-9 rounded-3xl bg-surface-950/90 border border-red-900/40 backdrop-blur-xl relative overflow-hidden flex flex-col justify-between group hover:border-red-800/60 transition-colors spring-interactive"
              whileHover={{ scale: 1.01, transition: springTransition }}
            >
              <div>
                <motion.div
                  className="flex items-center justify-between mb-4"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.35 }}
                >
                  <span className="px-3 py-1 rounded-full bg-red-950/80 border border-red-800/60 text-[11px] font-mono text-red-300 font-bold">
                    LEGACY STATUS QUO
                  </span>
                  <span className="text-slate-500 font-mono text-xs">Standard Naive RAG</span>
                </motion.div>
                <motion.h3
                  className="text-2xl font-extrabold text-white mb-2"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.4 }}
                >
                  Blind Single-Pass Generation
                </motion.h3>
                <motion.p
                  className="text-slate-400 text-xs leading-relaxed mb-6"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.45 }}
                >
                  Standard retrieval models blindly trust retrieved chunks and assume the LLM generates 100% grounded facts. Hallucinations, stale information, and citation mismatches reach production users undetected.
                </motion.p>

                <motion.div
                  className="p-3.5 rounded-xl bg-surface-900/80 border border-slate-800 font-mono text-[11px] text-slate-400 mb-6 space-y-1.5"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.5 }}
                >
                  <div className="text-slate-500">{'// Execution Flow (No Verification Gate)'}</div>
                  <motion.div
                    className="text-slate-300 flex items-center gap-1.5"
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ ...springTransitionGentle, delay: 0.55 }}
                  >
                    <span>Query</span>
                    <span>&rarr;</span>
                    <span>Vector Search</span>
                    <span>&rarr;</span>
                    <span className="text-red-400 font-bold">Unverified LLM Output</span>
                    <span>&rarr;</span>
                    <span>User</span>
                  </motion.div>
                </motion.div>

                <motion.div
                  className="space-y-3"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.55 }}
                >
                  {filteredComparisonRows.map((row, idx) => (
                    <motion.div
                      key={idx}
                      className="flex items-start gap-2.5 text-xs text-slate-400"
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ ...springTransitionGentle, delay: 0.6 + idx * 0.05 }}
                    >
                      <XCircle size={16} className="text-red-400/80 shrink-0 mt-0.5" aria-hidden="true" />
                      <div>
                        <span className="font-semibold text-slate-300">{row.title}: </span>
                        <span>{row.naive}</span>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              </div>

              <motion.div
                className="mt-8 pt-4 border-t border-slate-900 text-center text-xs font-mono text-red-400/80"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springTransitionGentle, delay: 0.8 }}
              >
                High-stakes domains where a wrong answer has real consequences
              </motion.div>
            </motion.div>

            <motion.div
              className="border-beam p-7 sm:p-9 rounded-3xl bg-surface-900/90 border border-cyan-500/40 backdrop-blur-xl relative overflow-hidden flex flex-col justify-between shadow-2xl shadow-cyan-950/40 spring-interactive"
              whileHover={{ scale: 1.01, transition: springTransition }}
            >
              <div>
                <motion.div
                  className="flex items-center justify-between mb-4"
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.35 }}
                >
                  <motion.span
                    className="px-3 py-1 rounded-full bg-cyan-950/90 border border-cyan-500/60 text-[11px] font-mono text-cyan-300 font-bold flex items-center gap-1.5 spring-critical"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ ...springTransition, delay: 0.4 }}
                  >
                    <motion.span
                      className="w-2 h-2 rounded-full bg-cyan-400"
                      animate={!reduced ? { scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] } : false}
                      transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
                      aria-hidden="true"
                    />
                    <span>RECOMMENDED FOR PRODUCTION</span>
                  </motion.span>
                  <span className="text-cyan-400 font-mono text-xs font-semibold">TrustRAG Platform</span>
                </motion.div>
                <motion.h3
                  className="text-2xl font-extrabold text-white mb-2"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.4 }}
                >
                  Autonomous Closed-Loop Recovery
                </motion.h3>
                <motion.p
                  className="text-slate-300 text-xs leading-relaxed mb-6 font-normal"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.45 }}
                >
                  Decomposes responses into atomic claims, audits evidence citations with hybrid RRF retrieval, and triggers automated LangGraph query rewrites to self-heal low-confidence answers before they leave the server.
                </motion.p>

                <motion.div
                  className="p-3.5 rounded-xl bg-surface-950 border border-cyan-800/60 font-mono text-[11px] text-cyan-300 mb-6 space-y-1.5 shadow-inner"
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.5 }}
                >
                  <div className="text-slate-500">{'// Execution Flow (Deterministic Closed-Loop)'}</div>
                  <motion.div
                    className="text-slate-200 flex flex-wrap items-center gap-1.5"
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ ...springTransitionGentle, delay: 0.55 }}
                  >
                    <span>Query</span>
                    <span>&rarr;</span>
                    <span>Hybrid RRF</span>
                    <span>&rarr;</span>
                    <span>NLI Audit</span>
                    <span>&rarr;</span>
                    <span className="text-cyan-400 font-bold">LangGraph Healing</span>
                    <span>&rarr;</span>
                    <span className="text-emerald-400 font-bold">Grounded Truth</span>
                  </motion.div>
                </motion.div>

                <motion.div
                  className="space-y-3"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.55 }}
                >
                  {filteredComparisonRows.map((row, idx) => (
                    <motion.div
                      key={idx}
                      className="flex items-start gap-2.5 text-xs text-slate-300"
                      initial={{ opacity: 0, x: 12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ ...springTransitionGentle, delay: 0.6 + idx * 0.05 }}
                    >
                      <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />
                      <div>
                        <span className="font-semibold text-white">{row.title}: </span>
                        <span>{row.trustrag}</span>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              </div>

              <motion.div
                className="mt-8 pt-4 border-t border-slate-800/80 text-center text-xs font-mono text-emerald-400 font-bold flex items-center justify-center gap-1.5"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springTransitionGentle, delay: 0.8 }}
              >
                <Check size={14} aria-hidden="true" />
                <span>99.4% Claim Precision &bull; Abstain-safe by design</span>
              </motion.div>
            </motion.div>
          </motion.div>
        )}

        {compareViewMode === 'matrix' && (
          <motion.div
            className="rounded-3xl border border-slate-800 bg-surface-900/70 overflow-hidden backdrop-blur-xl shadow-2xl spring-interactive"
            variants={sectionVariants}
            initial="hidden"
            animate="visible"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-surface-950 text-slate-400 uppercase font-mono text-[11px]">
                    <th className="py-4 px-6">Capability & Dimension</th>
                    <th className="py-4 px-6 text-slate-500">Standard Blind RAG</th>
                    <th className="py-4 px-6 text-cyan-400 font-bold bg-cyan-950/20">TrustRAG Platform</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {filteredComparisonRows.map((row, idx) => {
                    const isExpanded = expandedRowIndex === idx
                    return (
                      <motion.tr
                        key={idx}
                        onClick={() => setExpandedRowIndex(isExpanded ? null : idx)}
                        onKeyDown={e => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setExpandedRowIndex(isExpanded ? null : idx)
                          }
                        }}
                        tabIndex={0}
                        role="button"
                        aria-expanded={isExpanded}
                        className="hover:bg-cyan-950/30 transition-colors duration-150 cursor-pointer group spring-interactive"
                        whileHover={{ backgroundColor: 'rgba(6, 182, 212, 0.1)', transition: springTransition }}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ ...springTransitionGentle, delay: 0.4 + idx * 0.03 }}
                      >
                        <td className="py-4 px-6 align-top">
                          <div className="font-semibold text-white group-hover:text-cyan-300 transition-colors flex items-center gap-1.5">
                            <span>{row.title}</span>
                            <Info size={12} className="text-slate-500 group-hover:text-cyan-400 transition-colors" aria-hidden="true" />
                          </div>
                          <div className="text-[11px] text-slate-500 mt-0.5">{row.subtitle}</div>
                          {isExpanded && (
                            <motion.div
                              className="mt-2.5 p-2 rounded bg-surface-950 border border-slate-800 text-[10px] font-mono text-cyan-300"
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              transition={{ ...springTransitionGentle, delay: 0.1 }}
                            >
                              <strong>Production Impact:</strong> {row.impact}
                            </motion.div>
                          )}
                        </td>
                        <td className="py-4 px-6 text-red-400/90 align-top">
                          <div className="flex items-start gap-1.5">
                            <XCircle size={14} className="shrink-0 mt-0.5 text-red-400" aria-hidden="true" />
                            <span>{row.naive}</span>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-slate-200 align-top bg-cyan-950/10 group-hover:bg-cyan-900/20 transition-colors">
                          <div className="flex items-start gap-1.5">
                            <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-emerald-400" aria-hidden="true" />
                            <div>
                              <span className="font-medium text-white">{row.trustrag}</span>
                              <span className="inline-block mt-1 px-2 py-0.5 rounded bg-cyan-900/40 border border-cyan-700/50 text-[10px] font-mono text-cyan-300">
                                {row.tag}
                              </span>
                            </div>
                          </div>
                        </td>
                      </motion.tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <motion.div
              className="p-3 bg-surface-950/80 border-t border-slate-800 text-center text-[11px] text-slate-500 font-mono"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...springTransitionGentle, delay: 0.6 }}
            >
              Click any row to reveal its real-world production impact and risk profile
            </motion.div>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
    </section>
  )
}
