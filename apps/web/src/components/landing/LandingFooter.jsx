import { Link } from 'react-router-dom'
import { Swords, ExternalLink } from 'lucide-react'

export default function LandingFooter() {
  return (
    <footer className="relative z-20 border-t border-slate-800/80 py-12 bg-surface-950/90 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-primary-600 to-cyan-500 flex items-center justify-center text-white shadow-md">
            <Swords size={13} />
          </div>
          <span className="font-bold text-slate-200 text-sm">TRUSTRAG</span>
          <span className="text-slate-500">Autonomous AI Reliability Platform</span>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>All Verification Nodes Operational</span>
        </div>

        <div className="flex items-center gap-6">
          <a href="https://github.com/MaithreshVaddi-27/TrustRAG" target="_blank" rel="noreferrer" className="hover:text-cyan-400 transition-colors flex items-center gap-1">
            <span>GitHub</span>
            <ExternalLink size={12} />
          </a>
          <Link to="/login" className="hover:text-cyan-400 transition-colors">Sign In</Link>
          <Link to="/login" className="hover:text-cyan-400 transition-colors">Get Started</Link>
        </div>
      </div>
    </footer>
  )
}
