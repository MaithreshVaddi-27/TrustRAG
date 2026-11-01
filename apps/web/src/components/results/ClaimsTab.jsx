import { motion } from 'motion/react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'
import { ClaimInspector } from '@/components/workbench/ClaimInspector'

export function ClaimsTab({ analysis }) {
  return (
    <motion.div
      key="claims"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={SPRING_SNAPPY}
    >
      {analysis.status === 'abstained' || analysis.reliability?.status === 'ABSTAINED' ? (
        <p className="mb-3 rounded-lg border border-amber-800/50 bg-amber-950/20 px-3 py-2 text-xs text-amber-300">
          The generated draft was checked against the evidence, but the final answer was withheld. These claim verdicts apply to that draft, not the abstention message.
        </p>
      ) : null}
      <ClaimInspector claims={analysis.claims || []} />
    </motion.div>
  )
}