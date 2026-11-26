import { SkeletonRows } from '@/components/workbench/Skeleton'

/**
 * SettingsSkeleton — the diagnostics screen's shape, held while the
 * registry answers.
 *
 * It is a different component from the panel stack it stands in for, so
 * the panels arrive as new elements rather than as ones that moved. A
 * reading that is longer than the placeholder it replaces would otherwise
 * push every panel below it down the page.
 */
export function SettingsSkeleton() {
  return (
    <div className="lx-stack" aria-busy="true" aria-live="polite">
      <span className="lx-sr-only">Reading the system diagnostics</span>

      {[5, 7, 3, 4, 6].map((rows, index) => (
        <div key={index} className="lx-panel-block">
          <div className="lx-panel-block__head">
            <span className="lx-skeleton h-4 w-48" />
          </div>
          <div className="lx-panel-block__body">
            <SkeletonRows
              rows={rows}
              className="h-6 rounded-md"
              gap="gap-2"
            />
          </div>
        </div>
      ))}
    </div>
  )
}
