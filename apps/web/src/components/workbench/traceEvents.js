import {
  AlertTriangle, CheckCircle2,
  Circle, RefreshCw, XCircle,
} from 'lucide-react'

export const TraceEventType = {
  ANALYSIS_STARTED: 'analysis.started',
  RETRIEVAL_STARTED: 'retrieval.started',
  RETRIEVAL_EMPTY: 'retrieval.empty',
  RETRIEVAL_COMPLETED: 'retrieval.completed',
  RETRIEVAL_OUTAGE: 'retrieval.outage',
  INTEGRITY_FAILED: 'integrity.failed',
  GENERATION_STARTED: 'generation.started',
  GENERATION_COMPLETED: 'generation.completed',
  GENERATION_SKIPPED: 'generation.skipped',
  CLAIMS_STARTED: 'claims.started',
  CLAIMS_DECOMPOSED: 'claims.decomposed',
  CLAIMS_VERIFIED: 'claims.verified',
  VERIFICATION_STARTED: 'verification.started',
  VERIFICATION_COMPLETED: 'verification.completed',
  CACHE_HIT: 'cache.hit',
  RECOVERY_STARTED: 'recovery.started',
  RECOVERY_COMPLETED: 'recovery.completed',
  RECOVERY_REWRITE: 'recovery.rewrite',
  RECOVERY_RE_RETRIEVE: 'recovery.re_retrieve',
  RECOVERY_REGENERATE: 'recovery.regenerate',
  RECOVERY_SKIPPED: 'recovery.skipped',
  RECOVERY_RE_RETRIEVE_SKIPPED: 'recovery.re_retrieve_skipped',
  RETRIEVAL_REUSED: 'retrieval.reused',
  RETRIEVAL_CAPPED: 'retrieval.capped',
  GENERATION_DEGENERATE: 'generation.degenerate',
  CLAIMS_EMPTY: 'claims.empty',
  ANALYSIS_COMPLETED: 'analysis.completed',
  ANALYSIS_ABSTAINED: 'analysis.abstained',
  ANALYSIS_FAILED: 'analysis.failed',
}

