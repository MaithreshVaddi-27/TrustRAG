import { Zap, ShieldCheck, Sparkles, Globe, ArrowRight, FileCheck } from 'lucide-react'

export function EmptyState({ onLoadSample }) {
  return (
    <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-6 sm:p-10 space-y-6 overflow-y-auto">
      <div className="relative">
        <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-primary-600/20 via-cyan-500/10 to-transparent border border-primary-500/30 flex items-center justify-center shadow-glow-cyan animate-float">
          <Zap size={34} className="text-cyan-400" />
        </div>
        <div className="absolute -inset-2.5 rounded-3xl border border-cyan-500/20 animate-pulse-slow pointer-events-none" />
      </div>

      <div className="max-w-md text-center space-y-2">
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
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl w-full text-left">
        <div className="p-3.5 rounded-xl border border-slate-800/90 bg-surface-900/60 backdrop-blur-sm space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
            <FileCheck size={14} className="text-emerald-400" />
            <span>Closed-Loop NLI</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Decomposes generated answers into atomic claims and cross-verifies every proposition against citations.
          </p>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800/90 bg-surface-900/60 backdrop-blur-sm space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
            <Sparkles size={14} className="text-cyan-400" />
            <span>Self-Healing Loop</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            LangGraph state machine automatically triggers targeted query rewrites and context expansions when uncertainty occurs.
          </p>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800/90 bg-surface-900/60 backdrop-blur-sm space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
            <Globe size={14} className="text-primary-400" />
            <span>Zero-Key MCP Web</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Dynamic Model Context Protocol tool execution pulls fresh web facts via DuckDuckGo with 0 API keys.
          </p>
        </div>
      </div>

      <div className="pt-2 flex items-center gap-3">
        <button
          type="button"
          onClick={onLoadSample}
          className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-surface-800 border border-slate-700/80 hover:border-cyan-500/50 flex items-center gap-1.5 transition-all shadow-sm"
        >
          <span>Load Sample Query</span>
          <ArrowRight size={12} className="text-cyan-400" />
        </button>
      </div>
    </div>
  )
}