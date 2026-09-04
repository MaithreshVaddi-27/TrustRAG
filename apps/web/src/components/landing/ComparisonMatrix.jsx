import { useState } from 'react'
import {
  ShieldCheck, XCircle, CheckCircle2, Check,
  LayoutGrid, Table, Info
} from 'lucide-react'
import { COMPARISON_CATEGORIES, COMPARISON_ROWS } from './landingData'

export default function ComparisonMatrix() {
  const [activeCompareCategory, setActiveCompareCategory] = useState('all')
  const [compareViewMode, setCompareViewMode] = useState('cards')
  const [expandedRowIndex, setExpandedRowIndex] = useState(null)

  const filteredComparisonRows = activeCompareCategory === 'all'
    ? COMPARISON_ROWS
    : COMPARISON_ROWS.filter(r => r.category === activeCompareCategory)

  return (
    <section id="compare" className="scroll-mt-24 relative z-20 py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
          <ShieldCheck size={13} />
          <span>ARCHITECTURAL SUPERIORITY</span>
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
          Why Teams Upgrade To TrustRAG
        </h2>
        <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
          Compare standard single-pass RAG pipelines against our deterministic, closed-loop verification architecture.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 pt-4 border-t border-slate-800/80">
          <div className="flex flex-wrap items-center justify-center gap-2">
            {COMPARISON_CATEGORIES.map((cat) => {
              const isSelected = activeCompareCategory === cat.id
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCompareCategory(cat.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-950/50'
                      : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700'
                  }`}
                >
                  {cat.label}
                </button>
              )
            })}
          </div>

          <div className="inline-flex items-center p-1 rounded-xl bg-surface-900 border border-slate-800">
            <button
              onClick={() => setCompareViewMode('cards')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                compareViewMode === 'cards'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <LayoutGrid size={13} />
              <span>Side-by-Side</span>
            </button>
            <button
              onClick={() => setCompareViewMode('matrix')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                compareViewMode === 'matrix'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Table size={13} />
              <span>Matrix Table</span>
            </button>
          </div>
        </div>
      </div>

      {compareViewMode === 'cards' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
          <div className="p-7 sm:p-9 rounded-3xl bg-surface-950/90 border border-red-900/40 backdrop-blur-xl relative overflow-hidden flex flex-col justify-between group hover:border-red-800/60 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="px-3 py-1 rounded-full bg-red-950/80 border border-red-800/60 text-[11px] font-mono text-red-300 font-bold">
                  LEGACY STATUS QUO
                </span>
                <span className="text-slate-500 font-mono text-xs">Standard Naive RAG</span>
              </div>
              <h3 className="text-2xl font-extrabold text-white mb-2">Blind Single-Pass Generation</h3>
              <p className="text-slate-400 text-xs leading-relaxed mb-6">
                Standard retrieval models blindly trust retrieved chunks and assume the LLM generates 100% grounded facts. Hallucinations, stale information, and citation mismatches reach production users undetected.
              </p>

              <div className="p-3.5 rounded-xl bg-surface-900/80 border border-slate-800 font-mono text-[11px] text-slate-400 mb-6 space-y-1.5">
                <div className="text-slate-500">{'// Execution Flow (No Verification Gate)'}</div>
                <div className="text-slate-300 flex items-center gap-1.5">
                  <span>Query</span>
                  <span>&rarr;</span>
                  <span>Vector Search</span>
                  <span>&rarr;</span>
                  <span className="text-red-400 font-bold">Unverified LLM Output</span>
                  <span>&rarr;</span>
                  <span>User</span>
                </div>
              </div>

              <div className="space-y-3">
                {filteredComparisonRows.map((row, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-400">
                    <XCircle size={16} className="text-red-400/80 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-slate-300">{row.title}: </span>
                      <span>{row.naive}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-slate-900 text-center text-xs font-mono text-red-400/80">
              High legal, financial, and clinical liability risk
            </div>
          </div>

          <div className="border-beam p-7 sm:p-9 rounded-3xl bg-surface-900/90 border border-cyan-500/40 backdrop-blur-xl relative overflow-hidden flex flex-col justify-between shadow-2xl shadow-cyan-950/40">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="px-3 py-1 rounded-full bg-cyan-950/90 border border-cyan-500/60 text-[11px] font-mono text-cyan-300 font-bold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span>RECOMMENDED FOR PRODUCTION</span>
                </span>
                <span className="text-cyan-400 font-mono text-xs font-semibold">TrustRAG Platform</span>
              </div>
              <h3 className="text-2xl font-extrabold text-white mb-2">Autonomous Closed-Loop Recovery</h3>
              <p className="text-slate-300 text-xs leading-relaxed mb-6 font-normal">
                Decomposes responses into atomic claims, audits evidence citations with hybrid RRF retrieval, and triggers automated LangGraph query rewrites to self-heal low-confidence answers before they leave the server.
              </p>

              <div className="p-3.5 rounded-xl bg-surface-950 border border-cyan-800/60 font-mono text-[11px] text-cyan-300 mb-6 space-y-1.5 shadow-inner">
                <div className="text-slate-500">{'// Execution Flow (Deterministic Closed-Loop)'}</div>
                <div className="text-slate-200 flex flex-wrap items-center gap-1.5">
                  <span>Query</span>
                  <span>&rarr;</span>
                  <span>Hybrid RRF</span>
                  <span>&rarr;</span>
                  <span>NLI Audit</span>
                  <span>&rarr;</span>
                  <span className="text-cyan-400 font-bold">LangGraph Healing</span>
                  <span>&rarr;</span>
                  <span className="text-emerald-400 font-bold">Grounded Truth</span>
                </div>
              </div>

              <div className="space-y-3">
                {filteredComparisonRows.map((row, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300">
                    <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-white">{row.title}: </span>
                      <span>{row.trustrag}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-slate-800/80 text-center text-xs font-mono text-emerald-400 font-bold flex items-center justify-center gap-1.5">
              <Check size={14} />
              <span>99.4% Claim Precision &bull; Zero Hallucination Leakage</span>
            </div>
          </div>
        </div>
      )}

      {compareViewMode === 'matrix' && (
        <div className="rounded-3xl border border-slate-800 bg-surface-900/70 overflow-hidden backdrop-blur-xl shadow-2xl animate-fade-in">
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
                  <tr
                    key={idx}
                    onClick={() => setExpandedRowIndex(isExpanded ? null : idx)}
                    className="hover:bg-cyan-950/30 transition-colors duration-150 cursor-pointer group"
                  >
                    <td className="py-4 px-6 align-top">
                      <div className="font-semibold text-white group-hover:text-cyan-300 transition-colors flex items-center gap-1.5">
                        <span>{row.title}</span>
                        <Info size={12} className="text-slate-500 group-hover:text-cyan-400 transition-colors" />
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{row.subtitle}</div>
                      {isExpanded && (
                        <div className="mt-2.5 p-2 rounded bg-surface-950 border border-slate-800 text-[10px] font-mono text-cyan-300">
                          <strong>Production Impact:</strong> {row.impact}
                        </div>
                      )}
                    </td>
                    <td className="py-4 px-6 text-red-400/90 align-top">
                      <div className="flex items-start gap-1.5">
                        <XCircle size={14} className="shrink-0 mt-0.5 text-red-400" />
                        <span>{row.naive}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-slate-200 align-top bg-cyan-950/10 group-hover:bg-cyan-900/20 transition-colors">
                      <div className="flex items-start gap-1.5">
                        <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-emerald-400" />
                        <div>
                          <span className="font-medium text-white">{row.trustrag}</span>
                          <span className="inline-block mt-1 px-2 py-0.5 rounded bg-cyan-900/40 border border-cyan-700/50 text-[10px] font-mono text-cyan-300">
                            {row.tag}
                          </span>
                        </div>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div className="p-3 bg-surface-950/80 border-t border-slate-800 text-center text-[11px] text-slate-500 font-mono">
            Click any row to reveal its real-world production impact and risk profile
          </div>
        </div>
      )}
    </section>
  )
}
