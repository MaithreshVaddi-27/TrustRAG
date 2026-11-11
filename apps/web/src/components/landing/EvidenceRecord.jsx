import { memo } from 'react'
import { clsx } from 'clsx'
import { FileText } from 'lucide-react'
import VerificationSeal from './VerificationSeal'
import Verdict from './Verdict'

/**
 * EvidenceRecord — one row of the verification ledger.
 *
 * A claim, the evidence it was checked against, and the verdict. The
 * document reference and the content hash are mono because they are
 * measured data, not prose.
 */
const EvidenceRecord = memo(function EvidenceRecord({
  index,
  claim,
  status = 'unknown',
  confidence,
  citation,
  hash,
  conflict,
  score,
  sealed = false,
  className = '',
}) {
  return (
    <article className={clsx('lx-record', status === 'contradicted' && 'lx-record--contradicted', className)}>
      <header className="lx-record__head">
        <span className="lx-micro">{index}</span>
        {sealed && (
          <span className="inline-flex items-center gap-2">
            <span className="lx-micro">Registered</span>
            <VerificationSeal />
          </span>
        )}
      </header>

      <div className="lx-record__claim">
        <p className="lx-record__text">{claim}</p>

        {citation && (
          <p className="lx-record__citation">
            <FileText size={12} strokeWidth={1.5} aria-hidden="true" />
            <span>{citation}</span>
          </p>
        )}

        {hash && <p className="lx-record__citation">sha256 {hash}</p>}

        {conflict && <p className="lx-record__conflict">{conflict}</p>}
      </div>

      <footer className="lx-record__foot">
        <Verdict status={status} />
        {confidence && (
          <span className="lx-score">
            entailment
            <span className="lx-score__value">{confidence}</span>
          </span>
        )}
        {score && <span className="lx-score">{score}</span>}
      </footer>
    </article>
  )
})

export default EvidenceRecord
