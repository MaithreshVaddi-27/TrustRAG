import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, Zap, ShieldCheck, RefreshCw
} from 'lucide-react'

export default function HeroSection() {
  const navigate = useNavigate()

  return (
    <section className="relative z-20 pt-20 pb-16 sm:pt-28 sm:pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
      {/* Floating Card Left (Desktop) */}
      <div className="hidden xl:flex absolute left-4 top-32 items-center gap-3 p-3.5 rounded-2xl bg-surface-900/90 border border-slate-700/80 backdrop-blur-xl shadow-2xl shadow-cyan-950/50 animate-float hover:scale-105 transition-transform group cursor-default">
        <div className="w-10 h-10 rounded-xl bg-emerald-950/80 border border-emerald-500/40 flex items-center justify-center text-emerald-400 group-hover:rotate-6 transition-transform">
          <ShieldCheck size={20} />
        </div>
        <div className="text-left font-mono">
          <div className="text-white text-xs font-bold flex items-center gap-1.5">
            <span>Entailment Guard</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          </div>
          <div className="text-emerald-400 text-[10px]">99.4% Claim Precision</div>
        </div>
      </div>

      {/* Floating Card Right (Desktop) */}
      <div className="hidden xl:flex absolute right-4 top-36 items-center gap-3 p-3.5 rounded-2xl bg-surface-900/90 border border-slate-700/80 backdrop-blur-xl shadow-2xl shadow-cyan-950/50 animate-float hover:scale-105 transition-transform group cursor-default" style={{ animationDelay: '2.5s' }}>
        <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 group-hover:rotate-180 transition-transform duration-700">
          <RefreshCw size={18} className="animate-spin-slow" />
        </div>
        <div className="text-left font-mono">
          <div className="text-white text-xs font-bold flex items-center gap-1.5">
            <span>Self-Healing Loop</span>
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          </div>
          <div className="text-cyan-400 text-[10px]">LangGraph Active</div>
        </div>
      </div>

      {/* Floating Telemetry Badge */}
      <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-surface-900/90 border border-cyan-500/40 text-xs font-mono text-cyan-300 shadow-xl shadow-cyan-950/50 mb-8 backdrop-blur-md animate-fade-in hover:border-cyan-400 hover:scale-105 transition-all cursor-default">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
        </span>
        <span className="font-semibold tracking-wide">AUTONOMOUS AGENTIC RELIABILITY</span>
        <span className="text-slate-600">|</span>
        <span className="text-slate-400">Zero Hallucination Tolerance</span>
      </div>

      <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.08] mb-6">
        Trust Every Token With{' '}
        <span className="shimmer-text">Closed-Loop Self-Healing RAG</span>
      </h1>

      <p className="text-slate-400 text-base sm:text-lg max-w-3xl mx-auto leading-relaxed mb-10 font-normal">
        Decompose unstructured LLM responses into atomic propositional claims, cross-examine citations with hybrid RRF retrieval, and autonomously trigger LangGraph self-healing loops before hallucinations reach users.
      </p>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
        <button
          onClick={() => navigate('/register')}
          className="w-full sm:w-auto px-9 py-4 rounded-xl bg-gradient-to-r from-primary-600 via-sky-500 to-cyan-500 hover:from-primary-500 hover:to-cyan-400 text-white font-bold text-sm shadow-2xl shadow-cyan-950/80 border border-cyan-400/50 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.04] active:scale-[0.98] group cursor-pointer relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full duration-700 transition-transform pointer-events-none" />
          <span>Get Started Free</span>
          <ArrowRight size={16} className="group-hover:translate-x-1.5 transition-transform" />
        </button>
        <a
          href="#simulation"
          className="w-full sm:w-auto px-8 py-4 rounded-xl bg-surface-900/90 hover:bg-surface-850 text-slate-300 hover:text-white font-semibold text-sm border border-slate-700/80 hover:border-cyan-400/60 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98] backdrop-blur-md shadow-lg group"
        >
          <Zap size={16} className="text-cyan-400 group-hover:scale-125 transition-transform" />
          <span>Launch Interactive Sandbox</span>
        </a>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto pt-6 border-t border-slate-800/80">
        <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-cyan-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-cyan-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="text-2xl sm:text-3xl font-extrabold text-white font-mono group-hover:scale-105 transition-transform origin-left">99.4%</div>
          <div className="text-xs text-slate-400 mt-1">Claim Grounding Precision</div>
        </div>
        <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-emerald-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-emerald-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 font-mono group-hover:scale-105 transition-transform origin-left">0.0%</div>
          <div className="text-xs text-slate-400 mt-1">Hallucination Leakage</div>
        </div>
        <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-cyan-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-cyan-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400 font-mono group-hover:scale-105 transition-transform origin-left">&lt;120ms</div>
          <div className="text-xs text-slate-400 mt-1">Hybrid RRF Retrieval</div>
        </div>
        <div className="p-5 rounded-2xl bg-surface-900/50 border border-slate-800/80 backdrop-blur-md hover:border-sky-400/60 hover:bg-surface-850/90 hover:-translate-y-2 hover:shadow-2xl hover:shadow-sky-950/50 transition-all duration-300 group cursor-default relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-sky-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="text-2xl sm:text-3xl font-extrabold text-sky-400 font-mono group-hover:scale-105 transition-transform origin-left">0 MB</div>
          <div className="text-xs text-slate-400 mt-1">Local GPU Weights (Pure Cloud)</div>
        </div>
      </div>
    </section>
  )
}
