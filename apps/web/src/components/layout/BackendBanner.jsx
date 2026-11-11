import { RefreshCw } from 'lucide-react'

/**
 * BackendBanner — the alarm band.
 *
 * Shown only when the backend is unreachable. Laser Crimson, because
 * something is genuinely wrong and the operator needs to know before the
 * page they are looking at starts lying to them.
 *
 * The band collapses on a CSS transition rather than an animation
 * library, so it stays mounted and the exit plays.
 */
export function BackendBanner({ isOnline, recheck }) {
  const offline = isOnline === false

  return (
    <div
      className={`lx-alarm transition-[max-height,opacity] duration-200 ${
        offline ? 'max-h-24 opacity-100' : 'max-h-0 opacity-0'
      }`}
      aria-hidden={!offline}
      role={offline ? 'alert' : undefined}
    >
      <div className="lx-alarm__inner">
        <span>Backend unreachable — start the API server to enable analysis.</span>
        <button type="button" onClick={recheck} className="lx-alarm__retry" tabIndex={offline ? 0 : -1}>
          <RefreshCw size={11} strokeWidth={1.5} aria-hidden="true" />
          Retry
        </button>
      </div>
    </div>
  )
}
