import { Layers, AlertTriangle } from 'lucide-react'
import { shortModelId } from '@/lib/modelLabels'

export function EmbeddingModelDisplay({
  selectedEmbeddingModel,
  selectedKb,
  kbEmbeddingPin,
  embeddingMismatch,
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-3 transition-colors hover:border-slate-700/80 shadow-sm">
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>Dense Embedding Model</span>
        </label>
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950/80 text-cyan-400 border border-cyan-800/40">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          Local BGE
        </span>
      </div>

      <div className="flex items-center justify-between gap-2 bg-surface-900 px-2.5 py-2 rounded-lg border border-cyan-500/30">
        <span className="text-xs font-medium text-cyan-200">Local BGE</span>
        <span className="text-[10px] px-1.5 py-[2px] rounded bg-surface-950 border border-slate-700/60 text-cyan-400 font-mono">384d · offline</span>
      </div>

      <div className="space-y-1 pt-1 border-t border-slate-800">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="font-medium">Embedding Model:</span>
          <span className="font-mono text-[10px] text-cyan-400">
            {selectedEmbeddingModel ? `${shortModelId(selectedEmbeddingModel)} · 384d vectors` : ''}
          </span>
        </div>
        {selectedKb && (
          <div className="text-[10px] font-mono text-slate-500">
            KB index: {selectedKb.embedding_model || 'legacy (unknown): re-ingest recommended'}
            {selectedKb.embedding_dim ? ` · ${selectedKb.embedding_dim}d` : ''}
          </div>
        )}
        {embeddingMismatch && kbEmbeddingPin && (
          <div className="w-full flex items-start gap-1.5 rounded-lg border border-amber-500/50 bg-amber-950/40 px-2 py-1.5 text-left text-[11px] text-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 mt-[1px] shrink-0" />
            <span>
              This KB was indexed with <span className="font-mono">{kbEmbeddingPin}</span>.
              Re-upload its documents to re-index with local BGE.
            </span>
          </div>
        )}
      </div>
    </div>
  )
}