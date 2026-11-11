import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import {
  Cpu, Activity, Check
} from 'lucide-react'
import { CAPABILITIES } from './landingData'

const springTransition = { type: 'spring', damping: 25, stiffness: 200 }
const springTransitionGentle = { type: 'spring', damping: 30, stiffness: 180 }

const tabVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 8 },
  visible: { opacity: 1, scale: 1, y: 0, transition: springTransitionGentle },
}

const contentVariants = {
  hidden: { opacity: 0, x: -16 },
  visible: { opacity: 1, x: 0, transition: springTransitionGentle },
}

export default function CapabilitiesExplorer() {
  const [activeCapKey, setActiveCapKey] = useState('langgraph')
  const currentCapability = CAPABILITIES[activeCapKey]
  const reduced = useReducedMotion()
  const codeRef = useRef(null)

  return (
    <section id="features" className="scroll-mt-24 relative z-20 py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" aria-labelledby="capabilities-heading">
      <motion.div
        className="text-center mb-12"
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
          <Cpu size={13} aria-hidden="true" />
          <span>DEEP CAPABILITIES EXPLORER</span>
        </motion.div>
        <motion.h2
          id="capabilities-heading"
          className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.15 }}
        >
          Interactive System Capabilities
        </motion.h2>
        <motion.p
          className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.2 }}
        >
          Click a subsystem to explore its code, invariants, and safety guarantees.
        </motion.p>

        <motion.div
          className="flex flex-wrap items-center justify-center gap-3 mt-8"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.25 }}
          role="tablist"
          aria-label="System capabilities"
        >
          {Object.keys(CAPABILITIES).map((key, i) => {
            const cap = CAPABILITIES[key]
            const Icon = cap.icon
            const isSelected = activeCapKey === key
            return (
              <motion.button
                key={key}
                onClick={() => setActiveCapKey(key)}
                className={`px-4 py-3 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border spring-interactive ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-lg shadow-cyan-950/50'
                    : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700'
                }`}
                variants={tabVariants}
                initial="hidden"
                animate="visible"
                custom={i}
                whileHover={{ scale: 1.05, transition: springTransition }}
                whileTap={{ scale: 0.97, transition: { duration: 0.08, ease: 'easeOut' } }}
                role="tab"
                aria-selected={isSelected}
                aria-controls={`capability-${key}`}
                id={`tab-${key}`}
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                <motion.span
                  className={isSelected ? 'text-cyan-400' : 'text-slate-500'}
                  animate={isSelected && !reduced ? { rotate: [0, 360] } : false}
                  transition={{ duration: 4, ease: 'linear', repeat: Infinity }}
                >
                  <Icon size={14} aria-hidden="true" />
                </motion.span>
                <span>{cap.title.split(' ')[0]} {cap.title.split(' ')[1]}</span>
              </motion.button>
            )
          })}
        </motion.div>
      </motion.div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeCapKey}
          className="rounded-3xl border border-slate-800/90 bg-surface-900/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:border-cyan-500/40 spring-interactive"
          variants={contentVariants}
          initial="hidden"
          animate="visible"
          exit="hidden"
          role="tabpanel"
          aria-labelledby={`tab-${activeCapKey}`}
          id={`capability-${activeCapKey}`}
        >
          <motion.div
            className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springTransitionGentle, delay: 0.1 }}
          >
            <div>
              <motion.div
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-card border border-cyan-500/20 text-[11px] font-mono text-cyan-300 mb-4 spring-critical"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ ...springTransition, delay: 0.15 }}
              >
                <Activity size={12} aria-hidden="true" />
                <span>{currentCapability.tagline}</span>
              </motion.div>
              <motion.h3
                className="text-2xl sm:text-3xl font-extrabold text-white mb-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springTransitionGentle, delay: 0.2 }}
              >
                {currentCapability.title}
              </motion.h3>
              <motion.p
                className="text-slate-300 text-sm leading-relaxed mb-6 font-normal"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springTransitionGentle, delay: 0.25 }}
              >
                {currentCapability.desc}
              </motion.p>
              <motion.div
                className="space-y-2.5"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springTransitionGentle, delay: 0.3 }}
              >
                {currentCapability.highlights.map((h, i) => (
                  <motion.div
                    key={i}
                    className="flex items-center gap-2.5 text-xs text-slate-300 font-mono"
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ ...springTransitionGentle, delay: 0.35 + i * 0.05 }}
                  >
                    <motion.div
                      className="w-5 h-5 rounded-full bg-emerald-950 border border-emerald-600/60 flex items-center justify-center text-emerald-400 shrink-0"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ ...springTransitionGentle, delay: 0.35 + i * 0.05 }}
                    >
                      <Check size={11} aria-hidden="true" />
                    </motion.div>
                    <span>{h}</span>
                  </motion.div>
                ))}
              </motion.div>
            </div>

            <motion.div
              className="rounded-2xl bg-surface-950 border border-slate-800 p-5 font-mono text-xs text-slate-300 shadow-inner overflow-hidden relative group spring-interactive"
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ ...springTransitionGentle, delay: 0.15 }}
              whileHover={{ scale: 1.01, transition: springTransition }}
              ref={codeRef}
            >
              <div className="flex items-center justify-between text-[11px] text-slate-500 pb-3 mb-3 border-b border-slate-800/80">
                <span>implementation_preview.py</span>
                <span className="text-cyan-400 text-[10px]">Python 3.12 Verified</span>
              </div>
              <pre className="text-slate-300 text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono" style={{ scrollBehavior: 'auto' }}>
                {currentCapability.code}
              </pre>
            </motion.div>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </section>
  )
}