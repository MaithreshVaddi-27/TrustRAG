import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/ui/PageHeader'
import { StatStrip } from '@/components/dashboard/StatStrip'
import { ReliabilityChart } from '@/components/dashboard/ReliabilityChart'
import { ClaimDistributionChart } from '@/components/dashboard/ClaimDistributionChart'
import { ActivityFeed } from '@/components/dashboard/ActivityFeed'
import { AttentionPanel } from '@/components/dashboard/AttentionPanel'
import { WorkspacePanel } from '@/components/dashboard/WorkspacePanel'
import { PipelineArchitecture } from '@/components/dashboard/PipelineArchitecture'
import { DashboardSkeleton } from '@/components/dashboard/DashboardSkeleton'
import { kbService, analysisService, claimService, conflictService } from '@/services/api'
import { normalizeClaimState } from '@/lib/claimState'

/**
 * DashboardPage — the operator's overview.
 *
 * Four questions, in order of how much they matter:
 *
 *   1. What needs my attention?      — AttentionPanel
 *   2. How is the corpus doing?       — StatStrip, WorkspacePanel
 *   3. Is reliability holding?        — the two charts
 *   4. What has happened lately?      — ActivityFeed
 *
 * The pipeline primer is only shown to a workspace that has not run
 * anything yet. After the first run it is noise, and it is duplicated by
 * the playground's own empty state.
 */
