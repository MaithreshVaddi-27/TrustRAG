import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, Brain } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/ui/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import ExplainerList from '@/components/app/ExplainerList'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'
import { claimService } from '@/services/api'

const NLI_CLASSES = [
  {
    icon: Brain,
    title: 'Supported — entailment',
    body: 'The proposition is explicitly substantiated by the cited evidence spans, with a confidence of 0.70 or above.',
  },
  {
    icon: Brain,
    title: 'Contradicted — refutation',
    body: 'The assertion directly conflicts with the grounded evidence. This triggers the automatic healing loop.',
    tone: 'alarm',
  },
  {
    icon: Brain,
    title: 'Neutral — unverified',
    body: 'Neither confirmed nor refuted by the evidence. Treated as ungrounded extrapolation.',
    tone: 'quiet',
  },
]

export default function ClaimsPage() {
  const {
    data: claims = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['all-claims'],
    queryFn: claimService.list,
  })

  const status = isLoading ? 'loading' : isError ? 'error' : claims.length === 0 ? 'empty' : 'ready'

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <PageHeader
          title="Atomic"
          accent="claims"
          countLabel={
            isError
              ? 'unavailable'
              : isLoading
                ? null
                : `${claims.length} ${claims.length === 1 ? 'claim' : 'claims'}`
          }
          description="Atomic assertions decomposed from model answers, each verified against its cited evidence by natural language inference."
          actions={
            <Link to="/playground" className="lx-btn lx-btn--primary">
              Run new query
              <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
            </Link>
          }
        />

        <AsyncState
          status={status}
          loadingLabel="Loading verified claim records…"
          errorTitle="Failed to load claims"
          errorMessage={error?.message}
          onRetry={refetch}
          emptyIcon={Brain}
          emptyTitle="No claims extracted yet"
          emptyBody="Run an analysis in the playground to decompose a response into atomic propositions and verify each one."
          emptyAction={
            <Link to="/playground" className="lx-btn lx-btn--primary">
              Decompose claims in the playground
              <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
            </Link>
          }
        />

        {status === 'ready' && <ClaimInspector claims={claims} />}

        {status === 'empty' && (
          <ExplainerList
            title="Natural language inference classifications"
            items={NLI_CLASSES}
          />
        )}
      </div>
    </AppLayout>
  )
}
