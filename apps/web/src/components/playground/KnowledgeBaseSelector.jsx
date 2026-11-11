import { Database } from 'lucide-react'
import { motion } from 'motion/react'
import { useReducedMotion } from 'motion/react'

const SPRING_SNAPPY = { type: 'spring', damping: 28, stiffness: 220 }

export function KnowledgeBaseSelector({ kbId, setKbId, knowledgeBases = [], selectedKb, loading, disabled }) {
  const reduced = useReducedMotion()

  const springTransition = reduced ? { duration: 0.01 } : SPRING_SNAPPY

  return (
    <motion.div
      initial={reduced ? { opacity: 1 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springTransition}
      className="space-y-1.5"
    >
      <div className="flex items-center justify-between text-xs">
        <label className="section-heading !mb-0" htmlFor="kb-select">
          Knowledge Base
        </label>
        {selectedKb && (
          <motion.span
            className="text-[10px] text-slate-400 font-mono"
            initial={reduced ? { opacity: 1 } : { opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={springTransition}
          >
            {selectedKb.document_count ?? 0} docs
          </motion.span>
        )}
      </div>
      <div className="relative">
        <Database
          size={13}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
          aria-hidden="true"
        />
        <select
          id="kb-select"
          name="kbId"
          aria-label="Select Knowledge Base"
          value={kbId}
          onChange={(e) => setKbId(e.target.value)}
          className="w-full bg-surface-800 border border-slate-700/80 rounded-xl pl-8 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50 appearance-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={loading || disabled}
          style={{ minHeight: '44px' }}
        >
          <option value="">— select a KB —</option>
          {knowledgeBases?.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name} ({kb.document_count ?? 0} docs)
            </option>
          ))}
        </select>
      </div>
      {selectedKb && selectedKb.document_count === 0 && (
        <motion.p
          className="text-[10px] text-amber-400/90 leading-tight flex items-center gap-1.5"
          initial={reduced ? { opacity: 1 } : { opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={springTransition}
          role="alert"
        >
          <span className="w-3 h-3 shrink-0" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </span>
          <span>
            Selected knowledge base contains 0 indexed documents. Upload documents in the Knowledge Bases tab.
          </span>
        </motion.p>
      )}
    </motion.div>
  )
}