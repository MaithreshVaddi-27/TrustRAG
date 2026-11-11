import { Database } from 'lucide-react'

/**
 * KnowledgeBaseSelector — which corpus the question is asked against.
 *
 * The document count sits beside the label, because a knowledge base with
 * no documents is a knowledge base that cannot answer anything. That case
 * is called out explicitly rather than left to be discovered.
 */
export function KnowledgeBaseSelector({
  kbId,
  setKbId,
  knowledgeBases = [],
  selectedKb,
  loading,
  disabled,
}) {
  const isEmpty = selectedKb && selectedKb.document_count === 0

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <label className="lx-workbench__label !mb-0" htmlFor="kb-select">
          Knowledge base
        </label>
        {selectedKb && (
          <span className="lx-micro">{selectedKb.document_count ?? 0} docs</span>
        )}
      </div>

      <div className="relative">
        <Database
          size={13}
          strokeWidth={1.5}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-silver-500"
          aria-hidden="true"
        />
        <select
          id="kb-select"
          name="kbId"
          aria-label="Select the knowledge base"
          value={kbId}
          onChange={(event) => setKbId(event.target.value)}
          className="lx-control pl-8"
          disabled={loading || disabled}
        >
          <option value="">Select a knowledge base</option>
          {knowledgeBases?.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name} ({kb.document_count ?? 0} docs)
            </option>
          ))}
        </select>
      </div>

      {isEmpty && (
        <p className="lx-micro flex items-start gap-2" role="alert">
          <span
            className="mt-0.5 h-3 w-3 shrink-0 rounded-full border border-[color:var(--color-crimson-500)]"
            aria-hidden="true"
          />
          <span style={{ color: 'var(--color-crimson-300)' }}>
            This knowledge base has no indexed documents. Upload documents on the
            knowledge bases screen before querying it.
          </span>
        </p>
      )}
    </div>
  )
}
