import { useState } from 'react'
import {
  Terminal, Brain, RefreshCw, Play, RotateCcw,
  CheckCircle2, XCircle
} from 'lucide-react'
import { SCENARIOS } from './landingData'

export default function SimulationSandbox() {
  const [selectedScenarioKey, setSelectedScenarioKey] = useState('entailment')
  const [simStep, setSimStep] = useState(4)
  const [isSimulating, setIsSimulating] = useState(false)
  const currentScenario = SCENARIOS[selectedScenarioKey]

  const runSimulation = () => {
    if (isSimulating) return
    setIsSimulating(true)
    setSimStep(0)
    setTimeout(() => setSimStep(1), 600)
    setTimeout(() => setSimStep(2), 1400)
    setTimeout(() => setSimStep(3), 2200)
    setTimeout(() => {
      setSimStep(4)
      setIsSimulating(false)
    }, 3200)
  }

  const handleSelectScenario = (key) => {
    setSelectedScenarioKey(key)
    setSimStep(4)
    setIsSimulating(false)
  }

  return (
    <section id="simulation" className="scroll-mt-24 relative z-20 py-16 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
          <Terminal size={13} />
          <span>INTERACTIVE EXECUTION SANDBOX</span>
        </div>
        <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
          See Hallucinations Caught & Self-Healed In Real Time
        </h2>
        <p className="text-slate-400 text-sm max-w-2xl mx-auto mt-2">
          Select a core verification invariant below and trigger an audit to watch TrustRAG cross-examine claims against ground-truth evidence citations.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-2.5 mt-6">
          {Object.keys(SCENARIOS).map((key) => {
            const sc = SCENARIOS[key]
            const isSelected = selectedScenarioKey === key
            return (
              <button
                key={key}
                onClick={() => handleSelectScenario(key)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-950/40 scale-105'
                    : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700 hover:scale-102'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${isSelected ? 'bg-cyan-400 animate-pulse' : 'bg-slate-600'}`} />
                <span>{sc.label}</span>
              </button>
            )
          })}
          <button
            onClick={runSimulation}
            disabled={isSimulating}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-cyan-950/40 cursor-pointer disabled:opacity-50 hover:scale-105 active:scale-95 transition-all"
          >
            {isSimulating ? <RotateCcw size={13} className="animate-spin" /> : <Play size={13} />}
            <span>{isSimulating ? 'Executing Pipeline...' : 'Run Audit Simulation'}</span>
          </button>
        </div>
      </div>

      <div className="border-beam rounded-2xl border border-slate-800/90 bg-surface-900/90 shadow-2xl overflow-hidden backdrop-blur-xl relative">
        {isSimulating && <div className="laser-scanline" />}

        <div className="h-12 px-5 bg-surface-950/90 border-b border-slate-800/90 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2.5">
            <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
            <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
            <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
            <span className="ml-2 font-mono text-slate-400 text-[11px] hidden sm:inline">
              trustrag_engine {'//'} {currentScenario.doc} {'//'} session_audit_live
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-[11px] text-slate-400 hidden sm:inline">Latency: 114ms</span>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-700/60 text-[10px] font-mono text-emerald-300 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>{simStep >= 4 ? 'GROUNDED: 96.4%' : simStep === 3 ? 'HEALING IN PROGRESS' : 'AUDITING'}</span>
            </span>
          </div>
        </div>

        <div className="p-6 space-y-5">
          <div className="p-4 rounded-xl bg-surface-950/80 border border-slate-800/80">
            <div className="text-[11px] font-mono text-cyan-400 font-semibold mb-1 flex items-center justify-between">
              <span>USER QUERY</span>
              <span className="text-[10px] text-slate-500 font-mono">Source KB: {currentScenario.doc}</span>
            </div>
            <div className="text-sm text-slate-200 font-medium">
              &ldquo;{currentScenario.query}&rdquo;
            </div>
          </div>

          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Brain size={14} className="text-cyan-400" />
                <span>Atomic Claim Decomposition & Entailment Verdicts</span>
              </div>
              <span className="text-[11px] text-slate-500">3 Claims Audited</span>
            </div>

            <div className="grid gap-3">
              <div className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-cyan-400/60 hover:shadow-xl hover:shadow-cyan-950/40 cursor-pointer ${
                simStep >= 2
                  ? 'bg-emerald-950/20 border-emerald-800/40'
                  : 'bg-surface-950/40 border-slate-800/60 opacity-60'
              }`}>
                <div className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-emerald-200">Claim 1 (Verified Entailment):</span>
                    <span className="text-slate-300 ml-1.5">{currentScenario.claims[0].text}</span>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-mono">
                      <span className="px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-300 border border-emerald-800/40">
                        Citation: {currentScenario.claims[0].citation}
                      </span>
                      <span className="text-emerald-400 font-semibold">Confidence: {currentScenario.claims[0].confidence}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-red-500/80 hover:shadow-xl hover:shadow-red-950/50 cursor-pointer ${
                simStep >= 3
                  ? 'bg-red-950/30 border-red-800/60'
                  : 'bg-surface-950/40 border-slate-800/60 opacity-60'
              }`}>
                <div className="flex items-start gap-3">
                  <XCircle size={18} className="text-red-400 shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-red-200">Claim 2 (Hallucination Intercepted):</span>
                      <span className="px-2 py-0.5 rounded bg-red-900/70 border border-red-700 text-[10px] font-mono text-red-200 font-bold animate-pulse">
                        CONTRADICTED
                      </span>
                    </div>
                    <span className="text-slate-300 block line-through decoration-red-400/60">
                      &ldquo;{currentScenario.claims[1].text}&rdquo;
                    </span>
                    <div className="mt-2 text-[11px] font-mono text-red-300/90 bg-red-950/50 p-2 rounded-lg border border-red-900/50">
                      Warning: {currentScenario.claims[1].conflict}
                    </div>
                  </div>
                </div>
              </div>

              <div className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-cyan-400/60 hover:shadow-xl hover:shadow-cyan-950/40 cursor-pointer ${
                simStep >= 2
                  ? 'bg-emerald-950/20 border-emerald-800/40'
                  : 'bg-surface-950/40 border-slate-800/60 opacity-60'
              }`}>
                <div className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-emerald-200">Claim 3 (Verified Entailment):</span>
                    <span className="text-slate-300 ml-1.5">{currentScenario.claims[2].text}</span>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-mono">
                      <span className="px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-300 border border-emerald-800/40">
                        Citation: {currentScenario.claims[2].citation}
                      </span>
                      <span className="text-emerald-400 font-semibold">Confidence: {currentScenario.claims[2].confidence}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {simStep >= 4 && (
            <div className="p-4 rounded-xl bg-gradient-to-r from-primary-950/80 via-slate-900 to-cyan-950/80 border border-cyan-500/50 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-slide-up">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-cyan-900/60 border border-cyan-500/50 flex items-center justify-center shrink-0 mt-0.5">
                  <RefreshCw size={17} className="text-cyan-300 animate-spin-slow" />
                </div>
                <div>
                  <div className="text-xs font-bold text-white flex items-center gap-2">
                    <span>Closed-Loop Recovery Executed</span>
                    <span className="px-2 py-0.5 rounded bg-cyan-900/40 border border-cyan-700/50 text-[10px] font-mono text-cyan-300">
                      Attempt 1 / 2
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 mt-1 font-medium leading-relaxed">
                    {currentScenario.recovery.healedText}
                  </div>
                  <div className="text-[10px] font-mono text-slate-400 mt-1.5">
                    Strategy: {currentScenario.recovery.action}
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end shrink-0">
                <span className="text-[10px] font-mono text-slate-400">Post-Healing Score</span>
                <span className="text-lg font-mono font-extrabold text-cyan-300">
                  {currentScenario.recovery.finalScore}
                </span>
                <span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-700 text-[9px] font-mono text-emerald-300 font-bold">
                  VERIFIED & GROUNDED
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