export default function DashboardPage() {
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [historyWindow, setHistoryWindow] = useState('10') // '10' | '20' | 'all'

  const {
    data: analyses = [],
    refetch: refetchAnalyses,
    isFetching: isFetchingAnalyses,
    isLoading: isLoadingAnalyses,
    isError: isErrorAnalyses,
    error: analysesError,
    dataUpdatedAt: analysesUpdatedAt,
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
    dataUpdatedAt: claimsUpdatedAt,
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
    dataUpdatedAt: conflictsUpdatedAt,
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
    dataUpdatedAt: kbsUpdatedAt,
  } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list,
    refetchInterval: autoRefresh ? 30000 : false,
  })

  // First paint shows layout-matching skeletons rather than a false "0" state.
  const isInitialLoad = isLoadingAnalyses || isLoadingClaims || isLoadingKbs

  // Surface the first failing feed — silent zeros previously hid outages.
  const loadError = analysesError || kbsError || claimsError || conflictsError
  const hasLoadError =
    isErrorAnalyses || isErrorKbs || isErrorClaims || isErrorConflicts

  // The least fresh feed decides when the workspace is genuinely current.
  // A timestamp that ticks on a timer measures the clock, not the data.
  const stamps = [analysesUpdatedAt, claimsUpdatedAt, conflictsUpdatedAt, kbsUpdatedAt].filter(
    Boolean,
  )
  const lastSync = stamps.length ? Math.min(...stamps) : null

  const handleManualSync = () => {
    refetchAnalyses()
    refetchClaims()
    refetchConflicts()
    refetchKbs()
  }

  const stats = useMemo(() => {
    const totalDocs = kbs.reduce((sum, kb) => sum + (kb.document_count || 0), 0)

    // A run that abstained scores zero because there was no answer, not
    // because the answer was unreliable. Averaging those into "mean
    // reliability" would conflate "no answer" with "a bad answer".
    const answeredRuns = analyses.filter(
      (analysis) =>
        analysis.status === 'completed' &&
        analysis.reliability?.score !== undefined &&
        analysis.reliability?.score !== null,
    )
    const meanScore = answeredRuns.length
      ? answeredRuns.reduce((sum, a) => sum + a.reliability.score, 0) /
        answeredRuns.length
      : null

    let supported = 0
    let contradicted = 0
    let neutral = 0

    claims.forEach((claim) => {
      const state = normalizeClaimState(claim)
      if (state === 'SUPPORTED' || state === 'VERIFIED') supported += 1
      else if (state === 'CONTRADICTED') contradicted += 1
      else neutral += 1
    })

    const totalClaims = supported + contradicted + neutral
    const answered = analyses.filter((a) => a.status === 'completed').length
    const abstained = analyses.filter((a) => a.status === 'abstained').length
    const failed = analyses.filter(
      (a) => a.status === 'failed' || a.status === 'outage',
    ).length
    const running = analyses.filter(
      (a) => a.status === 'pending' || a.status === 'processing',
    ).length

    // The second line of the figure states what happened to the runs, not
    // what they are. A run that abstained still happened.
    const analysisMeta = (() => {
      if (analyses.length === 0) return 'No runs yet'
      const parts = []
      if (answered) parts.push(`${answered} answered`)
      if (abstained + failed) parts.push(`${abstained + failed} without an answer`)
      if (running) parts.push(`${running} running`)
      return parts.join(' · ') || 'No runs yet'
    })()

    const kbNames = Object.fromEntries(kbs.map((kb) => [kb.id, kb.name]))

    // The last run against each collection, so the workspace table can say
    // whether a collection has been exercised recently.
    const lastRunByKb = {}
    for (const analysis of analyses) {
      const id = analysis.knowledge_base_id
      if (!id || lastRunByKb[id]) continue
      lastRunByKb[id] = {
        label: formatDistanceToNow(new Date(analysis.created_at)) + ' ago',
        at: analysis.created_at,
      }
    }

    return {
      figures: {
        'knowledge-bases': {
          value: kbs.length,
          meta: `${totalDocs} ${totalDocs === 1 ? 'document' : 'documents'} indexed`,
        },
        analyses: {
          value: analyses.length,
          meta: analysisMeta,
          alarm: failed > 0,
        },
        reliability: {
          value: meanScore == null ? '—' : `${(meanScore * 100).toFixed(1)}%`,
          meta:
            meanScore == null
              ? 'No verified answers yet'
              : `Threshold 50% · ${answeredRuns.length} ${answeredRuns.length === 1 ? 'answer' : 'answers'}`,
          alarm: meanScore != null && meanScore * 100 < 50,
        },
        claims: {
          value: totalClaims,
          meta: totalClaims
            ? `${supported} supported · ${contradicted} contradicted`
            : 'No claims decomposed yet',
          alarm: contradicted > 0,
        },
      },
      chart: {
        supportedClaims: supported,
        neutralClaims: neutral,
        contradictedClaims: contradicted,
        totalClaimsCount: totalClaims,
        supportedRate: totalClaims ? Math.round((supported / totalClaims) * 100) : 0,
      },
      attention: {
        conflicts,
        contradictedClaims: contradicted,
        failedRuns: abstained + failed,
      },
      lastRunByKb,
      kbNames,
      hasActivity: analyses.length > 0,
    }
  }, [kbs, analyses, claims, conflicts])

  const syncLabel = lastSync
    ? `Synced ${formatDistanceToNow(new Date(lastSync))} ago`
    : 'Never synced'

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <PageHeader
          title="Overview"
          description="The state of your corpus, and the reliability of every answer it has produced."
          countLabel={
            <span className="inline-flex items-center gap-1.5">
              <span
                className={`lx-dot${autoRefresh ? ' lx-dot--live' : ''}`}
                aria-hidden="true"
              />
              {autoRefresh ? 'Live' : 'Paused'}
            </span>
          }
          actions={
            <>
              {/* The sync time sits with the control that performs the sync.
                  In the chip it made the chip's width depend on how long ago
                  the last sync was — so the chip sometimes fit beside the
                  heading and sometimes did not, and the heading moved. */}
              <span className="lx-micro">{syncLabel}</span>

              <button
                type="button"
                onClick={handleManualSync}
                disabled={isFetchingAnalyses}
                className="lx-btn lx-btn--secondary"
                title="Refresh every feed"
              >
                <RefreshCw
                  size={13}
                  strokeWidth={1.75}
                  className={isFetchingAnalyses ? 'animate-spin' : ''}
                  aria-hidden="true"
                />
                <span>Sync now</span>
              </button>

              <button
                type="button"
                onClick={() => setAutoRefresh((previous) => !previous)}
                className="lx-btn lx-btn--quiet"
                aria-pressed={autoRefresh}
              >
                {autoRefresh ? 'Pause stream' : 'Go live'}
              </button>
            </>
          }
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

        {isInitialLoad ? (
          <DashboardSkeleton />
        ) : (
          <>
            <AttentionPanel {...stats.attention} />

            <StatStrip stats={stats} />

            {/* One wide chart beside a narrower one — a rhythm, not two
                equal boxes. */}
            <div className="lx-grid-wide-narrow">
              <ReliabilityChart
                analyses={analyses}
                historyWindow={historyWindow}
                setHistoryWindow={setHistoryWindow}
              />
              <ClaimDistributionChart stats={stats.chart} />
            </div>

            <WorkspacePanel kbs={kbs} lastRunByKb={stats.lastRunByKb} />

            <ActivityFeed analyses={analyses} kbNames={stats.kbNames} />

            {/* The primer is for a workspace that has not run anything yet. */}
            {!stats.hasActivity && <PipelineArchitecture />}
          </>
        )}
      </div>
    </AppLayout>
  )
}
