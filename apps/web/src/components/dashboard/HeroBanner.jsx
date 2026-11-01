import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { Database, Zap, Activity } from 'lucide-react'

/**
 * HeroBanner - Dashboard hero section with CTAs
 * Called by: DashboardPage.jsx (line 230-266)
 * No existing file serves this purpose - extracted from DashboardPage
 * Reads/writes: No external data, purely presentational
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function HeroBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200, delay: 0.1 }}
      className="glass-card relative overflow-hidden p-6 sm:p-8 border-primary-500/20 bg-gradient-to-br from-surface-900/90 via-surface-900/60 to-primary-950/20"
    >
      {/* Subtle glowing ambient orb */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-primary-500/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 border border-primary-500/30 text-xs font-mono text-primary-300">
            <Activity size={12} className="text-cyan-400 animate-pulse" />
            <span>Production Observability Engine Active</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            AI Reliability <span className="text-gradient">Workbench</span>
          </h1>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl leading-relaxed">
            Autonomous hallucination detection, atomic claim verification, and self-healing closed-loop RAG recovery powered by LangGraph.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <Link
            to="/knowledge-bases"
            className="btn-secondary text-xs sm:text-sm px-4 py-2.5"
          >
            <Database size={15} />
            <span>Knowledge Bases</span>
          </Link>
          <Link
            to="/playground"
            className="btn-primary text-xs sm:text-sm px-5 py-2.5 shadow-lg shadow-primary-900/40"
          >
            <Zap size={15} />
            <span>Run Interactive Analysis</span>
          </Link>
        </div>
      </div>
    </motion.div>
  )
}