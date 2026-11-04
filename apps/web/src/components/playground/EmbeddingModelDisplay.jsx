import { Layers, AlertTriangle, ShieldCheck } from 'lucide-react'
import { shortModelId } from '@/lib/modelLabels'

export function EmbeddingModelDisplay({
  selectedEmbeddingModel,
  selectedKb,
  kbEmbeddingPin,
  embeddingMismatch,
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-2.5 transition-colors hover:border-slate-700/80 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>Dense Embedding Model</span>
        </div>
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950/80 text-cyan-400 border border-cyan-800/40">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          ONNX Runtime
        </span>
      </div>

      <div className="flex items-center justify-between gap-2 bg-surface-900/90 px-2.5 py-2 rounded-lg border border-slate-800">
        <div className="flex items-center gap-2">
          <ShieldCheck size={14} className="text-cyan-400 shrink-0" />
          <div className="text-xs font-medium text-slate-200 font-mono">
            {selectedEmbeddingModel ? shortModelId(selectedEmbeddingModel) : 'bge-small-en-v1.5'}
          </div>
        </div>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-950 border border-slate-800 text-cyan-400 font-mono">
          384d · offline
        </span>
      </div>

      {selectedKb && (
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-0.5">
          <span>Index vector dim:</span>
          <span className="text-slate-400">{selectedKb.embedding_dim ? `${selectedKb.embedding_dim}d` : '384d'}</span>
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
  )
}