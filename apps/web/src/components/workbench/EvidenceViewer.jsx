import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { BookOpen, Calendar, ExternalLink, Hash, Shield, ShieldAlert, Search, Globe, Database, Copy, Check } from 'lucide-react'

/**
 * EvidenceViewer — Ultra-refined retrieved evidence viewer with live keyword filter,
 * source segregation (KB vs MCP Web), and score bars.
 */
export function EvidenceViewer({ chunks = [] }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sourceFilter, setSourceFilter] = useState('ALL') // 'ALL' | 'KB' | 'WEB'
  const [copiedIndex, setCopiedIndex] = useState(null)

  const counts = useMemo(() => {
    let webCount = 0
    let kbCount = 0
    chunks.forEach(c => {
      if (c.url || c.method?.includes('web') || c.method?.includes('mcp') || c.chunk_id?.startsWith('web_')) {
        webCount++
      } else {
        kbCount++
      }
    })
    return { all: chunks.length, web: webCount, kb: kbCount }
  }, [chunks])

  const filteredChunks = useMemo(() => {
    return chunks.filter(c => {
      const isWeb = Boolean(c.url || c.method?.includes('web') || c.method?.includes('mcp') || c.chunk_id?.startsWith('web_'))
      if (sourceFilter === 'KB' && isWeb) return false
      if (sourceFilter === 'WEB' && !isWeb) return false

      if (!searchTerm.trim()) return true
      const term = searchTerm.toLowerCase()
      const textMatch = (c.text || '').toLowerCase().includes(term)
      const fileMatch = (c.filename || c.document_id || '').toLowerCase().includes(term)
      return textMatch || fileMatch
    })
  }, [chunks, searchTerm, sourceFilter])

  const handleCopy = (text, rank) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(rank)
    setTimeout(() => setCopiedIndex(null), 1800)
  }

  if (chunks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500 border border-slate-800 rounded-2xl bg-surface-900/40">
        <BookOpen size={24} className="text-slate-600 mb-2" />
        <p className="text-sm font-medium text-slate-300">No Evidence Segments Retrieved</p>
        <p className="text-xs text-slate-500 mt-1 max-w-sm">
          No passages matched the hybrid search query thresholds or knowledge base is currently unindexed.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search & Source Filter Bar */}
      <div className="p-3 rounded-xl border border-slate-800 bg-surface-900/60 backdrop-blur-sm flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm">
        {/* Search box */}
        <div className="relative w-full sm:w-72">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Filter evidence text or filename…"
            className="w-full bg-surface-800 border border-slate-700/80 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary-500/50"
          />
        </div>

        {/* Source Pills */}
        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setSourceFilter('ALL')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              sourceFilter === 'ALL'
                ? 'bg-primary-600/30 text-primary-200 border border-primary-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({counts.all})
          </button>
          <button
            type="button"
            onClick={() => setSourceFilter('KB')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
              sourceFilter === 'KB'
                ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database size={12} className="text-indigo-400" />
            <span>Local KB ({counts.kb})</span>
          </button>
          {counts.web > 0 && (
            <button
              type="button"
              onClick={() => setSourceFilter('WEB')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                sourceFilter === 'WEB'
                  ? 'bg-cyan-600/30 text-cyan-200 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Globe size={12} className="text-cyan-400" />
              <span>MCP Web ({counts.web})</span>
            </button>
          )}
        </div>
      </div>

      {/* Chunks List */}
      <div className="space-y-3">
        {filteredChunks.map((chunk, i) => (
          <EvidenceChunk
            key={chunk.chunk_id ?? chunk.id ?? i}
            chunk={chunk}
            rank={i + 1}
            onCopy={() => handleCopy(chunk.text, i + 1)}
            isCopied={copiedIndex === i + 1}
          />
        ))}
      </div>
    </div>
  )
}

