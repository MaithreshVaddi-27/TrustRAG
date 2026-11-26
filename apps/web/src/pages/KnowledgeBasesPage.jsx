import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Database, X } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/common/PageHeader'
import AsyncState from '@/components/app/AsyncState'
import CollectionLedger from '@/components/kb/CollectionLedger'
import CreateCollectionForm from '@/components/kb/CreateCollectionForm'
import { kbService } from '@/services/api'

const SORTS = [
  { id: 'newest', label: 'Newest first' },
  { id: 'name', label: 'Name' },
  { id: 'documents', label: 'Document count' },
]

export default function KnowledgeBasesPage() {
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const [newKbName, setNewKbName] = useState('')
  const [newKbDesc, setNewKbDesc] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('newest')
  const [createError, setCreateError] = useState(null)

  const { data: knowledgeBases = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: kbService.list,
  })

  const createKbMutation = useMutation({
    mutationFn: kbService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] })
      setIsCreating(false)
      setNewKbName('')
      setNewKbDesc('')
      setCreateError(null)
    },
    onError: (err) => {
      setCreateError(err.message || 'Failed to create the collection.')
    },
  })

  const handleCreateSubmit = (event) => {
    event.preventDefault()
    if (!newKbName.trim()) return
    createKbMutation.mutate({ name: newKbName.trim(), description: newKbDesc.trim() })
  }

  const visibleCollections = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()

    const filtered = knowledgeBases.filter(
      (kb) =>
        !term ||
        kb.name.toLowerCase().includes(term) ||
        (kb.description || '').toLowerCase().includes(term),
    )

    return [...filtered].sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name)
      if (sortBy === 'documents') {
        return (b.document_count ?? 0) - (a.document_count ?? 0)
      }
      return (
        new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime()
      )
    })
  }, [knowledgeBases, searchTerm, sortBy])

  const status =
    isLoading
      ? 'loading'
      : isError
        ? 'error'
        : knowledgeBases.length === 0
          ? 'empty'
          : 'ready'

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
              onClick={() => {
                setIsCreating(true)
                setCreateError(null)
              }}
              className={`lx-btn ${isCreating ? 'lx-btn--secondary' : 'lx-btn--primary'}`}
            >
              <Plus size={15} strokeWidth={1.75} aria-hidden="true" />
              <span>New collection</span>
            </button>
          }
        />

        {isCreating && (
          <CreateCollectionForm
            onSubmit={handleCreateSubmit}
            onCancel={() => {
              setIsCreating(false)
              setCreateError(null)
            }}
            error={createError}
            isPending={createKbMutation.isPending}
            name={newKbName}
            description={newKbDesc}
            onNameChange={setNewKbName}
            onDescriptionChange={setNewKbDesc}
          />
        )}

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
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Filter by name or topic"
                aria-label="Filter collections by name or topic"
                className="lx-control pl-9 pr-9"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm('')}
                  className="lx-icon-btn absolute right-1 top-1/2 h-10 w-10 -translate-y-1/2"
                  title="Clear the filter"
                  aria-label="Clear the filter"
                >
                  <X size={13} strokeWidth={1.75} aria-hidden="true" />
                </button>
              )}
            </div>

            <div className="lx-toolbar__group">
              <label className="lx-micro" htmlFor="kb-sort">
                Sort
              </label>
              <select
                id="kb-sort"
                name="kb-sort"
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
                className="lx-control w-auto"
              >
                {SORTS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>

              <span className="lx-micro">
                {visibleCollections.length} of {knowledgeBases.length}
              </span>
            </div>
          </div>
        )}

        <AsyncState
          status={status}
          loadingLabel="Querying the cluster collections…"
          errorTitle="Failed to load knowledge bases"
          errorMessage={error?.message}
          onRetry={refetch}
          emptyIcon={Database}
          emptyTitle="No collections yet"
          emptyBody="Create a collection to upload documents, generate dense embeddings and run grounded queries."
          emptyAction={
            <button
              type="button"
              onClick={() => setIsCreating(true)}
              className="lx-btn lx-btn--secondary"
            >
              <Plus size={15} strokeWidth={1.75} aria-hidden="true" />
              <span>Create a collection</span>
            </button>
          }
        />

        {status === 'ready' && visibleCollections.length === 0 && (
          <div className="lx-panel-block">
            <div className="lx-empty">
              <Search size={20} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
              <p className="lx-empty__title">No collection matches that filter</p>
              <p className="lx-empty__body">
                Clear the filter to see all {knowledgeBases.length} collections.
              </p>
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="lx-btn lx-btn--secondary"
              >
                Clear the filter
              </button>
            </div>
          </div>
        )}

        {status === 'ready' && visibleCollections.length > 0 && (
          <CollectionLedger collections={visibleCollections} />
        )}
      </div>
    </AppLayout>
  )
}