export const EVENT_META = {
  [TraceEventType.ANALYSIS_STARTED]:      { icon: Circle,        color: 'text-primary-400', label: 'Analysis started' },
  [TraceEventType.RETRIEVAL_STARTED]:     { icon: Circle,        color: 'text-cyan-400',    label: 'Hybrid retrieval started' },
  [TraceEventType.RETRIEVAL_EMPTY]:       { icon: AlertTriangle, color: 'text-amber-400',   label: 'Knowledge base empty' },
  [TraceEventType.RETRIEVAL_COMPLETED]:   { icon: CheckCircle2,  color: 'text-blue-400',    label: 'Retrieval completed' },
  [TraceEventType.INTEGRITY_FAILED]:      { icon: AlertTriangle, color: 'text-amber-400',   label: 'Integrity check failed' },
  [TraceEventType.GENERATION_STARTED]:    { icon: Circle,        color: 'text-sky-400',     label: 'Grounded generation started' },
  [TraceEventType.GENERATION_COMPLETED]:  { icon: CheckCircle2,  color: 'text-sky-400',     label: 'Generation completed' },
  [TraceEventType.CLAIMS_STARTED]:        { icon: Circle,        color: 'text-primary-400', label: 'Claim decomposition started' },
  [TraceEventType.CLAIMS_DECOMPOSED]:     { icon: CheckCircle2,  color: 'text-primary-400', label: 'Claims decomposed' },
  [TraceEventType.CLAIMS_VERIFIED]:       { icon: CheckCircle2,  color: 'text-emerald-400', label: 'Claims verified' },
  [TraceEventType.VERIFICATION_STARTED]:  { icon: Circle,        color: 'text-cyan-400',    label: 'NLI verification started' },
  [TraceEventType.VERIFICATION_COMPLETED]:{ icon: CheckCircle2,  color: 'text-emerald-400', label: 'Verification completed' },
  [TraceEventType.RECOVERY_REWRITE]:      { icon: RefreshCw,     color: 'text-amber-400',   label: 'Recovery: query rewrite' },
  [TraceEventType.RECOVERY_RE_RETRIEVE]:  { icon: RefreshCw,     color: 'text-amber-400',   label: 'Recovery: expanded retrieval' },
  [TraceEventType.RECOVERY_REGENERATE]:   { icon: RefreshCw,     color: 'text-cyan-400',    label: 'Recovery: regeneration retry' },
  [TraceEventType.RECOVERY_RE_RETRIEVE_SKIPPED]: { icon: CheckCircle2, color: 'text-slate-400', label: 'Recovery: kept narrow retrieval' },
  [TraceEventType.RETRIEVAL_REUSED]:      { icon: CheckCircle2, color: 'text-cyan-400',    label: 'Reused saved evidence' },
  [TraceEventType.RETRIEVAL_CAPPED]:      { icon: AlertTriangle, color: 'text-amber-400',  label: 'Generation context capped' },
  [TraceEventType.GENERATION_DEGENERATE]: { icon: XCircle,       color: 'text-red-400',     label: 'Degenerate output discarded' },
  [TraceEventType.CLAIMS_EMPTY]:          { icon: AlertTriangle, color: 'text-amber-400',   label: 'No verifiable claims' },
  [TraceEventType.ANALYSIS_COMPLETED]:    { icon: CheckCircle2, color: 'text-green-400', label: 'Analysis complete' },
  [TraceEventType.ANALYSIS_ABSTAINED]:    { icon: AlertTriangle, color: 'text-amber-400', label: 'Abstained' },
  [TraceEventType.ANALYSIS_FAILED]:       { icon: XCircle,       color: 'text-red-400',   label: 'Analysis failed' },
  [TraceEventType.RETRIEVAL_OUTAGE]:      { icon: XCircle,       color: 'text-red-400',   label: 'Search service outage' },
  [TraceEventType.GENERATION_SKIPPED]:    { icon: CheckCircle2,  color: 'text-slate-400', label: 'Repeat generation skipped' },
  [TraceEventType.CACHE_HIT]:             { icon: CheckCircle2,  color: 'text-cyan-400',  label: 'Semantic cache hit' },
  [TraceEventType.RECOVERY_STARTED]:      { icon: Circle,        color: 'text-amber-400', label: 'Recovery started' },
  [TraceEventType.RECOVERY_COMPLETED]:    { icon: CheckCircle2,  color: 'text-amber-400', label: 'Recovery round complete' },
  [TraceEventType.RECOVERY_SKIPPED]:      { icon: CheckCircle2,  color: 'text-slate-400', label: 'Recovery skipped' },
}

/** Normalize for tautology comparison: lowercase, alnum+spaces only. */
const _norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim()

/**
 * displayMessage — suppress backend messages that merely restate the event
 * label ("retrieval completed successfully" under "Retrieval completed").
 * Returns null when the message adds nothing, so rows read once, not twice.
 */
export function displayMessage(event, message) {
  if (!message) return null
  const meta = EVENT_META[event]
  if (!meta) return message
  const label = _norm(meta.label)
  const msg = _norm(message)
  if (!msg || msg === label || msg.startsWith(label) || label.startsWith(msg)) return null
  return message
}

/**
 * compactTraceEvents — collapse consecutive same-type events (the backend
 * emits node-lifecycle pairs like started+completed plus a summary event).
 * Keeps the richest message and earliest timestamp; data fields merge.
 */
export function compactTraceEvents(events) {
  const out = []
  for (const e of events || []) {
    const prev = out[out.length - 1]
    if (prev && prev.event === e.event) {
      const prevMsg = prev.data?.message || ''
      const nextMsg = e.data?.message || ''
      const message = nextMsg.length > prevMsg.length ? nextMsg : prevMsg
      out[out.length - 1] = {
        ...prev,
        data: { ...(prev.data || {}), ...(e.data || {}), ...(message ? { message } : {}) },
        timestamp: prev.timestamp || e.timestamp,
      }
      continue
    }
    out.push(e)
  }
  return out
}
