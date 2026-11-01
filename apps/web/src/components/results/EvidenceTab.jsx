import { motion } from 'motion/react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'

export function EvidenceTab({ analysis }) {
  return (
    <motion.div
      key="evidence"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={SPRING_SNAPPY}
    >
      <EvidenceViewer chunks={analysis.evidence || []} />
    </motion.div>
  )
}