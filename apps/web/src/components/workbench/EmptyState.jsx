import { motion } from 'motion/react'
import { Zap, ShieldCheck, Sparkles, Globe, FileCheck } from 'lucide-react'
import { SPRING_GENTLE } from '@/lib/motionConfig'

const staggerItem = {
  hidden: { opacity: 0, y: 16 },
  visible: i => ({
    opacity: 1,
    y: 0,
    transition: { ...SPRING_GENTLE, delay: i * 0.08 }
  })
}

export function EmptyState({ enableWebSearch = false }) {
  return (
    <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-6 sm:p-10 space-y-6 overflow-y-auto">
      <motion.div
        custom={0}
        variants={staggerItem}
        initial="hidden"
        animate="visible"
        className="relative"
      >
        <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-primary-600/20 via-cyan-500/10 to-transparent border border-primary-500/30 flex items-center justify-center shadow-glow-cyan animate-float">
          <Zap size={34} className="text-cyan-400" />
        </div>
        <div className="absolute -inset-2.5 rounded-3xl border border-cyan-500/20 animate-pulse-slow pointer-events-none" />
      </motion.div>

      <motion.div
        custom={1}
        variants={staggerItem}
        initial="hidden"
        animate="visible"
        className="max-w-md text-center space-y-2"
      >
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/70 border border-cyan-700/50 text-cyan-300 text-[11px] font-mono mb-1">
          <ShieldCheck size={12} className="text-cyan-400" />
          <span>Interactive Verification Workbench</span>
        </div>
        <h3 className="text-lg font-bold text-slate-100 tracking-tight">
          Awaiting Pipeline Query
        </h3>
        <p className="text-slate-400 text-xs leading-relaxed">
          Select a knowledge base, configure your AI engine, and execute your prompt to observe closed-loop NLI claim verification in real-time.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl w-full text-left">
        {[
          { icon: FileCheck, iconColor: 'text-emerald-400', title: 'Closed-Loop NLI', desc: 'Decomposes generated answers into atomic claims and cross-verifies every proposition against citations.' },
          { icon: Sparkles, iconColor: 'text-cyan-400', title: 'Self-Healing Loop', desc: 'LangGraph state machine automatically triggers targeted query rewrites and context expansions when uncertainty occurs.' },
          ...(enableWebSearch
            ? [{ icon: Globe, iconColor: 'text-primary-400', title: 'Web Grounding', desc: 'MCP tool execution pulls fresh web facts alongside your local knowledge base.' }]
            : []),
        ].map((card, i) => (
          <motion.div
            key={card.title}
            custom={i + 2}
            variants={staggerItem}
            initial="hidden"
            animate="visible"
            className="p-3.5 rounded-xl border border-slate-800/90 bg-surface-900/60 backdrop-blur-sm space-y-1.5"
          >
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <card.icon size={14} className={card.iconColor} />
              <span>{card.title}</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              {card.desc}
            </p>
          </motion.div>
        ))}
      </div>

      </div>
  )
}
