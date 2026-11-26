import { Layers, AlertTriangle, ShieldCheck } from 'lucide-react'
import { shortModelId } from '@/lib/modelLabels'

/**
 * EmbeddingModelDisplay — the vector engine, and whether it matches.
 *
 * The interesting case is a mismatch: the knowledge base was indexed with
 * a different embedding model than the one now serving queries. That is a
 * correctness problem, so it is the one thing here that carries crimson.
 *
 * Everything else on this panel is read from the registry. It used to say
 * "ONNX runtime" and "384d · offline" in hardcoded strings — a claim about
 * the vector engine that was true on the day it was written and would have
 * stayed true after the engine changed.
 */
export function EmbeddingModelDisplay({
  embedding,
  selectedEmbeddingModel,
  selectedKb,
  kbEmbeddingPin,
  embeddingMismatch,
}) {
  const provider = embedding?.provider
  const dimension = selectedKb?.embedding_dim ?? embedding?.dim ?? null

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="lx-workbench__label !mb-0 flex items-center gap-2">
          <Layers size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
          Dense embedding model
        </span>
        <span className="lx-chip">
          {provider ? provider.toUpperCase() : 'Detecting'}
        </span>
      </div>

      <dl className="lx-deflist">
        <div className="lx-deflist__row">
          <dt className="lx-deflist__key flex items-center gap-2">
            <ShieldCheck size={13} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
            Model
          </dt>
          <dd className="lx-deflist__value">
            {selectedEmbeddingModel
              ? shortModelId(selectedEmbeddingModel)
              : 'Detecting…'}
          </dd>
        </div>

        <div className="lx-deflist__row">
          <dt className="lx-deflist__key">Index vector dimension</dt>
          <dd className="lx-deflist__value">
            {dimension ? `${dimension}d` : '—'}
          </dd>
        </div>

        <div className="lx-deflist__row">
          <dt className="lx-deflist__key">Execution</dt>
          <dd className="lx-deflist__value">
            {provider
              ? `${provider.toUpperCase()} · ${dimension ? `${dimension}d` : 'unknown dim'} · ${
                  embedding?.type === 'cloud' ? 'cloud' : 'local'
                }`
              : '—'}
          </dd>
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
