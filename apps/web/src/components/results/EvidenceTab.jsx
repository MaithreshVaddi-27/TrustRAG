import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'

export function EvidenceTab({ analysis }) {
  return (
    <EvidenceViewer
      chunks={analysis.evidence || []}
      unavailable={Boolean(analysis.evidenceUnavailable)}
    />
  )
}
