import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  ShieldAlert,
  ShieldCheck,
  Scale,
  CheckCircle,
  RefreshCw,
} from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/ui/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import ExplainerList from '@/components/app/ExplainerList'
import { conflictService } from '@/services/api'

const CONFLICT_KINDS = [
  {
    icon: ShieldAlert,
    title: 'Cross-document divergence',
    body: 'Identifies semantic conflicts between distinct files in the same knowledge base partition, so synthesis never silently picks a winner.',
  },
  {
    icon: ShieldCheck,
    title: 'Entailment refutation guard',
    body: 'A refutation score above 0.70 triggers query reformulation and retrieves corroborating citations to resolve the ambiguity.',
  },
]

export default function ConflictsPage() {
  const {
    data: conflicts = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['all-conflicts'],
    queryFn: conflictService.list,
  })

  const status =
    isLoading ? 'loading' : isError ? 'error' : conflicts.length === 0 ? 'empty' : 'ready'

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <PageHeader
          title="Source and claim"
          accent="conflicts"
          countLabel={`${conflicts.length} ${conflicts.length === 1 ? 'conflict' : 'conflicts'}`}
          description="Contradictions and integrity flags detected across document versions and queries."
          actions={
            <Link to="/playground" className="lx-btn lx-btn--primary">
              Run new query
              <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
            </Link>
          }
        />

        <AsyncState
          status={status}
          loadingLabel="Auditing source conflicts…"
          errorTitle="Failed to load conflicts"
          errorMessage={error?.message}
          onRetry={refetch}
          emptyIcon={CheckCircle}
          emptyTitle="No active conflicts detected"
          emptyBody="Every claim processed so far is coherent with its evidence, with no contradictory assertions or integrity violations."
          emptyAction={
            <Link to="/playground" className="lx-btn lx-btn--secondary">
              <RefreshCw size={13} strokeWidth={1.5} aria-hidden="true" />
              Test adversarial prompts in the playground
              <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
            </Link>
          }
        />

        {status === 'ready' && (
          <div className="lx-panel-block">
            <div className="lx-list">
              {conflicts.map((conflict) => (
                <article key={conflict.id} className="lx-list__item">
                  <div className="lx-list__head">
                    <h2 className="lx-list__title flex items-center gap-2">
                      <ShieldAlert
                        size={15}
                        strokeWidth={1.75}
                        className="text-crimson-400 shrink-0"
                        aria-hidden="true"
                      />
                      {conflict.title}
                    </h2>
                    <span className="lx-chip lx-chip--alarm">{conflict.type}</span>
                  </div>

                  <blockquote className="lx-body mt-3 border-l border-[color:var(--rule-strong)] pl-3 max-w-[70ch]">
                    {conflict.claim}
                  </blockquote>

                  {conflict.explanation && (
                    <p className="lx-body-sm mt-3 max-w-[70ch]">
                      <span className="text-silver-300 font-medium">Explanation: </span>
                      {conflict.explanation}
                    </p>
                  )}

                  {conflict.query && (
                    <div className="lx-list__meta">
                      <span className="text-silver-400">Query</span>
                      <span>{conflict.query}</span>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
        )}

        {status === 'empty' && (
          <ExplainerList
            title="Conflict resolution and self-healing protocol"
            icon={Scale}
            items={CONFLICT_KINDS}
          />
        )}
      </div>
    </AppLayout>
  )
}
