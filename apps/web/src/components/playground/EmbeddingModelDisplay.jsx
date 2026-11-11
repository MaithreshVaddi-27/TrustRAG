import { Layers, AlertTriangle, ShieldCheck } from 'lucide-react'
import { shortModelId } from '@/lib/modelLabels'

/**
 * EmbeddingModelDisplay — the vector engine, and whether it matches.
 *
 * The interesting case is a mismatch: the knowledge base was indexed with a
 * different embedding model than the one now serving queries. That is a
 * correctness problem, so it is the one thing here that carries crimson.
 */
export function EmbeddingModelDisplay({
  selectedEmbeddingModel,
  selectedKb,
  kbEmbeddingPin,
  embeddingMismatch,
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="lx-workbench__label !mb-0 flex items-center gap-2">
          <Layers size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
          Dense embedding model
        </span>
        <span className="lx-chip">ONNX runtime</span>
      </div>

      <dl className="lx-deflist">
        <div className="lx-deflist__row">
          <dt className="lx-deflist__key flex items-center gap-2">
            <ShieldCheck size={13} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
            Model
          </dt>
          <dd className="lx-deflist__value">
            {selectedEmbeddingModel ? shortModelId(selectedEmbeddingModel) : 'bge-small-en-v1.5'}
          </dd>
        </div>

        <div className="lx-deflist__row">
          <dt className="lx-deflist__key">Index vector dimension</dt>
          <dd className="lx-deflist__value">
            {selectedKb?.embedding_dim ? `${selectedKb.embedding_dim}d` : '384d'}
          </dd>
        </div>

        <div className="lx-deflist__row">
          <dt className="lx-deflist__key">Execution</dt>
          <dd className="lx-deflist__value">384d · offline</dd>
        </div>
      </dl>

      {embeddingMismatch && kbEmbeddingPin && (
        <div className="lx-message lx-message--alarm" role="alert">
          <AlertTriangle size={14} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
          <span>
            This knowledge base was indexed with{' '}
            <span className="font-mono">{kbEmbeddingPin}</span>. Re-upload its
            documents to re-index them with the local BGE model.
          </span>
        </div>
      )}
    </div>
  )
}
