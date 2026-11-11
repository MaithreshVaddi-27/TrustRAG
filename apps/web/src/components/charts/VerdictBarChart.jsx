import { useMemo } from 'react'
import { CHART } from '@/lib/chartTheme'
import { useChartWidth } from './useChartWidth'

/**
 * VerdictBarChart — how the audited claims broke down.
 *
 * Horizontal bars, ranked, with the count set in tabular figures beside the
 * label. One accent: supported is Chrome Silver, neutral is a quiet step,
 * and only contradicted carries crimson.
 *
 * Hand-drawn SVG rather than a charting library — see ReliabilityAreaChart.
 */
const ROW_HEIGHT = 44
const BAR_HEIGHT = 12
const LABEL_WIDTH = 104

export default function VerdictBarChart({ data = [] }) {
  const [ref, width] = useChartWidth()

  const max = useMemo(
    () => Math.max(1, ...data.map((entry) => entry.count)),
    [data],
  )

  if (!data.length) return null

  const height = data.length * ROW_HEIGHT + 8
  const trackWidth = Math.max(40, width - LABEL_WIDTH - 52)

  return (
    <div ref={ref} className="w-full">
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={data
          .map((entry) => `${entry.name}: ${entry.count}`)
          .join(', ')}
      >
        {data.map((entry, index) => {
          const y = index * ROW_HEIGHT + 12
          const barWidth = Math.max(2, (entry.count / max) * trackWidth)

          return (
            <g key={entry.name}>
              <text
                x={0}
                y={y + BAR_HEIGHT / 2 + 3}
                fill={CHART.textMuted}
                fontSize="11"
                fontFamily="var(--typeface-sans)"
              >
                {entry.name}
              </text>

              <rect
                x={LABEL_WIDTH}
                y={y}
                width={trackWidth}
                height={BAR_HEIGHT}
                fill={CHART.grid}
                rx="2"
              />

              <rect
                x={LABEL_WIDTH}
                y={y}
                width={barWidth}
                height={BAR_HEIGHT}
                fill={entry.color}
                rx="2"
              />

              <text
                x={LABEL_WIDTH + trackWidth + 10}
                y={y + BAR_HEIGHT / 2 + 3}
                fill={CHART.text}
                fontSize="11"
                fontFamily="var(--typeface-mono)"
                style={{ fontVariantNumeric: 'tabular-nums' }}
              >
                {entry.count}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
