import { Layers, AlertTriangle, ShieldCheck } from 'lucide-react'
import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'
import { shortModelId } from '@/lib/modelLabels'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }

export function EmbeddingModelDisplay({
  selectedEmbeddingModel,
  selectedKb,
  kbEmbeddingPin,
  embeddingMismatch,
}) {
  const reduced = useReducedMotion()

  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="rounded-xl border border-slate-800 bg-surface-850/60 p-3 space-y-2.5 transition-colors hover:border-slate-700/80 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
          <Layers className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
          <span>Dense Embedding Model</span>
        </div>
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950/80 text-cyan-400 border border-cyan-800/40">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" aria-hidden="true" />
          ONNX Runtime
        </span>
      </div>

      <motion.div
        initial={reduced ? { opacity: 1 } : { opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={springTransition}
        className="flex items-center justify-between gap-2 bg-surface-900/90 px-2.5 py-2 rounded-lg border border-slate-800"
      >
        <div className="flex items-center gap-2">
          <ShieldCheck size={14} className="text-cyan-400 shrink-0" aria-hidden="true" />
          <div className="text-xs font-medium text-slate-200 font-mono">
            {selectedEmbeddingModel ? shortModelId(selectedEmbeddingModel) : 'bge-small-en-v1.5'}
          </div>
        </div>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-950 border border-slate-800 text-cyan-400 font-mono">
          384d · offline
        </span>
      </motion.div>

      {selectedKb && (
        <motion.div
          initial={reduced ? { opacity: 1 } : { opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ ...springTransition, delay: 0.05 }}
          className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-0.5"
        >
          <span>Index vector dim:</span>
          <span className="text-slate-400">{selectedKb.embedding_dim ? `${selectedKb.embedding_dim}d` : '384d'}</span>
        </motion.div>
      )}

      {embeddingMismatch && kbEmbeddingPin && (
        <motion.div
          initial={reduced ? { opacity: 1, height: 'auto' } : { opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
          transition={reduced ? { duration: 0.01 } : { duration: 0.25, ease: 'easeOut' }}
          className="w-full flex items-start gap-1.5 rounded-lg border border-amber-500/50 bg-amber-950/40 px-2 py-1.5 text-left text-[11px] text-amber-200"
          role="alert"
        >
          <AlertTriangle className="w-3.5 h-3.5 mt-[1px] shrink-0" aria-hidden="true" />
          <span>
            This KB was indexed with <span className="font-mono">{kbEmbeddingPin}</span>.
            Re-upload its documents to re-index with local BGE.
          </span>
        </motion.div>
      )}
    </motion.div>
  )
}