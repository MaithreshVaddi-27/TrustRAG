import { motion } from 'motion/react'
import { RefreshCw } from 'lucide-react'
import { SPRING_SNAPPY } from '@/lib/motionConfig'

/**
 * BackendBanner - Shows when backend is unreachable
 * Called by: AppLayout.jsx
 * No existing file serves this purpose - extracted from AppLayout
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function BackendBanner({ isOnline, recheck }) {
  return (
    <AnimatePresence>
      {isOnline === false && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={SPRING_SNAPPY}
          className="overflow-hidden z-30 border-b border-red-900/40 bg-red-950/30 backdrop-blur-sm"
        >
          <div className="flex items-center justify-center gap-2 py-2 px-4 text-xs text-red-300">
            <span className="shrink-0">
              Backend unreachable — start the API server to enable analysis.
            </span>
            <motion.button
              onClick={recheck}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="shrink-0 ml-1 px-2 py-0.5 rounded-lg bg-red-900/30 border border-red-800/40 text-red-200 hover:text-red-100 hover:bg-red-900/50 transition-colors text-[11px] font-mono"
            >
              <RefreshCw size={11} className="inline mr-1" />
              Retry
            </motion.button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// Need AnimatePresence import
import { AnimatePresence } from 'motion/react'