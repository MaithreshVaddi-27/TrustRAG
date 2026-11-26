import { useState } from 'react'
import { clsx } from 'clsx'
import { FileWarning } from 'lucide-react'
import VerificationSeal from './VerificationSeal'
import Verdict from './Verdict'
import { SCENARIOS, SCENARIO_ORDER } from './data/scenarios'

/**
 * SimulationSandbox — four measured runs, opened one at a time.
 *
 * Nothing here is a mock. Each scenario is a query the evaluation harness
 * actually issued against the frozen fixture corpus, and every figure,
 * claim, explanation and citation under it was read back out of the run
 * record. The provenance line at the foot of each case names the run.
 */
export default function SimulationSandbox() {
  const [activeId, setActiveId] = useState(SCENARIO_ORDER[0])
  const scenario = SCENARIOS[activeId]

  return (
    <div className="lx-ledger">
      <div className="lx-ledger__head">
        <div className="lx-scenarios" role="group" aria-label="Measured verification runs">
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
          {scenario.doc} · {scenario.claims.length}{' '}
          {scenario.claims.length === 1 ? 'claim' : 'claims'}
        </span>
      </div>

      <div className="lx-ledger__query">
        <p className="lx-ledger__query-text">{scenario.query}</p>
      </div>

      {scenario.answer && (
        <div className="lx-ledger__answer">
          <p className="lx-label lx-ledger__answer-label">Answer as emitted</p>
          <p className="lx-ledger__answer-body">{scenario.answer}</p>
        </div>
      )}

      {scenario.claims.length > 0 ? (
        <div role="list" key={`claims-${scenario.id}`}>
          {scenario.claims.map((claim, index) => (
            <div
              key={claim.id}
              role="listitem"
              className={clsx(
                'lx-claim',
                claim.status === 'contradicted' && 'lx-claim--contradicted',
              )}
              style={{ '--claim-index': index }}
            >
              <span className="lx-claim__index">
                {String(claim.id).padStart(2, '0')}
              </span>

              <div>
                <p className="lx-claim__text">{claim.text}</p>

                {claim.citation && (
                  <p className="lx-claim__citation">{claim.citation}</p>
                )}

                {claim.explanation && (
                  <p className="lx-claim__explanation">{claim.explanation}</p>
                )}
              </div>

              <div className="lx-claim__aside">
                <Verdict status={claim.status} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="lx-claim lx-claim--empty">
          <span className="lx-claim__index">—</span>

          <div>
            <p className="lx-claim__text">
              Nothing was asserted. The run reached the abstention state without emitting
              a single claim, so there is no claim to audit and no segment to cite.
            </p>
          </div>

          <div className="lx-claim__aside">
            <span className="lx-verdict lx-verdict--unknown">
              <FileWarning size={14} strokeWidth={1.75} aria-hidden="true" />
              <span>Withheld</span>
            </span>
          </div>
        </div>
      )}

      <dl className="lx-metrics">
        {scenario.metrics.map((metric) => (
          <div key={metric.label} className="lx-metric">
            <dt className="lx-micro">{metric.label}</dt>
            <dd className="lx-metric__value">{metric.value}</dd>
          </div>
        ))}
      </dl>

      <div key={`outcome-${scenario.id}`} className={clsx('lx-outcome', `lx-outcome--${scenario.outcome.kind}`)}>
        <div className="lx-outcome__head">
          <VerificationSeal tone={scenario.outcome.kind === 'abstained' ? 'crimson' : 'silver'} />
          <span className="lx-label">{scenario.outcome.title}</span>
        </div>

        <p className="lx-outcome__body">{scenario.outcome.body}</p>

        {scenario.outcome.audit && (
          <p className="lx-outcome__audit">{scenario.outcome.audit}</p>
        )}
      </div>

      <p className="lx-ledger__provenance">{scenario.provenance}</p>
    </div>
  )
}
