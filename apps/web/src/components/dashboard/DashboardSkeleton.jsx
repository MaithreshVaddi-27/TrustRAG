import { SkeletonRows } from '@/components/workbench/Skeleton'

/**
 * DashboardSkeleton — the dashboard's own shape, held while it loads.
 *
 * The dashboard used to render its panels with empty data and then swap in
 * the real values. Every panel changed height at once, and the page jumped
 * by most of a screen — a cumulative layout shift of 0.84 on a phone.
 *
 * A skeleton in the shape of the thing that is coming fixes it: the
 * skeleton occupies the same space the content will, so the numbers, the
 * charts and the ledger all arrive in place.
 */
export function DashboardSkeleton() {
  return (
    <div className="lx-stack" aria-busy="true" aria-live="polite">
      <span className="lx-sr-only">Loading the dashboard</span>

      {/* Needs attention */}
      <div className="lx-panel-block">
        <div className="lx-panel-block__head">
          <span className="lx-skeleton h-4 w-40" />
        </div>
        <div className="lx-panel-block__body">
          <span className="lx-skeleton block h-4 w-2/3" />
          <span className="lx-skeleton mt-3 block h-3 w-full" />
          <span className="lx-skeleton mt-2 block h-3 w-4/5" />
        </div>
      </div>

      {/* Figures */}
      <div className="lx-statstrip">
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="lx-stat">
            <span className="lx-skeleton block h-3 w-24" />
            <span className="lx-skeleton mt-2 block h-8 w-16" />
            <span className="lx-skeleton mt-2 block h-3 w-28" />
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="lx-grid-wide-narrow">
        <div className="lx-panel-block">
          <div className="lx-panel-block__head">
            <span className="lx-skeleton h-4 w-48" />
          </div>
          <div className="lx-panel-block__body">
            <span className="lx-skeleton block h-72 w-full" />
          </div>
        </div>
        <div className="lx-panel-block">
          <div className="lx-panel-block__head">
            <span className="lx-skeleton h-4 w-36" />
          </div>
          <div className="lx-panel-block__body">
            <span className="lx-skeleton block h-72 w-full" />
          </div>
        </div>
      </div>

      {/* Workspace */}
      <div className="lx-panel-block">
        <div className="lx-panel-block__head">
          <span className="lx-skeleton h-4 w-28" />
        </div>
        <div className="lx-panel-block__body">
          <SkeletonRows rows={3} className="h-10 rounded-md" gap="gap-2" />
        </div>
      </div>

      {/* Activity */}
      <div className="lx-panel-block">
        <div className="lx-panel-block__body">
          <SkeletonRows rows={3} className="h-16 rounded-xl" gap="gap-3" />
        </div>
      </div>
    </div>
  )
}
