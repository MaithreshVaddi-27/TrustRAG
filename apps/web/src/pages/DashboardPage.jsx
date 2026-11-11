import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
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

  // Real-time live polling for active telemetry
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

  // First paint shows layout-matching skeletons rather than a false "0" state.
  const isInitialLoad = isLoadingAnalyses || isLoadingClaims || isLoadingKbs
  // Surface the first failing feed — silent zeros previously hid outages.
  const loadError = analysesError || kbsError || claimsError || conflictsError
  const hasLoadError = isErrorAnalyses || isErrorKbs || isErrorClaims || isErrorConflicts

  const updateLastSync = () => setLastSync(new Date())

  // Re-render every 30s so "Synced x ago" never freezes.
  useEffect(() => {
    const t = setInterval(updateLastSync, 30000)
    return () => clearInterval(t)
  }, [])

  const handleManualSync = () => {
    refetchAnalyses()
    refetchClaims()
    refetchConflicts()
    refetchKbs()
    updateLastSync()
  }

  const stats = useMemo(() => {
    const totalDocs = kbs.reduce((sum, kb) => sum + (kb.document_count || 0), 0)

    let totalScore = 0
    let scoredCount = 0
    let supportedClaims = 0
    let contradictedClaims = 0
    let neutralClaims = 0

    analyses.forEach((a) => {
      if (a.reliability?.score !== undefined && a.reliability?.score !== null) {
        totalScore += a.reliability.score
        scoredCount++
      }
    })

    claims.forEach((c) => {
      const s = normalizeClaimState(c)
      if (s === 'SUPPORTED' || s === 'VERIFIED') supportedClaims++
      else if (s === 'CONTRADICTED') contradictedClaims++
      else neutralClaims++
    })

    const avgReliability = scoredCount > 0 ? totalScore / scoredCount : 0
    const avgReliabilityDisplay = scoredCount > 0 ? `${(avgReliability * 100).toFixed(1)}%` : '--'
    const totalClaimsCount = supportedClaims + contradictedClaims + neutralClaims
    const supportedRate = totalClaimsCount > 0 ? (supportedClaims / totalClaimsCount) * 100 : 0

    return {
      totalDocs,
      avgReliability: (avgReliability * 100).toFixed(1),
      avgReliabilityDisplay,
      supportedClaims,
      contradictedClaims,
      neutralClaims,
      totalClaimsCount,
      supportedRate: supportedRate.toFixed(0),
      totalConflicts: conflicts.length,
    }
  }, [kbs, analyses, claims, conflicts])

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <HeroBanner />

        <ObservabilityBar
          autoRefresh={autoRefresh}
          setAutoRefresh={setAutoRefresh}
          lastSync={lastSync}
          isFetchingAnalyses={isFetchingAnalyses}
          handleManualSync={handleManualSync}
        />

        {hasLoadError && !isInitialLoad && (
          <div className="lx-message lx-message--alarm" role="alert">
            <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <span className="lx-message__title">Some dashboard feeds failed to load</span>
              <span className="lx-message__body">
                {loadError?.message ||
                  'An unexpected error occurred. Metrics below may be incomplete.'}
              </span>
            </div>
            <button
              type="button"
              onClick={handleManualSync}
              className="lx-btn lx-btn--secondary shrink-0"
            >
              Retry
            </button>
          </div>
        )}

        <MetricsGrid
          stats={stats}
          kbs={kbs}
          analyses={analyses}
          claims={claims}
          conflicts={conflicts}
        />

        {/* One wide chart beside a narrower one — a rhythm, not two equal boxes. */}
        <div className="lx-grid-wide-narrow">
          <ReliabilityChart
            analyses={analyses}
            historyWindow={historyWindow}
            setHistoryWindow={setHistoryWindow}
          />
          <ClaimDistributionChart stats={stats} />
        </div>

        <RecentAnalysesFeed analyses={analyses} isInitialLoad={isInitialLoad} />

        <PipelineArchitecture />
      </div>
    </AppLayout>
  )
}
