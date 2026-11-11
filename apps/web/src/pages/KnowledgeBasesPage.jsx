import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Database, File } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/ui/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import KnowledgeBaseCard from '@/components/kb/KnowledgeBaseCard'
import CreateKnowledgeBaseDialog from '@/components/kb/CreateKnowledgeBaseDialog'
import { kbService } from '@/services/api'

const FORMATS = [
  'PDF (.pdf)',
  'Word (.docx)',
  'Markdown (.md)',
  'Text (.txt)',
  'CSV (.csv)',
  'JSON (.json)',
  'HTML (.html)',
]

export default function KnowledgeBasesPage() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newKbName, setNewKbName] = useState('')
  const [newKbDesc, setNewKbDesc] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [createError, setCreateError] = useState(null)

  const { data: knowledgeBases = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list,
  })

  const createKbMutation = useMutation({
    mutationFn: kbService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
      setIsCreateOpen(false)
      setNewKbName('')
      setNewKbDesc('')
      setCreateError(null)
    },
    onError: (err) => {
      setCreateError(err.message || 'Failed to create the knowledge base.')
    },
  })

  const handleCreateSubmit = (event) => {
    event.preventDefault()
    if (!newKbName.trim()) return
    createKbMutation.mutate({ name: newKbName, description: newKbDesc })
  }

  const filteredKbs = knowledgeBases.filter(
    (kb) =>
      !searchTerm ||
      kb.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (kb.description || '').toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const status =
    isLoading ? 'loading' : isError ? 'error' : knowledgeBases.length === 0 ? 'empty' : 'ready'

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <PageHeader
          title="Knowledge"
          accent="bases"
          countLabel={`${knowledgeBases.length} ${knowledgeBases.length === 1 ? 'collection' : 'collections'}`}
          description="Document repositories partitioned with multi-dimensional dense and sparse BM25 indexing."
          actions={
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="lx-btn lx-btn--primary"
            >
              <Plus size={15} strokeWidth={1.75} aria-hidden="true" />
              <span>New knowledge base</span>
            </button>
          }
        />

        {!isLoading && knowledgeBases.length > 0 && (
          <div className="lx-toolbar">
            <div className="relative w-full max-w-md">
              <Search
                size={15}
                strokeWidth={1.5}
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-silver-500"
              />
              <input
                id="kb-search-filter"
                name="kb-search"
                type="search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter by name or topic"
                aria-label="Filter knowledge bases by name or topic"
                className="lx-control pl-9"
              />
            </div>
            <span className="lx-micro">
              {filteredKbs.length} of {knowledgeBases.length} collections
            </span>
          </div>
        )}

        <AsyncState
          status={status}
          loadingLabel="Querying the cluster collections…"
          errorTitle="Failed to load knowledge bases"
          errorMessage={error?.message}
          onRetry={refetch}
          emptyIcon={Database}
          emptyTitle="No knowledge bases yet"
          emptyBody="Create a collection to upload documents, generate dense embeddings and run grounded queries."
          emptyAction={
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="lx-btn lx-btn--primary"
            >
              <Plus size={15} strokeWidth={1.75} aria-hidden="true" />
              <span>Create a collection</span>
            </button>
          }
        />

        {status === 'ready' && (
          <div className="lx-stack">
            {filteredKbs.length === 0 ? (
              <div className="lx-panel-block">
                <div className="lx-empty">
                  <Search size={20} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
                  <p className="lx-empty__title">No collection matches that filter</p>
                  <p className="lx-empty__body">
                    Clear the filter to see all {knowledgeBases.length} collections.
                  </p>
                </div>
              </div>
            ) : (
              filteredKbs.map((kb) => <KnowledgeBaseCard key={kb.id} kb={kb} />)
            )}
          </div>
        )}

        <section className="lx-panel-block">
          <div className="lx-panel-block__head">
            <h2 className="lx-panel-block__title">Supported document formats</h2>
          </div>
          <div className="lx-panel-block__body">
            <div className="flex flex-wrap gap-2">
              {FORMATS.map((format) => (
                <span key={format} className="lx-chip">
                  <File size={11} strokeWidth={1.75} aria-hidden="true" />
                  {format}
                </span>
              ))}
            </div>
          </div>
          <div className="lx-panel-block__foot">
            <p className="lx-micro">
              Documents undergo Porter stemming and zone weighting (title 3.0×,
              abstract 2.0×), then are indexed with 384-dimensional dense
              embeddings generated locally by BGE.
            </p>
          </div>
        </section>
      </div>

      <CreateKnowledgeBaseDialog
        open={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false)
          setCreateError(null)
        }}
        onSubmit={handleCreateSubmit}
        error={createError}
        isPending={createKbMutation.isPending}
        name={newKbName}
        description={newKbDesc}
        onNameChange={setNewKbName}
        onDescriptionChange={setNewKbDesc}
      />
    </AppLayout>
  )
}
