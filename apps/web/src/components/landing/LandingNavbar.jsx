import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Swords, ArrowRight, ChevronRight,
  Sparkles, Cpu, RefreshCw, BarChart3, ShieldCheck,
  Menu, X
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export default function LandingNavbar() {
  const { isAuthenticated } = useAuthStore()
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 backdrop-blur-2xl bg-surface-950/80 border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-primary-950/80 border border-cyan-400/30 group-hover:scale-105 transition-transform">
            <Swords size={18} className="text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-base tracking-tight text-white flex items-center gap-1">
              TRUST<span className="text-primary-400">RAG</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest hidden sm:inline">
              Reliability Workbench
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-400">
          <a href="#simulation" className="hover:text-cyan-400 transition-colors flex items-center gap-1">
            <Sparkles size={13} className="text-cyan-400" />
            <span>Sandbox</span>
          </a>
          <a href="#features" className="hover:text-cyan-400 transition-colors">Capabilities</a>
          <a href="#bento" className="hover:text-cyan-400 transition-colors">Architecture</a>
          <a href="#benchmarks" className="hover:text-cyan-400 transition-colors">Benchmarks</a>
          <a href="#compare" className="hover:text-cyan-400 transition-colors">Comparison</a>
        </nav>

        <div className="flex items-center gap-2.5">
          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/50 border border-cyan-400/30 transition-all hover:scale-[1.02]"
            >
              <span>Dashboard</span>
              <ChevronRight size={14} />
            </Link>
          ) : (
            <div className="hidden sm:flex items-center gap-3">
              <Link
                to="/login"
                className="px-3.5 py-1.5 rounded-xl text-slate-300 hover:text-white hover:bg-surface-800/80 text-xs font-semibold transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/50 border border-cyan-400/30 transition-all hover:scale-[1.02]"
              >
                <span>Get Started</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          )}

          <button
            onClick={() => setIsMobileNavOpen(prev => !prev)}
            className="md:hidden flex items-center justify-center w-9 h-9 rounded-xl border border-slate-800 text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
            aria-label="Toggle mobile menu"
          >
            {isMobileNavOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {isMobileNavOpen && (
        <div className="md:hidden bg-surface-950/95 border-b border-slate-800 backdrop-blur-2xl px-4 pt-3 pb-5 space-y-3 animate-fade-in">
          <div className="flex flex-col space-y-1.5 text-xs font-medium text-slate-300">
            <a href="#simulation" onClick={() => setIsMobileNavOpen(false)} className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2">
              <Sparkles size={14} className="text-cyan-400" />
              <span>Interactive Sandbox</span>
            </a>
            <a href="#features" onClick={() => setIsMobileNavOpen(false)} className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2">
              <Cpu size={14} className="text-cyan-400" />
              <span>Capabilities Explorer</span>
            </a>
            <a href="#bento" onClick={() => setIsMobileNavOpen(false)} className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2">
              <RefreshCw size={14} className="text-cyan-400" />
              <span>Architecture</span>
            </a>
            <a href="#benchmarks" onClick={() => setIsMobileNavOpen(false)} className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2">
              <BarChart3 size={14} className="text-cyan-400" />
              <span>Benchmarks</span>
            </a>
            <a href="#compare" onClick={() => setIsMobileNavOpen(false)} className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2">
              <ShieldCheck size={14} className="text-cyan-400" />
              <span>Why TrustRAG</span>
            </a>
          </div>
          {!isAuthenticated && (
            <div className="pt-3 border-t border-slate-800/80 flex items-center gap-2.5">
              <Link to="/login" onClick={() => setIsMobileNavOpen(false)} className="flex-1 py-2.5 rounded-xl text-center text-xs font-semibold text-slate-300 bg-surface-900 border border-slate-800">
                Sign In
              </Link>
              <Link to="/register" onClick={() => setIsMobileNavOpen(false)} className="flex-1 py-2.5 rounded-xl text-center text-xs font-semibold text-white bg-gradient-to-r from-primary-600 to-cyan-600 shadow-md">
                Get Started
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  )
}
