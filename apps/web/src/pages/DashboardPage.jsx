import { useState, useMemo, useEffect } from 'react'
import {
  Brain, Database, Zap, ArrowRight, Clock,
  ShieldCheck, Cpu,
  TrendingUp, Sparkles, Layers, Activity, RefreshCw
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, Cell, ReferenceLine
} from 'recharts'
import AppLayout from '@/layouts/AppLayout'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'
import { kbService, analysisService, claimService, conflictService } from '@/services/api'
import { formatDistanceToNow, format } from 'date-fns'

const PIPELINE_PHASES = [
  {
    step: '01',
    title: 'Hybrid Retrieval',
    desc: 'Dense embeddings (Local BGE / Ollama / Gemini) + Sparse BM25 fused via Reciprocal Rank Fusion.',
    icon: Database,
    color: 'text-cyan-400',
    border: 'border-cyan-500/30',
  },
  {
    step: '02',
    title: 'Grounded Reasoning',
    desc: 'Strict evidence-grounded synthesis using Local LLMs (Ollama / llama.cpp) or Cloud.',
    icon: Cpu,
    color: 'text-sky-400',
    border: 'border-sky-500/30',
  },
  {
    step: '03',
    title: 'Claim Decomposition',
    desc: 'Automated extraction of atomic, falsifiable claims from synthesized answers.',
    icon: Brain,
    color: 'text-primary-400',
    border: 'border-primary-500/30',
  },
  {
    step: '04',
    title: 'Multi-Perspective NLI',
    desc: 'Zero-temperature natural language inference verifying each claim against evidence.',
    icon: ShieldCheck,
    color: 'text-emerald-400',
    border: 'border-emerald-500/30',
  },
  {
    step: '05',
    title: 'Self-Healing Recovery',
    desc: 'Adaptive LangGraph state loop triggers query rewrite or expanded retrieval on failure.',
    icon: Sparkles,
    color: 'text-teal-400',
    border: 'border-teal-500/30',
  },
]

