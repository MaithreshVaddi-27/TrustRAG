import { memo, useMemo, useState } from 'react'
import { BookOpen, Search, Globe, Database } from 'lucide-react'
import EvidenceChunk from './EvidenceChunk'
import { copyToClipboard } from '@/lib/clipboard'
import { isWebSource } from '@/lib/claimState'

/**
 * EvidenceViewer — the retrieved passages, with their provenance.
 *
 * Three filters: where the passage came from, how it was retrieved, and a
 * free-text filter over the passage and its filename. The counts in the
 * source filter are always shown, so a reader can see how much of the
 * evidence is web-sourced without switching filter.
 *
 * Memoized (FE-M3): re-renders only when the chunks array reference changes.
 */
const SOURCES = [
  { id: 'ALL', label: 'All' },
  { id: 'KB', label: 'Local KB', icon: Database },
  { id: 'WEB', label: 'MCP web', icon: Globe },
]

export const EvidenceViewer = memo(function EvidenceViewer({ chunks = [] }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sourceFilter, setSourceFilter] = useState('ALL')
  const [methodFilter, setMethodFilter] = useState('ALL')
  const [copiedIndex, setCopiedIndex] = useState(null)

  const counts = useMemo(() => {
    let web = 0
    let kb = 0
    chunks.forEach((chunk) => {
      if (isWebSource(chunk)) web += 1
      else kb += 1
    })
    return { all: chunks.length, web, kb }
  }, [chunks])

  const filteredChunks = useMemo(
    () =>
      chunks.filter((chunk) => {
        const isWeb = isWebSource(chunk)
        if (sourceFilter === 'KB' && isWeb) return false
        if (sourceFilter === 'WEB' && !isWeb) return false

        if (
          methodFilter !== 'ALL' &&
          chunk.method?.toLowerCase() !== methodFilter.toLowerCase()
        ) {
          return false
        }

        if (!searchTerm.trim()) return true
        const term = searchTerm.toLowerCase()
        const textMatch = (chunk.text || '').toLowerCase().includes(term)
        const fileMatch = (chunk.filename || chunk.document_id || '')
          .toLowerCase()
          .includes(term)
        return textMatch || fileMatch
      }),
    [chunks, searchTerm, sourceFilter, methodFilter],
  )

  const handleCopy = async (text, rank) => {
    const ok = await copyToClipboard(text)
    if (!ok) return
    setCopiedIndex(rank)
    setTimeout(() => setCopiedIndex(null), 1800)
  }

  if (chunks.length === 0) {
    return (
      <div className="lx-panel-block">
        <div className="lx-empty">
          <BookOpen size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
          <p className="lx-empty__title">No evidence segments retrieved</p>
          <p className="lx-empty__body">
            No passages matched the hybrid search thresholds, or the knowledge
            base has not been indexed yet.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="lx-toolbar">
        <div className="relative w-full max-w-xs">
          <Search
            size={14}
            strokeWidth={1.75}
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-silver-500"
          />
          <input
            id="evidence-search-input"
            name="evidence-search"
            type="search"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Filter the evidence text or filename"
            aria-label="Filter the evidence text or filename"
            className="lx-control pl-9"
          />
        </div>

        <div className="lx-toolbar__group">
          <select
            id="evidence-method-filter"
            name="evidence-method"
            value={methodFilter}
            onChange={(event) => setMethodFilter(event.target.value)}
            aria-label="Filter by retrieval method"
            className="lx-control w-auto"
          >
            <option value="ALL">All methods</option>
            <option value="hybrid">Hybrid</option>
            <option value="dense">Dense</option>
            <option value="sparse">Sparse</option>
          </select>

          <div className="lx-tabs" role="group" aria-label="Filter by evidence source">
            {SOURCES.map((source) => {
              const count = counts[source.id.toLowerCase()] ?? 0
              if (source.id === 'WEB' && counts.web === 0) return null
              const Icon = source.icon
              return (
                <button
                  key={source.id}
                  type="button"
                  onClick={() => setSourceFilter(source.id)}
                  aria-pressed={sourceFilter === source.id}
                  className="lx-tab"
                >
                  {Icon && <Icon size={12} strokeWidth={1.75} aria-hidden="true" />}
                  {source.label}
                  <span className="ml-1 font-mono text-[0.625rem] text-silver-500">{count}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {filteredChunks.length === 0 ? (
        <div className="lx-panel-block">
          <div className="lx-empty">
            <Search size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            <p className="lx-empty__title">No passage matches this filter</p>
            <p className="lx-empty__body">
              Clear the search term, or choose a different source or retrieval
              method.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredChunks.map((chunk) => {
            const rank = chunks.indexOf(chunk) + 1
            return (
              <EvidenceChunk
                key={chunk.chunk_id ?? chunk.id ?? rank}
                chunk={chunk}
                rank={rank}
                onCopy={() => handleCopy(chunk.text, rank)}
                isCopied={copiedIndex === rank}
              />
            )
          })}
        </div>
      )}
    </div>
  )
})
