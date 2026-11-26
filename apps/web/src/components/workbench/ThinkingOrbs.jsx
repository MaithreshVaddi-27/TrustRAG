/**
 * ThinkingOrbs — libraries.dev-family loader ("orbs that think while you wait").
 *
 * Three breathing orbs (transform/opacity only, GPU-cheap) replace generic
 * circular spinners wherever the user waits on the pipeline: route loads,
 * page-level fetches, live stage cards, and the Run Analysis button.
 * Static under prefers-reduced-motion (see styles/loaders.css).
 *
 * Sizes: sm (inline, stage cards / buttons) · md (page loads) · lg (hero moments).
 */
export function ThinkingOrbs({ size = 'sm', label = null, elapsedSec = null, className = '' }) {
  const sizeClass =
    size === 'lg' ? 'thinking-orbs--lg' : size === 'md' ? 'thinking-orbs--md' : ''
  const accessibleLabel =
    label || (elapsedSec != null ? `Working (${elapsedSec}s elapsed)` : 'Loading')
  return (
    <span
      className={`thinking-orbs ${sizeClass} ${className}`.trim()}
      role="status"
      aria-label={accessibleLabel}
    >
      <span className="orb" aria-hidden="true" />
      <span className="orb" aria-hidden="true" />
      <span className="orb" aria-hidden="true" />
      {label && (
        <span className="ml-2 text-sm text-slate-400 font-medium">{label}</span>
      )}
      {elapsedSec != null && (
        <span className="ml-1 text-xs text-slate-500 font-mono tabular-nums">
          {elapsedSec}s
        </span>
      )}
    </span>
  )
}