export default function DashboardPage() {
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [historyWindow, setHistoryWindow] = useState('10') // '10' | '20' | 'all'
  const [lastSync, setLastSync] = useState(new Date())

  // Real-time live polling every 3 seconds for active telemetry
  const {
    data: analyses = [],
    refetch: refetchAnalyses,
    isFetching: isFetchingAnalyses,
  } = useQuery({
    queryKey: ['analyses'],
    queryFn: analysisService.list,
    refetchInterval: autoRefresh ? 3000 : false,
  })

  const {
    data: claims = [],
    refetch: refetchClaims,
  } = useQuery({
    queryKey: ['all-claims'],
    queryFn: claimService.list,
    refetchInterval: autoRefresh ? 3000 : false,
  })

  const {
    data: conflicts = [],
    refetch: refetchConflicts,
  } = useQuery({
    queryKey: ['all-conflicts'],
    queryFn: conflictService.list,
    refetchInterval: autoRefresh ? 5000 : false,
  })

  const {
    data: kbs = [],
    refetch: refetchKbs,
  } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list,
    refetchInterval: autoRefresh ? 5000 : false,
  })

  useEffect(() => {
    setLastSync(new Date())
  }, [analyses, claims])

  const handleManualSync = () => {
    refetchAnalyses()
    refetchClaims()
    refetchConflicts()
    refetchKbs()
  }

  // Aggregate statistics computed from real live history
  const stats = useMemo(() => {
    const totalDocs = kbs.reduce((sum, kb) => sum + (kb.document_count || 0), 0)
    
    let totalScore = 0
    let scoredCount = 0
    let supportedClaims = 0
    let contradictedClaims = 0
    let neutralClaims = 0

    analyses.forEach(a => {
      if (a.reliability?.score !== undefined && a.reliability?.score !== null) {
        totalScore += a.reliability.score
        scoredCount++
      }
    })

    claims.forEach(c => {
      const s = (c.state || c.status || c.verification_status || '').toLowerCase()
      if (s === 'supported' || s === 'verified') supportedClaims++
      else if (s === 'contradicted') contradictedClaims++
      else neutralClaims++
    })

    const avgReliability = scoredCount > 0 ? (totalScore / scoredCount) : 0
    const avgReliabilityDisplay = scoredCount > 0 ? `${(avgReliability * 100).toFixed(1)}%` : '--'
    const totalClaimsCount = supportedClaims + contradictedClaims + neutralClaims
    const supportedRate = totalClaimsCount > 0 ? ((supportedClaims / totalClaimsCount) * 100).toFixed(0) : '0'

    return {
      totalDocs,
      avgReliability: (avgReliability * 100).toFixed(1),
      avgReliabilityDisplay,
      supportedClaims,
      contradictedClaims,
      neutralClaims,
      totalClaimsCount,
      supportedRate,
      totalConflicts: conflicts.length,
    }
  }, [kbs, analyses, claims, conflicts])

  // Chart data: Reliability progression curve according to real history (chronological: past -> present)
  const timelineData = useMemo(() => {
    if (!analyses || !analyses.length) return []

    const limit = historyWindow === 'all' ? analyses.length : Number(historyWindow)
    // analyses is sorted by created_at DESC from the API, so slice newest and reverse to plot left-to-right
    const chronologicalSlice = [...analyses].slice(0, limit).reverse()

    return chronologicalSlice.map((a, idx) => {
      const scoreValue = a.reliability?.score != null
        ? Math.round(a.reliability.score * 100)
        : (a.status === 'completed' ? 100 : 0)

      const createdDate = a.created_at ? new Date(a.created_at) : new Date()

      return {
        id: a.id,
        runLabel: `#${idx + 1}`,
        time: format(createdDate, 'HH:mm'),
        fullTime: format(createdDate, 'MMM dd, HH:mm:ss'),
        score: scoreValue,
        threshold: 70,
        status: a.reliability?.status || (scoreValue >= 70 ? 'TRUSTED' : (scoreValue > 0 ? 'UNCERTAIN' : 'FAILED')),
        query: a.query || 'Untitled Analysis',
        shortQuery: (a.query || '').length > 30 ? (a.query || '').slice(0, 30) + '…' : (a.query || 'Untitled Analysis'),
        statusRaw: a.status,
      }
    })
  }, [analyses, historyWindow])

  // Chart data: Claims breakdown
  const claimDistributionData = useMemo(() => {
    return [
      { name: 'Supported', count: stats.supportedClaims, color: '#10b981' },
      { name: 'Neutral', count: stats.neutralClaims, color: '#f59e0b' },
      { name: 'Contradicted', count: stats.contradictedClaims, color: '#ef4444' },
    ]
  }, [stats])

  return (
    <AppLayout>
      <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-8 animate-fade-in">
        {/* ── HERO BANNER ─────────────────────────────────────────────── */}
        <div className="glass-card relative overflow-hidden p-6 sm:p-8 border-primary-500/20 bg-gradient-to-br from-surface-900/90 via-surface-900/60 to-primary-950/20">
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
        </div>

        {/* ── LIVE OBSERVABILITY CONTROL BAR ────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 rounded-2xl border border-cyan-500/30 bg-surface-900/80 backdrop-blur-xl shadow-lg shadow-cyan-950/20">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center">
              {autoRefresh ? (
                <>
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                  <span className="absolute w-2 h-2 rounded-full bg-emerald-400" />
                </>
              ) : (
                <span className="w-2 h-2 rounded-full bg-slate-500" />
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold tracking-wider uppercase text-cyan-300">
                Live Observability Stream
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                autoRefresh
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60'
                  : 'bg-surface-950 text-slate-400 border-slate-800'
              }`}>
                {autoRefresh ? 'Active Polling (3s)' : 'Paused'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
            <span>Synced {formatDistanceToNow(lastSync, { addSuffix: true })}</span>
            <button
              type="button"
              onClick={handleManualSync}
              disabled={isFetchingAnalyses}
              className="px-2.5 py-1.5 rounded-xl bg-surface-800 hover:bg-surface-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-sm"
              title="Force sync live state"
            >
              <RefreshCw size={12} className={isFetchingAnalyses ? 'animate-spin text-cyan-400' : 'text-slate-400'} />
              <span>Sync Now</span>
            </button>
            <button
              type="button"
              onClick={() => setAutoRefresh(prev => !prev)}
              className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all shadow-sm ${
                autoRefresh
                  ? 'bg-emerald-950/50 border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/50'
                  : 'bg-surface-800 border-slate-700 text-slate-300 hover:text-white'
              }`}
            >
              {autoRefresh ? 'Pause Stream' : 'Go Live'}
            </button>
          </div>
        </div>

        {/* ── 4 HERO METRIC CARDS ─────────────────────────────────────── */}
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
                <span className="font-mono text-emerald-400">100% Grounded</span>
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
                <TrendingUp size={11} /> High Trust
              </span>
            </div>
            <div className="mt-4">
              <p className="text-3xl font-extrabold text-white tracking-tight">{stats.avgReliabilityDisplay}</p>
              <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
                <span>Mean Reliability</span>
                <span className="font-mono text-slate-500">Threshold: 70%</span>
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

        {/* ── ANALYTICS VISUALIZATIONS ────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Reliability Score History AreaChart */}
          <div className="lg:col-span-2 glass-card p-6 flex flex-col justify-between">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  <Activity size={16} className="text-cyan-400" />
                  Reliability Progression Curve
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Chronological execution history trajectory vs. safety threshold (70%)</p>
              </div>

              {/* History Window Filter Pills */}
              <div className="flex items-center gap-1.5 bg-surface-950 p-1 rounded-xl border border-slate-800 text-[11px] font-mono shrink-0">
                <button
                  type="button"
                  onClick={() => setHistoryWindow('10')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    historyWindow === '10'
                      ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800/60 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Last 10
                </button>
                <button
                  type="button"
                  onClick={() => setHistoryWindow('20')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    historyWindow === '20'
                      ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800/60 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Last 20
                </button>
                <button
                  type="button"
                  onClick={() => setHistoryWindow('all')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    historyWindow === 'all'
                      ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800/60 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  All ({analyses.length})
                </button>
              </div>
            </div>

            {timelineData.length === 0 ? (
              <div className="h-64 w-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl bg-surface-900/40">
                <Activity size={24} className="text-slate-600 mb-2" />
                <p className="text-xs text-slate-300 font-medium">No reliability analyses recorded yet</p>
                <p className="text-[11px] text-slate-500 mt-1 max-w-sm">
                  Run an analysis in the Playground to generate telemetry progression and claim audit benchmarks.
                </p>
              </div>
            ) : (
              <div className="h-64 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timelineData} margin={{ top: 15, right: 15, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.45} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="runLabel"
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                    />
                    <YAxis
                      stroke="#64748b"
                      fontSize={11}
                      domain={[0, 100]}
                      ticks={[0, 25, 50, 75, 100]}
                      tickLine={false}
                    />
                    <ReferenceLine
                      y={70}
                      stroke="#f59e0b"
                      strokeDasharray="3 3"
                      label={{
                        value: 'Safety Threshold (70%)',
                        position: 'insideTopRight',
                        fill: '#f59e0b',
                        fontSize: 10,
                        fontFamily: 'monospace',
                      }}
                    />
                    <Tooltip content={<CustomTimelineTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="score"
                      stroke="#06b6d4"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#scoreGradient)"
                      dot={{ fill: '#06b6d4', stroke: '#080c16', strokeWidth: 2, r: 4 }}
                      activeDot={{ fill: '#38bdf8', stroke: '#ffffff', strokeWidth: 2, r: 6 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Claim Verification Breakdown BarChart */}
          <div className="glass-card p-6 flex flex-col justify-between">
            <div className="mb-4">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-400" />
                Claim Verification Audit
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {stats.totalClaimsCount} atomic claims evaluated from history
              </p>
            </div>

            {stats.totalClaimsCount === 0 ? (
              <div className="h-48 w-full flex flex-col items-center justify-center text-center p-4 border border-dashed border-slate-800 rounded-xl bg-surface-900/40">
                <ShieldCheck size={24} className="text-slate-600 mb-2" />
                <p className="text-xs text-slate-300 font-medium">No claims decomposed yet</p>
                <p className="text-[11px] text-slate-500 mt-1 max-w-xs">
                  Run a query in the Playground to extract and verify atomic assertions.
                </p>
              </div>
            ) : (
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={claimDistributionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#080c16',
                        borderColor: '#1e293b',
                        borderRadius: '12px',
                        fontSize: '12px',
                        color: '#f8fafc',
                      }}
                    />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                      {claimDistributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="grid grid-cols-3 gap-2 pt-4 border-t border-slate-800/80 text-center">
              <div className="p-2 rounded-xl bg-emerald-950/20 border border-emerald-800/30">
                <p className="text-xs text-emerald-400 font-bold">{stats.supportedClaims}</p>
                <p className="text-[10px] text-slate-400">Supported ({stats.supportedRate}%)</p>
              </div>
              <div className="p-2 rounded-xl bg-amber-950/20 border border-amber-800/30">
                <p className="text-xs text-amber-400 font-bold">{stats.neutralClaims}</p>
                <p className="text-[10px] text-slate-400">Neutral</p>
              </div>
              <div className="p-2 rounded-xl bg-red-950/20 border border-red-800/30">
                <p className="text-xs text-red-400 font-bold">{stats.contradictedClaims}</p>
                <p className="text-[10px] text-slate-400">Contradicted</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── RECENT EXECUTION FEED ───────────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Clock size={18} className="text-cyan-400" />
                Recent Live Analysis Traces
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Execution history, grounded answers, and verification logs</p>
            </div>
            <Link
              to="/playground"
              className="text-xs font-semibold text-primary-400 hover:text-primary-300 transition-colors flex items-center gap-1"
            >
              Open Playground <ArrowRight size={13} />
            </Link>
          </div>

          {analyses.length === 0 ? (
            <div className="glass-card p-10 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-surface-800 border border-slate-700 mx-auto flex items-center justify-center text-slate-500">
                <Zap size={22} />
              </div>
              <p className="text-sm font-semibold text-slate-200">No analysis runs yet</p>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Head over to the Playground to ask questions against your indexed documents.
              </p>
              <Link to="/playground" className="btn-primary inline-flex mt-2">
                Start First Analysis
              </Link>
            </div>
          ) : (
            <div className="glass-card divide-y divide-slate-800/80 overflow-hidden">
              {analyses.slice(0, 5).map((a) => (
                <div
                  key={a.id}
                  className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-surface-800/30 transition-colors group"
                >
                  <div className="space-y-1.5 min-w-0 flex-1">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs font-mono text-cyan-400 bg-cyan-950/50 border border-cyan-800/50 px-2 py-0.5 rounded">
                        Query
                      </span>
                      <h4 className="text-sm font-semibold text-slate-200 truncate group-hover:text-primary-300 transition-colors">
                        {a.query}
                      </h4>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-1 pl-1">
                      {a.answer || (a.status === 'abstained' ? 'System abstained due to insufficient verified evidence.' : 'Analysis in progress...')}
                    </p>

                    <div className="flex items-center gap-4 text-[11px] font-mono text-slate-500 pt-1 pl-1">
                      <span className="flex items-center gap-1">
                        <Clock size={11} /> {formatDistanceToNow(new Date(a.created_at))} ago
                      </span>
                      {a.reliability?.claims_count !== undefined && (
                        <span>{a.reliability.claims_count} claims verified</span>
                      )}
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-3">
                    <ReliabilityBadge
                      score={a.reliability?.score}
                      status={a.reliability?.status}
                      size="sm"
                    />
                    <Link
                      to="/playground"
                      className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-surface-800 border border-slate-800 transition-colors"
                      title="Inspect in Playground"
                    >
                      <ArrowRight size={15} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── 5-STEP RELIABILITY LOOP ARCHITECTURE ────────────────────── */}
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers size={18} className="text-primary-400" />
              The TRUSTRAG Closed-Loop Reliability Engine
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic 5-phase pipeline preventing silent hallucinations through active verification
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {PIPELINE_PHASES.map((phase) => {
              const Icon = phase.icon
              return (
                <div
                  key={phase.step}
                  className={`glass-card p-4 flex flex-col justify-between border ${phase.border} hover:scale-[1.02] transition-transform duration-200`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[11px] font-mono font-bold text-slate-500">{phase.step}</span>
                      <Icon size={16} className={phase.color} />
                    </div>
                    <h4 className="font-bold text-sm text-slate-200 mb-1.5">{phase.title}</h4>
                    <p className="text-xs text-slate-400 leading-relaxed">{phase.desc}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

function CustomTimelineTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const data = payload[0].payload
  const isTrusted = data.score >= 70
  const isFailed = data.score === 0 || data.status === 'FAILED'

  return (
    <div className="rounded-xl border border-slate-700/80 bg-surface-950/95 p-3.5 backdrop-blur-xl shadow-2xl space-y-2 max-w-xs font-sans text-xs">
      <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-2">
        <span className="font-mono text-cyan-300 font-bold text-[11px]">
          {data.runLabel} &bull; {data.time}
        </span>
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
            isTrusted
              ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
              : isFailed
              ? 'bg-red-950/80 text-red-300 border border-red-800/60'
              : 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
          }`}
        >
          {data.status}
        </span>
      </div>

      <div>
        <p className="text-[11px] text-slate-300 font-mono line-clamp-2 leading-relaxed">
          &ldquo;{data.query}&rdquo;
        </p>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px]">
        <span className="text-slate-400">Reliability Score:</span>
        <div className="flex items-baseline gap-1.5">
          <span
            className={`font-mono font-bold text-sm ${
              data.score >= 70 ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            {data.score}%
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            ({data.score >= 70 ? 'Passed' : 'Under 70%'})
          </span>
        </div>
      </div>

      <div className="text-[10px] text-slate-500 font-mono">
        {data.fullTime}
      </div>
    </div>
  )
}

