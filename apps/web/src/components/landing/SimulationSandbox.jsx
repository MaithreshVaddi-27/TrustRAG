import { useState, useEffect, useRef } from 'react'
import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'
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
  const timersRef = useRef([])
  const reduced = useReducedMotion()

  const springTransition = { type: 'spring', damping: 25, stiffness: 200 }
  const springTransitionGentle = { type: 'spring', damping: 30, stiffness: 180 }

  useEffect(() => () => {
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []
  }, [])

  const runSimulation = () => {
    if (isSimulating) return
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []
    setIsSimulating(true)
    setSimStep(0)
    timersRef.current = [
      setTimeout(() => setSimStep(1), 600),
      setTimeout(() => setSimStep(2), 1400),
      setTimeout(() => setSimStep(3), 2200),
      setTimeout(() => {
        setSimStep(4)
        setIsSimulating(false)
      }, 3200),
    ]
  }

  const handleSelectScenario = (key) => {
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []
    setSelectedScenarioKey(key)
    setSimStep(4)
    setIsSimulating(false)
  }

  const scenarioVariants = {
    hidden: { opacity: 0, scale: 0.95, y: 8 },
    visible: { opacity: 1, scale: 1, y: 0, transition: springTransitionGentle },
  }

  const stepVariants = {
    hidden: { opacity: 0, y: 12, scale: 0.98 },
    visible: { opacity: 1, y: 0, scale: 1, transition: springTransitionGentle },
  }

  return (
    <section id="simulation" className="scroll-mt-24 relative z-20 py-16 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8" aria-labelledby="simulation-heading">
      <motion.div
        className="text-center mb-8"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springTransitionGentle}
      >
        <motion.div
          className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full glass-card border border-cyan-500/20 text-xs font-mono text-cyan-400 mb-3 shadow-md spring-critical"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ ...springTransition, delay: 0.1 }}
        >
          <Terminal size={13} aria-hidden="true" />
          <span>INTERACTIVE EXECUTION SANDBOX</span>
        </motion.div>
        <motion.h2
          id="simulation-heading"
          className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.15 }}
        >
          See Hallucinations Caught & Self-Healed In Real Time
        </motion.h2>
        <motion.p
          className="text-slate-400 text-sm max-w-2xl mx-auto mt-2"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.2 }}
        >
          Pick a verification invariant, run the audit, and watch TrustRAG cross-examine claims against evidence in real time.
        </motion.p>

        <motion.div
          className="flex flex-wrap items-center justify-center gap-2.5 mt-6"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.25 }}
          role="group"
          aria-label="Simulation controls"
        >
          {Object.keys(SCENARIOS).map((key, i) => {
            const sc = SCENARIOS[key]
            const isSelected = selectedScenarioKey === key
            return (
              <motion.button
                key={key}
                onClick={() => handleSelectScenario(key)}
                className={`px-4 py-3 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border spring-interactive ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-950/40'
                    : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700'
                }`}
                variants={scenarioVariants}
                initial="hidden"
                animate="visible"
                custom={i}
                whileHover={{ scale: 1.05, transition: springTransition }}
                whileTap={{ scale: 0.97, transition: { duration: 0.08, ease: 'easeOut' } }}
                aria-pressed={isSelected}
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                <motion.span
                  className={`w-2 h-2 rounded-full ${isSelected ? 'bg-cyan-400' : 'bg-slate-600'}`}
                  animate={isSelected && !reduced ? { scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] } : false}
                  transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
                  aria-hidden="true"
                />
                <span>{sc.label}</span>
              </motion.button>
            )
          })}
          <motion.button
            onClick={runSimulation}
            disabled={isSimulating}
            className="px-4 py-3 rounded-xl text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-cyan-950/40 cursor-pointer disabled:opacity-50 spring-interactive action-feedback"
            style={{
              background: 'linear-gradient(to right, var(--color-primary-600), var(--color-cyber-600))',
              minWidth: '44px',
              minHeight: '44px',
            }}
            whileHover={{ scale: 1.05, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: { duration: 0.08, ease: 'easeOut' } }}
            aria-busy={isSimulating}
          >
            {isSimulating ? <RotateCcw size={13} className="animate-spin" aria-hidden="true" /> : <Play size={13} aria-hidden="true" />}
            <span>{isSimulating ? 'Executing Pipeline...' : 'Run Audit Simulation'}</span>
          </motion.button>
        </motion.div>
      </motion.div>

      <motion.div
        className="border-beam rounded-2xl border border-slate-800/90 bg-surface-900/90 shadow-2xl overflow-hidden backdrop-blur-xl relative"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springTransitionGentle, delay: 0.3 }}
      >
        {isSimulating && <div className="laser-scanline" aria-hidden="true" />}

        <motion.div
          className="h-12 px-5 bg-surface-950/90 border-b border-slate-800/90 flex items-center justify-between text-xs"
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.35 }}
        >
          <div className="flex items-center gap-2.5">
            <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" aria-hidden="true" />
            <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" aria-hidden="true" />
            <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" aria-hidden="true" />
            <span className="ml-2 font-mono text-slate-400 text-[11px] hidden sm:inline">
              trustrag_engine {'//'} {currentScenario.doc} {'//'} session_audit_live
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-[11px] text-slate-400 hidden sm:inline">Latency: 114ms</span>
            <motion.span
              className="px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-700/60 text-[10px] font-mono text-emerald-300 font-bold flex items-center gap-1"
              variants={{
                grounded: { backgroundColor: 'rgba(6, 78, 59, 0.6)', borderColor: 'rgba(16, 185, 129, 0.6)' },
                healing: { backgroundColor: 'rgba(127, 29, 29, 0.6)', borderColor: 'rgba(239, 68, 68, 0.6)' },
                auditing: { backgroundColor: 'rgba(120, 53, 15, 0.6)', borderColor: 'rgba(245, 158, 11, 0.6)' },
              }}
              animate={
                simStep >= 4 ? 'grounded'
                : simStep === 3 ? 'healing'
                : 'auditing'
              }
              transition={springTransitionGentle}
            >
              <motion.span
                className="w-1.5 h-1.5 rounded-full bg-emerald-400"
                animate={!reduced && simStep < 4 ? { scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] } : false}
                transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
                aria-hidden="true"
              />
              <span>
                {simStep >= 4 ? 'GROUNDED: 96.4%' : simStep === 3 ? 'HEALING IN PROGRESS' : 'AUDITING'}
              </span>
            </motion.span>
          </div>
        </motion.div>

        <motion.div
          className="p-6 space-y-5"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.4 }}
        >
          <motion.div
            className="p-4 rounded-xl glass-card border border-slate-800/80"
            variants={stepVariants}
            initial="hidden"
            animate="visible"
            custom={0}
          >
            <div className="text-[11px] font-mono text-cyan-400 font-semibold mb-1 flex items-center justify-between">
              <span>USER QUERY</span>
              <span className="text-[10px] text-slate-500 font-mono">Source KB: {currentScenario.doc}</span>
            </div>
            <div className="text-sm text-slate-200 font-medium">
              &ldquo;{currentScenario.query}&rdquo;
            </div>
          </motion.div>

          <motion.div
            className="space-y-3"
            variants={stepVariants}
            initial="hidden"
            animate="visible"
            custom={1}
          >
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Brain size={14} className="text-cyan-400" aria-hidden="true" />
                <span>Atomic Claim Decomposition & Entailment Verdicts</span>
              </div>
              <span className="text-[11px] text-slate-500">3 Claims Audited</span>
            </div>

            <div className="grid gap-3">
              <motion.div
                variants={stepVariants}
                initial="hidden"
                animate={simStep >= 2 ? 'visible' : 'hidden'}
                custom={0}
                className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-cyan-400/60 hover:shadow-xl hover:shadow-cyan-950/40 cursor-pointer spring-interactive ${
                  simStep >= 2
                    ? 'bg-emerald-950/20 border-emerald-800/40'
                    : 'bg-surface-950/40 border-slate-800/60 opacity-60'
                }`}
                whileHover={{ scale: 1.015, transition: springTransition }}
              >
                <div className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />
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
              </motion.div>

              <motion.div
                variants={stepVariants}
                initial="hidden"
                animate={simStep >= 3 ? 'visible' : 'hidden'}
                custom={1}
                className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-red-500/80 hover:shadow-xl hover:shadow-red-950/50 cursor-pointer spring-interactive ${
                  simStep >= 3
                    ? 'bg-red-950/30 border-red-800/60'
                    : 'bg-surface-950/40 border-slate-800/60 opacity-60'
                }`}
                whileHover={{ scale: 1.015, transition: springTransition }}
              >
                <div className="flex items-start gap-3">
                  <XCircle size={18} className="text-red-400 shrink-0 mt-0.5" aria-hidden="true" />
                  <div className="flex-1 text-xs">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-red-200">Claim 2 (Hallucination Intercepted):</span>
                      <motion.span
                        className="px-2 py-0.5 rounded bg-red-900/70 border border-red-700 text-[10px] font-mono text-red-200 font-bold"
                        animate={!reduced ? { scale: [1, 1.05, 1], opacity: [1, 0.7, 1] } : false}
                        transition={{ duration: 1, ease: 'easeInOut', repeat: Infinity }}
                      >
                        CONTRADICTED
                      </motion.span>
                    </div>
                    <span className="text-slate-300 block line-through decoration-red-400/60">
                      &ldquo;{currentScenario.claims[1].text}&rdquo;
                    </span>
                    <div className="mt-2 text-[11px] font-mono text-red-300/90 bg-red-950/50 p-2 rounded-lg border border-red-900/50">
                      Warning: {currentScenario.claims[1].conflict}
                    </div>
                  </div>
                </div>
              </motion.div>

              <motion.div
                variants={stepVariants}
                initial="hidden"
                animate={simStep >= 2 ? 'visible' : 'hidden'}
                custom={2}
                className={`p-4 rounded-xl transition-all duration-300 border hover:scale-[1.015] hover:border-cyan-400/60 hover:shadow-xl hover:shadow-cyan-950/40 cursor-pointer spring-interactive ${
                  simStep >= 2
                    ? 'bg-emerald-950/20 border-emerald-800/40'
                    : 'bg-surface-950/40 border-slate-800/60 opacity-60'
                }`}
                whileHover={{ scale: 1.015, transition: springTransition }}
              >
                <div className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />
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
              </motion.div>
            </div>
          </motion.div>

          {simStep >= 4 && (
            <motion.div
              className="p-4 rounded-xl border border-cyan-500/50 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 spring-interactive"
              style={{
                background: 'linear-gradient(to right, var(--color-primary-950), var(--color-ink-950), var(--color-cyber-950))',
              }}
              initial={{ opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={springTransitionGentle}
              whileHover={{ scale: 1.01, transition: springTransition }}
            >
              <div className="flex items-start gap-3">
                <motion.div
                  className="w-9 h-9 rounded-xl border border-cyan-500/50 flex items-center justify-center shrink-0 mt-0.5"
                  style={{ backgroundColor: 'rgba(6, 182, 212, 0.2)' }}
                  animate={!reduced ? { rotate: [0, 360] } : false}
                  transition={{ duration: 4, ease: 'linear', repeat: Infinity }}
                >
                  <RefreshCw size={17} className="text-cyan-300" aria-hidden="true" />
                </motion.div>
                <div>
                  <div className="text-xs font-bold text-white flex items-center gap-2">
                    <span>Closed-Loop Recovery Executed</span>
                    <span className="px-2 py-0.5 rounded border border-cyan-700/50 text-[10px] font-mono text-cyan-300" style={{ backgroundColor: 'rgba(6, 182, 212, 0.2)' }}>
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
                <span className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-700 text-[10px] font-mono text-emerald-300 font-bold">
                  VERIFIED & GROUNDED
                </span>
              </div>
            </motion.div>
          )}
        </motion.div>
      </motion.div>
    </section>
  )
}