import { Link } from 'react-router-dom'
import { Brain, Database, Zap, ArrowRight, ShieldCheck, TrendingUp } from 'lucide-react'

/**
 * MetricsGrid - 4 hero metric cards
 * Called by: DashboardPage.jsx (line 347-431)
 * No existing file serves this purpose - extracted from DashboardPage
 * Reads/writes: Receives stats, kbs, analyses, claims, conflicts as props
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function MetricsGrid({ stats, kbs, analyses, claims, conflicts }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Knowledge Bases */}
      <Link
        to="/knowledge-bases"
        className="glass-card glass-card-hover p-5 flex flex-col justify-between group relative overflow-hidden transition-all duration-300"
      >
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform">
            <Database size={18} />
          </div>
          <div className="w-6 h-6 rounded-lg bg-surface-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 group-hover:text-cyan-300 group-hover:border-cyan-500/40 transition-all">
            <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
          </div>
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight tabular-nums">{kbs.length}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span className="font-medium">Knowledge Bases</span>
            <span className="font-mono text-cyan-400 text-[11px]">{stats.totalDocs} docs</span>
          </div>
        </div>
      </Link>

      {/* Analyses Run */}
      <Link
        to="/playground"
        className="glass-card glass-card-hover p-5 flex flex-col justify-between group relative overflow-hidden transition-all duration-300"
      >
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-primary-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center text-primary-400 group-hover:scale-110 transition-transform">
            <Zap size={18} />
          </div>
          <div className="w-6 h-6 rounded-lg bg-surface-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 group-hover:text-primary-300 group-hover:border-primary-500/40 transition-all">
            <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
          </div>
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight tabular-nums">{analyses.length}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span className="font-medium">Analyses Executed</span>
            <span className="font-mono text-emerald-400 text-[11px]">Evidence-linked</span>
          </div>
        </div>
      </Link>

      {/* Average Reliability Score */}
      <div className="glass-card glass-card-hover p-5 flex flex-col justify-between relative overflow-hidden border-emerald-500/20 group transition-all duration-300">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
            <ShieldCheck size={18} />
          </div>
          <span className="flex items-center gap-1 text-[11px] font-mono font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full">
            <TrendingUp size={11} /> {Number(stats.avgReliability) >= 75 ? 'High Trust' : Number(stats.avgReliability) >= 50 ? 'Medium Trust' : 'Low Trust'}
          </span>
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight tabular-nums">{stats.avgReliabilityDisplay}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span className="font-medium">Mean Reliability</span>
            <span className="font-mono text-slate-500 text-[11px]">Threshold: 75%</span>
          </div>
        </div>
      </div>

      {/* Claims Decomposed */}
      <Link
        to="/claims"
        className="glass-card glass-card-hover p-5 flex flex-col justify-between group relative overflow-hidden transition-all duration-300"
      >
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-primary-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center text-primary-400 group-hover:scale-110 transition-transform">
            <Brain size={18} />
          </div>
          <div className="w-6 h-6 rounded-lg bg-surface-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 group-hover:text-primary-300 group-hover:border-primary-500/40 transition-all">
            <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
          </div>
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight tabular-nums">{stats.totalClaimsCount || claims.length}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span className="font-medium">Claims Decomposed</span>
            <span className="font-mono text-emerald-400 text-[11px]">{stats.supportedClaims} verified{conflicts?.length ? ` · ${conflicts.length} flagged` : ''}</span>
          </div>
        </div>
      </Link>
    </div>
  )
}