import { Link } from 'react-router-dom'
import { Swords, ArrowLeft } from 'lucide-react'

/**
 * AuthLayout — minimal centered layout for Login/Register pages.
 */
export default function AuthLayout({ children, title, subtitle }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-950 bg-cyber-grid px-4 relative overflow-hidden">
      {/* Ambient gradient */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-cyan-500/10 blur-[130px]" />
      </div>

      <div className="w-full max-w-sm relative z-10 animate-fade-in">
        {/* Back to Home Link */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 transition-colors mb-6 group"
        >
          <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform" />
          <span>Back to overview</span>
        </Link>

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <Link to="/" className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-primary-600 to-cyan-500 flex items-center justify-center shadow-xl shadow-primary-950/80 mb-4 border border-cyan-400/20 hover:scale-105 transition-transform group">
            <Swords size={24} className="text-white" />
          </Link>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            TRUST<span className="text-primary-400">RAG</span>
          </h1>
          <p className="text-slate-400 text-xs mt-1 text-center font-mono">Autonomous AI Reliability Workbench</p>
        </div>

        {/* Card */}
        <div className="glass-card p-6 shadow-2xl">
          {title && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white">{title}</h2>
              {subtitle && <p className="text-slate-400 text-sm mt-1">{subtitle}</p>}
            </div>
          )}
          {children}
        </div>
      </div>
    </div>
  )
}
