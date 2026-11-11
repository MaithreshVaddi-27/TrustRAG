import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import { BarChart3 } from 'lucide-react'
import { BENCHMARKS } from './landingData'

export default function BenchmarksSection() {
  const [activeBenchmarkKey, setActiveBenchmarkKey] = useState('accuracy')
  const currentBenchmark = BENCHMARKS[activeBenchmarkKey]
  const reduced = useReducedMotion()

  const springTransition = { type: 'spring', damping: 25, stiffness: 200 }
  const springTransitionGentle = { type: 'spring', damping: 30, stiffness: 180 }

  const headerVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: { opacity: 1, y: 0, transition: springTransitionGentle },
  }

  const tabVariants = {
    hidden: { opacity: 0, scale: 0.95, y: 8 },
    visible: (i) => ({ opacity: 1, scale: 1, y: 0, transition: { ...springTransitionGentle, delay: 0.1 + i * 0.05 } }),
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.98 },
    visible: { opacity: 1, y: 0, scale: 1, transition: springTransitionGentle },
  }

  const metricVariants = {
    hidden: { opacity: 0, x: -20, scaleX: 0.8 },
    visible: (i) => ({ opacity: 1, x: 0, scaleX: 1, transition: { ...springTransitionGentle, delay: 0.2 + i * 0.08 } }),
  }

  return (
    <section id="benchmarks" className="scroll-mt-24 relative z-20 py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8" aria-labelledby="benchmarks-heading">
      <motion.div
        className="text-center mb-12"
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
          <BarChart3 size={13} aria-hidden="true" />
          <span>EMPIRICAL BENCHMARKS & EVALUATION</span>
        </motion.div>
        <motion.h2
          id="benchmarks-heading"
          className="font-display text-heading-1 tracking-tight text-white"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.15 }}
        >
          Proven Performance In Production
        </motion.h2>
        <motion.p
          className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.2 }}
        >
          Toggle between accuracy, latency SLA, and vector storage memory savings.
        </motion.p>

        <motion.div
          className="flex flex-wrap items-center justify-center gap-3 mt-8"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springTransitionGentle, delay: 0.25 }}
          role="tablist"
          aria-label="Benchmark categories"
        >
          {Object.entries(BENCHMARKS).map(([key, b], i) => {
            const Icon = b.icon
            const isSelected = activeBenchmarkKey === key
            return (
              <motion.button
                key={key}
                onClick={() => setActiveBenchmarkKey(key)}
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
                aria-controls={`benchmark-${key}`}
                id={`tab-benchmark-${key}`}
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                <motion.span
                  className={isSelected ? 'text-cyan-400' : 'text-slate-500'}
                  animate={isSelected && !reduced ? { rotate: [0, 360] } : false}
                  transition={{ duration: 4, ease: 'linear', repeat: Infinity }}
                >
                  <Icon size={14} aria-hidden="true" />
                </motion.span>
                <span>{b.label}</span>
              </motion.button>
            )
          })}
        </motion.div>
      </motion.div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeBenchmarkKey}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          exit="hidden"
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          className="rounded-3xl border border-slate-800/90 bg-surface-900/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:border-cyan-500/40 spring-interactive"
          role="tabpanel"
          aria-labelledby={`tab-benchmark-${activeBenchmarkKey}`}
          id={`benchmark-${activeBenchmarkKey}`}
        >
          <motion.div
            className="mb-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springTransitionGentle, delay: 0.1 }}
          >
            <motion.h3
              className="text-xl sm:text-2xl font-extrabold text-white mb-2"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...springTransitionGentle, delay: 0.15 }}
            >
              {currentBenchmark.title}
            </motion.h3>
            <motion.p
              className="text-slate-400 text-xs sm:text-sm"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...springTransitionGentle, delay: 0.2 }}
            >
              {currentBenchmark.description}
            </motion.p>
          </motion.div>

          <motion.div
            className="space-y-5"
            variants={metricVariants}
            initial="hidden"
            animate="visible"
          >
            {currentBenchmark.metrics.map((m, i) => (
              <motion.div
                key={i}
                className="space-y-1.5 group cursor-default relative"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...springTransitionGentle, delay: 0.2 + i * 0.08 }}
                whileHover={{ x: 4, transition: springTransition }}
              >
                <motion.div
                  className="flex items-center justify-between text-xs font-mono"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ ...springTransitionGentle, delay: 0.25 + i * 0.08 }}
                >
                  <span className={`font-semibold ${m.highlight ? 'text-cyan-300' : 'text-slate-300'}`}>
                    {m.label}
                  </span>
                  <motion.div
                    className="flex items-center gap-2"
                    whileHover={{ scale: 1.02, transition: springTransition }}
                  >
                    <span className="text-[10px] px-2 py-0.5 rounded bg-surface-850 border border-slate-800 text-slate-400">
                      {m.badge}
                    </span>
                    <span className={`font-bold ${m.highlight ? 'text-cyan-400 text-sm' : 'text-slate-300'}`}>
                      {m.value} {m.suffix}
                    </span>
                  </motion.div>
                </motion.div>
                <motion.div
                  className="h-3 rounded-full bg-surface-950 border border-slate-800/80 overflow-hidden p-0.5 relative"
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ ...springTransitionGentle, delay: 0.3 + i * 0.08, duration: 0.8 }}
                  style={{ transformOrigin: 'left center' }}
                >
                  <motion.div
                    className={`h-full rounded-full bg-gradient-to-r ${m.color} shadow-sm relative`}
                    style={{ width: m.width }}
                    initial={{ width: 0 }}
                    animate={{ width: m.width }}
                    transition={{ type: 'spring', damping: 30, stiffness: 180, delay: 0.35 + i * 0.08, duration: 1.2 }}
                  >
                    <motion.div
                      className="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white/80 opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-hidden="true"
                    />
                  </motion.div>
                </motion.div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </section>
  )
}
