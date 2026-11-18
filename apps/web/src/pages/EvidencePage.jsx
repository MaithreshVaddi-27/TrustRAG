import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, FileSearch, Database, Hash, GitMerge } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/common/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import ExplainerList from '@/components/app/ExplainerList'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { evidenceService } from '@/services/api'

const RETRIEVAL_STREAMS = [
  {
    icon: Database,
    title: 'Dense ONNX vectors',
    body: 'Embeddings generated locally with 384-dimensional vectors, matched by cosine distance for semantic concept recall.',
  },
  {
    icon: Hash,
    title: 'Sparse BM25 index',
    body: 'Porter-stemmed exact keyword matching with inverse document frequency, for precise entity and code recall.',
  },
  {
    icon: GitMerge,
    title: 'Reciprocal rank fusion',
    body: 'The two result lists are merged into one calibrated ranking with k = 60, and every chunk keeps its source hash.',
  },
]

export default function EvidencePage() {
  const {
    data: evidence = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['all-evidence'],
    queryFn: evidenceService.list,
  })

  const status =
    isLoading ? 'loading' : isError ? 'error' : evidence.length === 0 ? 'empty' : 'ready'

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <PageHeader
          title="Evidence"
          accent="vault"
          countLabel={
            isError
              ? 'unavailable'
              : isLoading
                ? null
                : `${evidence.length} ${evidence.length === 1 ? 'record' : 'records'}`
          }
          description="Retrieved evidence chunks across every analysis, with provenance, score breakdown and integrity audit."
          actions={
            <Link to="/playground" className="lx-btn lx-btn--attention">
              Run new query
              <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
            </Link>
          }
        />

        <AsyncState
          status={status}
          loadingLabel="Loading retrieved evidence records…"
          errorTitle="Failed to load evidence"
          errorMessage={error?.message}
          onRetry={refetch}
          emptyIcon={FileSearch}
          emptyTitle="No evidence segments retrieved yet"
          emptyBody="Run an analysis in the playground to ingest, score and persist evidence chunks into the audit vault with verified token spans."
          emptyAction={
            <Link to="/playground" className="lx-btn lx-btn--attention">
              Launch a playground analysis
              <ArrowRight size={13} strokeWidth={1.5} aria-hidden="true" />
            </Link>
          }
        />

        {status === 'ready' && <EvidenceViewer chunks={evidence} />}

        {status === 'empty' && (
          <ExplainerList
            title="Dual-stream retrieval and provenance"
            items={RETRIEVAL_STREAMS}
          />
        )}
      </div>
    </AppLayout>
  )
}
