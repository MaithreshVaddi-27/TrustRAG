import { Link } from 'react-router-dom'
import { Swords } from 'lucide-react'

/**
 * AuthLayout — minimal centered layout for Login/Register pages.
 */
export default function AuthLayout({ children, title, subtitle }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-950 px-4">
      {/* Ambient gradient */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-primary-600/10 blur-[120px]" />
      </div>

      <div className="w-full max-w-sm relative z-10">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-primary-600 flex items-center justify-center shadow-xl shadow-primary-900/60 mb-4">
            <Swords size={22} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            TRUST<span className="text-primary-400">RAG</span>
          </h1>
          <p className="text-slate-500 text-sm mt-1 text-center">AI Reliability Workbench</p>
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
