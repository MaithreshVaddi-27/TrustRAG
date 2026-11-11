import { useState } from 'react'
import { clsx } from 'clsx'
import VerificationSeal from './VerificationSeal'
import Verdict from './Verdict'
import { SCENARIOS } from './data/scenarios'

/**
 * SimulationSandbox — an interactive verification run.
 *
 * Three real scenarios from the system's own fixture corpus. Choosing one
 * opens that record: the claims, the verdict on each, the contradiction, and
 * the recovery that followed.
 */
const SCENARIO_ORDER = ['entailment', 'recovery', 'provenance']

export default function SimulationSandbox() {
  const [activeId, setActiveId] = useState(SCENARIO_ORDER[0])
  const scenario = SCENARIOS[activeId]

  return (
    <div className="lx-ledger">
      <div className="lx-ledger__head">
        <div className="lx-scenarios" role="group" aria-label="Verification scenarios">
          {SCENARIO_ORDER.map((id) => {
            const option = SCENARIOS[id]
            const selected = option.id === scenario.id

            return (
              <button
                key={id}
                type="button"
                className="lx-scenario"
                aria-pressed={selected}
                onClick={() => setActiveId(id)}
              >
                {option.label}
              </button>
            )
          })}
        </div>

        <span className="lx-ledger__doc">
          {scenario.doc} · {scenario.claims.length} claims
        </span>
      </div>

      <div className="lx-ledger__query">
        <p className="lx-ledger__query-text">{scenario.query}</p>
      </div>

      <div role="list">
        {scenario.claims.map((claim) => (
          <div
            key={claim.id}
            role="listitem"
            className={clsx(
              'lx-claim',
              claim.status === 'contradicted' && 'lx-claim--contradicted',
            )}
          >
            <span className="lx-claim__index">
              {String(claim.id).padStart(2, '0')}
            </span>

            <div>
              <p className="lx-claim__text">{claim.text}</p>

              {claim.citation && (
                <p className="lx-claim__citation">{claim.citation}</p>
              )}

              {claim.conflict && (
                <p className="lx-claim__conflict">{claim.conflict}</p>
              )}
            </div>

            <div className="lx-claim__aside">
              <Verdict status={claim.status} />
              {claim.confidence && (
                <span className="lx-score">
                  <span className="lx-score__value">{claim.confidence}</span>
                </span>
              )}
              {claim.initialScore && (
                <span className="lx-score">
                  was <span className="lx-score__value">{claim.initialScore}</span>
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="lx-recovery">
        <div className="lx-recovery__head">
          <VerificationSeal />
          <span className="lx-label">Recovered by the closed loop</span>
          <span className="lx-micro">final score {scenario.recovery.finalScore}</span>
        </div>

        <p className="lx-recovery__action">{scenario.recovery.action}</p>
        <p className="lx-recovery__healed">{scenario.recovery.healed}</p>
      </div>
    </div>
  )
}
