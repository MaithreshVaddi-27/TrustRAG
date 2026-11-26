import { ClaimInspector } from '@/components/workbench/ClaimInspector'

export function ClaimsTab({ analysis }) {
  const abstained =
    analysis.status === 'abstained' || analysis.reliability?.status === 'ABSTAINED'

  return (
    <div className="space-y-4">
      {abstained && (
        <div className="lx-message" role="status">
          <span>
            The generated draft was checked against the evidence, but the final
            answer was withheld. These verdicts apply to the draft, not to the
            abstention message.
          </span>
        </div>
      )}
      <ClaimInspector claims={analysis.claims || []} />
    </div>
  )
}
