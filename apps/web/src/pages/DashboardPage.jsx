import { useState, useMemo, useEffect } from 'react'
import { motion } from 'motion/react'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { HeroBanner } from '@/components/dashboard/HeroBanner'
import { ObservabilityBar } from '@/components/dashboard/ObservabilityBar'
import { MetricsGrid } from '@/components/dashboard/MetricsGrid'
import { ReliabilityChart } from '@/components/dashboard/ReliabilityChart'
import { ClaimDistributionChart } from '@/components/dashboard/ClaimDistributionChart'
import { RecentAnalysesFeed } from '@/components/dashboard/RecentAnalysesFeed'
import { PipelineArchitecture } from '@/components/dashboard/PipelineArchitecture'
import { kbService, analysisService, claimService, conflictService } from '@/services/api'
import { normalizeClaimState } from '@/lib/claimState'

export default function DashboardPage() {
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [historyWindow, setHistoryWindow] = useState('10') // '10' | '20' | 'all'
  const [lastSync, setLastSync] = useState(new Date())
  const [, setTick] = useState(0)

  // Re-render every 30s so "Synced x ago" never freezes (N-82).
  useEffect(() => {
    const t = setInterval(() => setTick(x => x + 1), 30000)
    return () => clearInterval(t)
  }, [])

  // Real-time live polling every 3 seconds for active telemetry
  const {
    data: analyses = [],
    refetch: refetchAnalyses,
    isFetching: isFetchingAnalyses,
    isLoading: isLoadingAnalyses,
    isError: isErrorAnalyses,
    error: analysesError,
  } = useQuery({
    queryKey: ['analyses'],
    queryFn: analysisService.list,
    refetchInterval: autoRefresh ? 5000 : false,
  })

  const {
    data: claims = [],
    refetch: refetchClaims,
    isLoading: isLoadingClaims,
    isError: isErrorClaims,
    error: claimsError,
  } = useQuery({
    queryKey: ['all-claims'],
    queryFn: claimService.list,
    refetchInterval: autoRefresh ? 15000 : false,
  })

  const {
    data: conflicts = [],
    refetch: refetchConflicts,
    isError: isErrorConflicts,
    error: conflictsError,
  } = useQuery({
    queryKey: ['all-conflicts'],
    queryFn: conflictService.list,
    refetchInterval: autoRefresh ? 15000 : false,
  })

  const {
    data: kbs = [],
    refetch: refetchKbs,
    isLoading: isLoadingKbs,
    isError: isErrorKbs,
    error: kbsError,
  } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list,
    refetchInterval: autoRefresh ? 30000 : false,
  })

  // First paint: show layout-matching skeletons instead of a false "0" state.
  const isInitialLoad = isLoadingAnalyses || isLoadingClaims || isLoadingKbs
  // Surface the first failing feed — silent zeros previously hid outages.
  const loadError = analysesError || kbsError || claimsError || conflictsError
  const hasLoadError = isErrorAnalyses || isErrorKbs || isErrorClaims || isErrorConflicts

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
      const s = normalizeClaimState(c)
      if (s === 'SUPPORTED' || s === 'VERIFIED') supportedClaims++
      else if (s === 'CONTRADICTED') contradictedClaims++
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

  return (
    <AppLayout>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200, delay: 0.1 }}
        className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-8"
      >
        {/* ── HERO BANNER ─────────────────────────────────────────────── */}
        <HeroBanner />

        {/* ── LIVE OBSERVABILITY CONTROL BAR ────────────────────────────── */}
        <ObservabilityBar
          autoRefresh={autoRefresh}
          setAutoRefresh={setAutoRefresh}
          lastSync={lastSync}
          setLastSync={setLastSync}
          isFetchingAnalyses={isFetchingAnalyses}
          handleManualSync={handleManualSync}
          analyses={analyses}
          claims={claims}
        />

        {/* ── LOAD STATE: error banner + first-paint skeletons ──────────── */}
        {hasLoadError && !isInitialLoad && (
          <div
            role="alert"
            className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 rounded-2xl border border-red-800/50 bg-red-950/30"
          >
            <div className="flex items-start gap-2.5">
              <span className="text-red-400 mt-0.5 shrink-0">⚠</span>
              <div>
                <p className="text-xs font-semibold text-red-300">Some dashboard feeds failed to load</p>
                <p className="text-[11px] text-red-400/80 mt-0.5">
                  {loadError?.message || 'An unexpected error occurred. Metrics below may be incomplete.'}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleManualSync}
              className="px-3 py-1.5 rounded-xl bg-red-950/60 hover:bg-red-900/50 border border-red-800/60 text-red-200 text-xs font-semibold transition-all shrink-0"
            >
              Retry
            </button>
          </div>
        )}

        {/* ── 4 HERO METRIC CARDS ─────────────────────────────────────── */}
        <MetricsGrid
          stats={stats}
          kbs={kbs}
          analyses={analyses}
          claims={claims}
          conflicts={conflicts}
        />

        {/* ── ANALYTICS VISUALIZATIONS ────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Reliability Score History AreaChart */}
          <ReliabilityChart
            analyses={analyses}
            historyWindow={historyWindow}
            setHistoryWindow={setHistoryWindow}
          />

          {/* Claim Verification Breakdown BarChart */}
          <ClaimDistributionChart stats={stats} />
        </div>

        {/* ── RECENT EXECUTION FEED ───────────────────────────────────── */}
        <RecentAnalysesFeed
          analyses={analyses}
          isInitialLoad={isInitialLoad}
        />

        {/* ── 5-STEP RELIABILITY LOOP ARCHITECTURE ────────────────────── */}
        <PipelineArchitecture />
      </motion.div>
    </AppLayout>
  )
}