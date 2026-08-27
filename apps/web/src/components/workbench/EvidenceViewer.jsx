import { clsx } from 'clsx'
import { BookOpen, Calendar, ExternalLink, Hash, Shield, ShieldAlert } from 'lucide-react'

/**
 * EvidenceViewer — shows retrieved evidence chunks with provenance metadata.
 * Props:
 *   chunks: [{ id, text, document_id, filename, retrieval_score, fusion_score,
 *              rerank_score, method, effective_from, effective_until, integrity_status }]
 */
export function EvidenceViewer({ chunks = [] }) {
  if (chunks.length === 0) {
    return (
      <div className="text-slate-500 text-sm py-4 text-center">No evidence retrieved.</div>
    )
  }

  return (
    <div className="space-y-3">
      {chunks.map((chunk, i) => (
        <EvidenceChunk key={chunk.id ?? i} chunk={chunk} rank={i + 1} />
      ))}
    </div>
  )
}

function EvidenceChunk({ chunk, rank }) {
  const integrityOk = chunk.integrity_status === 'ok' || !chunk.integrity_status

  return (
    <div className="glass-card p-4 space-y-3 hover:border-slate-600/60 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-mono text-slate-500 shrink-0">#{rank}</span>
          <BookOpen size={13} className="text-primary-400 shrink-0" />
          <span className="text-sm font-medium text-slate-200 truncate">
            {chunk.filename ?? chunk.document_id ?? 'Unknown source'}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {integrityOk
            ? <Shield size={13} className="text-green-400" title="Source integrity OK" />
            : <ShieldAlert size={13} className="text-amber-400" title={chunk.integrity_status} />
          }
          {chunk.integrity_status && !integrityOk && (
            <span className="text-xs text-amber-400">{chunk.integrity_status}</span>
          )}
        </div>
      </div>

      {/* Evidence text */}
      <blockquote className="border-l-2 border-primary-600/50 pl-3 text-sm text-slate-300 leading-relaxed line-clamp-4">
        {chunk.text}
      </blockquote>

      {/* Scores + metadata */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 font-mono">
        {chunk.retrieval_score != null && (
          <span>dense <span className="text-slate-300">{chunk.retrieval_score.toFixed(3)}</span></span>
        )}
        {chunk.fusion_score != null && (
          <span>rrf <span className="text-slate-300">{chunk.fusion_score.toFixed(3)}</span></span>
        )}
        {chunk.rerank_score != null && (
          <span>rerank <span className="text-slate-300">{chunk.rerank_score.toFixed(3)}</span></span>
        )}
        {chunk.method && (
          <span className="flex items-center gap-1">
            <Hash size={10} /> {chunk.method}
          </span>
        )}
        {(chunk.effective_from || chunk.effective_until) && (
          <span className="flex items-center gap-1 text-amber-500/70">
            <Calendar size={10} />
            {chunk.effective_from && new Date(chunk.effective_from).toLocaleDateString()}
            {chunk.effective_until && ` → ${new Date(chunk.effective_until).toLocaleDateString()}`}
          </span>
        )}
        {chunk.document_id && (
          <span className="flex items-center gap-1 ml-auto">
            <ExternalLink size={10} />
            {String(chunk.document_id).slice(-8)}
          </span>
        )}
      </div>
    </div>
  )
}