function EvidenceChunk({ chunk, rank, onCopy, isCopied }) {
  const [expanded, setExpanded] = useState(false)
  const integrityOk = chunk.integrity_status === 'VERIFIED' || !chunk.integrity_status
  const isWeb = Boolean(chunk.url || chunk.method?.includes('web') || chunk.method?.includes('mcp') || chunk.chunk_id?.startsWith('web_'))
  const isLong = chunk.text && chunk.text.length > 260

  return (
    <div className="glass-card p-4 space-y-3 hover:border-cyan-500/40 hover:shadow-lg transition-all duration-200">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-mono font-bold text-slate-500 shrink-0">#{rank}</span>
          {isWeb ? (
            <Globe size={13} className="text-cyan-400 shrink-0" />
          ) : (
            <BookOpen size={13} className="text-primary-400 shrink-0" />
          )}
          <span className="text-sm font-semibold text-slate-200 truncate">
            {chunk.filename ?? chunk.document_id ?? (isWeb ? 'MCP Web Citation' : 'Unknown source')}
          </span>
          {isWeb && (
            <span className="px-1.5 py-[2px] rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/40 text-[9px] font-mono shrink-0">
              MCP
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onCopy}
            className="text-slate-500 hover:text-slate-300 p-1 rounded hover:bg-surface-800 transition-colors"
            title="Copy evidence snippet"
          >
            {isCopied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
          </button>
          {integrityOk
            ? <Shield size={13} className="text-emerald-400" title="Cryptographic provenance verified" />
            : <ShieldAlert size={13} className="text-amber-400" title={chunk.integrity_status} />
          }
          {chunk.integrity_status && !integrityOk && (
            <span className="text-xs text-amber-400">{chunk.integrity_status}</span>
          )}
        </div>
      </div>

      {/* Evidence text with expand/collapse */}
      <div className="space-y-1.5">
        <blockquote className={clsx(
          "border-l-2 pl-3 text-sm text-slate-300 leading-relaxed break-words font-normal",
          isWeb ? "border-cyan-500/60 bg-cyan-950/10 py-1 rounded-r-md" : "border-primary-600/60 bg-surface-900/40 py-1 rounded-r-md",
          !expanded && isLong && "line-clamp-4"
        )}>
          {chunk.text}
        </blockquote>
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded(e => !e)}
            className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium pl-3 transition-colors"
          >
            {expanded ? 'Show less ▲' : 'Read full segment ▼'}
          </button>
        )}
      </div>

      {/* Scores + metadata */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-1 border-t border-slate-800/60 text-xs text-slate-500 font-mono">
        {chunk.dense_score != null || chunk.retrieval_score != null ? (
          <span className="flex items-center gap-1">
            dense: <span className="text-slate-300 font-bold">{(chunk.dense_score ?? chunk.retrieval_score).toFixed(3)}</span>
          </span>
        ) : null}
        {chunk.rrf_score != null || chunk.fusion_score != null ? (
          <span className="flex items-center gap-1">
            rrf: <span className="text-slate-300 font-bold">{(chunk.rrf_score ?? chunk.fusion_score).toFixed(3)}</span>
          </span>
        ) : null}
        {chunk.rerank_score != null && (
          <span className="flex items-center gap-1">
            rerank: <span className="text-slate-300 font-bold">{chunk.rerank_score.toFixed(3)}</span>
          </span>
        )}
        {chunk.method && (
          <span className="flex items-center gap-1 text-[11px] text-slate-400">
            <Hash size={10} /> {chunk.method}
          </span>
        )}
        {(chunk.effective_from || chunk.effective_until) && (
          <span className="flex items-center gap-1 text-amber-400/80">
            <Calendar size={10} />
            {chunk.effective_from && new Date(chunk.effective_from).toLocaleDateString()}
            {chunk.effective_until && ` → ${new Date(chunk.effective_until).toLocaleDateString()}`}
          </span>
        )}
        {chunk.url ? (
          <a
            href={chunk.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan-400 hover:text-cyan-300 underline flex items-center gap-1 ml-auto font-sans text-[11px]"
          >
            <span>Direct Citation</span>
            <ExternalLink size={10} />
          </a>
        ) : null}
      </div>
    </div>
  )
}
