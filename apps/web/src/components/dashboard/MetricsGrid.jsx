import { Link } from 'react-router-dom'
import { Brain, Database, Zap, ArrowRight, ShieldCheck, TrendingUp } from 'lucide-react'
import { clsx } from 'clsx'

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
        className="glass-card-hover p-5 flex flex-col justify-between group relative overflow-hidden hover:-translate-y-1 hover:border-cyan-400/60 hover:shadow-xl hover:shadow-cyan-950/40 transition-all duration-300"
      >
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform">
            <Database size={20} />
          </div>
          <ArrowRight size={14} className="text-slate-600 group-hover:text-cyan-400 group-hover:translate-x-0.5 transition-all" />
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight">{kbs.length}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span>Knowledge Bases</span>
            <span className="font-mono text-cyan-400">{stats.totalDocs} docs</span>
          </div>
        </div>
      </Link>

      {/* Analyses Run */}
      <Link
        to="/playground"
        className="glass-card-hover p-5 flex flex-col justify-between group relative overflow-hidden hover:-translate-y-1 hover:border-sky-400/60 hover:shadow-xl hover:shadow-sky-950/40 transition-all duration-300"
      >
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-sky-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 group-hover:scale-110 transition-transform">
            <Zap size={20} />
          </div>
          <ArrowRight size={14} className="text-slate-600 group-hover:text-sky-400 group-hover:translate-x-0.5 transition-all" />
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight">{analyses.length}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span>Analyses Executed</span>
            <span className="font-mono text-emerald-400">Evidence-linked</span>
          </div>
        </div>
      </Link>

      {/* Average Reliability Score */}
      <div className="glass-card p-5 flex flex-col justify-between relative overflow-hidden border-emerald-500/20 hover:-translate-y-1 hover:border-emerald-400/60 hover:shadow-xl hover:shadow-emerald-950/40 transition-all duration-300 group">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
            <ShieldCheck size={20} />
          </div>
          <span className="flex items-center gap-1 text-[11px] font-mono font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full">
            <TrendingUp size={11} /> {Number(stats.avgReliability) >= 75 ? 'High Trust' : Number(stats.avgReliability) >= 50 ? 'Medium Trust' : 'Low Trust'}
          </span>
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight">{stats.avgReliabilityDisplay}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span>Mean Reliability</span>
            <span className="font-mono text-slate-500">Threshold: 75%</span>
          </div>
        </div>
      </div>

      {/* Claims Decomposed */}
      <Link
        to="/claims"
        className="glass-card-hover p-5 flex flex-col justify-between group relative overflow-hidden hover:-translate-y-1 hover:border-primary-400/60 hover:shadow-xl hover:shadow-primary-950/40 transition-all duration-300"
      >
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-primary-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex items-center justify-between">
          <div className="w-10 h-10 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center text-primary-400 group-hover:scale-110 transition-transform">
            <Brain size={20} />
          </div>
          <ArrowRight size={14} className="text-slate-600 group-hover:text-primary-400 group-hover:translate-x-0.5 transition-all" />
        </div>
        <div className="mt-4">
          <p className="text-3xl font-extrabold text-white tracking-tight">{stats.totalClaimsCount || claims.length}</p>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
            <span>Claims Decomposed</span>
            <span className="font-mono text-emerald-400">{stats.supportedClaims} verified</span>
          </div>
        </div>
      </Link>
    </div>
  )
}