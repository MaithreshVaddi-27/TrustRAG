import {
  AlertTriangle, CheckCircle2,
  Circle, RefreshCw, XCircle,
} from 'lucide-react'

export const TraceEventType = {
  ANALYSIS_STARTED: 'analysis.started',
  RETRIEVAL_STARTED: 'retrieval.started',
  RETRIEVAL_EMPTY: 'retrieval.empty',
  RETRIEVAL_COMPLETED: 'retrieval.completed',
  INTEGRITY_FAILED: 'integrity.failed',
  GENERATION_STARTED: 'generation.started',
  GENERATION_COMPLETED: 'generation.completed',
  CLAIMS_STARTED: 'claims.started',
  CLAIMS_DECOMPOSED: 'claims.decomposed',
  CLAIMS_VERIFIED: 'claims.verified',
  VERIFICATION_STARTED: 'verification.started',
  VERIFICATION_COMPLETED: 'verification.completed',
  RECOVERY_REWRITE: 'recovery.rewrite',
  RECOVERY_RE_RETRIEVE: 'recovery.re_retrieve',
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
  [TraceEventType.ANALYSIS_COMPLETED]:    { icon: CheckCircle2,  color: 'text-green-400',   label: 'Analysis complete' },
  [TraceEventType.ANALYSIS_ABSTAINED]:    { icon: AlertTriangle, color: 'text-amber-400',   label: 'Abstained' },
  [TraceEventType.ANALYSIS_FAILED]:       { icon: XCircle,       color: 'text-red-400',     label: 'Analysis failed' },
}
