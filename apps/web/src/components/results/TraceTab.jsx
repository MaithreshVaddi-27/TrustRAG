import { motion } from 'motion/react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'
import { ExecutionTrace } from '@/components/workbench/ExecutionTrace'

export function TraceTab({ currentTraceEvents }) {
  return (
    <motion.div
      key="trace"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={SPRING_SNAPPY}
    >
      <ExecutionTrace events={currentTraceEvents} isLive={false} />
    </motion.div>
  )
}