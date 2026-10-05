/**
 * Skeleton — layout-matching shimmer placeholder (design-taste rule:
 * "skeletal loaders matching the final layout's shape", never a spinner
 * for content loads). Shape via Tailwind classes at the call site.
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
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className={className} />
      ))}
    </div>
  )
}
