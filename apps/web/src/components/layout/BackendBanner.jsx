import { AnimatePresence, motion } from 'motion/react'
import { RefreshCw } from 'lucide-react'

/**
 * BackendBanner — the alarm band.
 *
 * Shown only when the backend is unreachable. Laser Crimson, because
 * something is genuinely wrong and the operator needs to know before the
 * page they are looking at starts lying to them.
 */
export function BackendBanner({ isOnline, recheck }) {
  return (
    <AnimatePresence>
      {isOnline === false && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          className="lx-alarm"
        >
          <div className="lx-alarm__inner">
            <span>Backend unreachable — start the API server to enable analysis.</span>
            <button type="button" onClick={recheck} className="lx-alarm__retry">
              <RefreshCw size={11} strokeWidth={1.5} aria-hidden="true" />
              Retry
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
