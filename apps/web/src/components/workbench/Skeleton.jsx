/**
 * Skeleton — a layout-matching placeholder.
 *
 * A skeleton takes the shape of the content it stands in for, so the page
 * does not reflow when the data arrives. It breathes rather than shimmers:
 * a sweep is a loop that carries no information, and on a dark surface it
 * reads as noise.
 *
 *   <Skeleton className="h-4 w-3/4" />
 *   <SkeletonRows rows={5} className="h-12" gap="gap-2" />
 */
export function Skeleton({ className = '' }) {
  return <div className={`skel ${className}`.trim()} aria-hidden="true" />
}

export function SkeletonRows({ rows = 4, className = 'h-12', gap = 'gap-2' }) {
  return (
    <div className={`flex flex-col ${gap}`.trim()} aria-hidden="true" role="status" aria-label="Loading content">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className={className} />
      ))}
    </div>
  )
}
