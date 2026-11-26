import { useMemo, useState } from 'react'
import { CHART } from '@/lib/chartTheme'
import { useChartWidth } from './useChartWidth'

/**
 * ReliabilityAreaChart — the reliability trajectory.
 *
 * One series, one accent. The threshold is a dashed hairline, not a
 * coloured band, and a point that fell below the threshold is the only
 * thing on the chart that carries crimson.
 *
 * Hand-drawn SVG rather than a charting library: the chart needs exactly
 * one area, one reference line and a hover readout, and a general-purpose
 * library costs three hundred kilobytes for it.
 */
const PAD = { top: 12, right: 12, bottom: 24, left: 40 }
const HEIGHT = 236

export default function ReliabilityAreaChart({
  data = [],
  threshold = 75,
  onHover = null,
}) {
  const [ref, width] = useChartWidth()
  const [hovered, setHovered] = useState(null)

  const innerW = Math.max(40, width - PAD.left - PAD.right)
  const innerH = HEIGHT - PAD.top - PAD.bottom

  const points = useMemo(
    () =>
      data.map((entry, index) => ({
        ...entry,
        x:
          data.length === 1
            ? PAD.left + innerW / 2
            : PAD.left + (index / (data.length - 1)) * innerW,
        y: PAD.top + innerH - (Math.min(100, Math.max(0, entry.score)) / 100) * innerH,
      })),
    [data, innerW, innerH],
  )

  if (!data.length) return null

  const linePath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)},${point.y.toFixed(2)}`)
    .join(' ')

  const areaPath = `${linePath} L${points[points.length - 1].x.toFixed(2)},${(
    PAD.top + innerH
  ).toFixed(2)} L${points[0].x.toFixed(2)},${(PAD.top + innerH).toFixed(2)} Z`

  const thresholdY = PAD.top + innerH - (threshold / 100) * innerH

  const gridValues = [0, 25, 50, 75, 100]
  const activePoint = hovered != null ? points[hovered] : null

  const handleMove = (event) => {
    if (!points.length) return
    const bounds = event.currentTarget.getBoundingClientRect()
    const x = event.clientX - bounds.left
    let nearest = 0
    let best = Infinity
    points.forEach((point, index) => {
      const distance = Math.abs(point.x - x)
      if (distance < best) {
        best = distance
        nearest = index
      }
    })
    setHovered(nearest)
    onHover?.(points[nearest])
  }

  return (
    <div ref={ref} className="relative w-full">
      <svg
        width="100%"
        height={HEIGHT}
        viewBox={`0 0 ${width} ${HEIGHT}`}
        role="img"
        aria-label={`Reliability across ${data.length} analyses, threshold ${threshold} percent`}
        onMouseMove={handleMove}
        onMouseLeave={() => {
          setHovered(null)
          onHover?.(null)
        }}
      >
        <defs>
          <linearGradient id="lxReliabilityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CHART.silver} stopOpacity="0.22" />
            <stop offset="100%" stopColor={CHART.silver} stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Gridlines — hairlines, no axes. */}
        {gridValues.map((value) => {
          const y = PAD.top + innerH - (value / 100) * innerH
          return (
            <g key={value}>
              <line
                x1={PAD.left}
                x2={PAD.left + innerW}
                y1={y}
                y2={y}
                stroke={CHART.grid}
                strokeWidth="1"
              />
              <text
                x={PAD.left - 8}
                y={y + 3}
                textAnchor="end"
                fill={CHART.axis}
                fontSize="10"
                fontFamily="var(--typeface-mono)"
              >
                {value}
              </text>
            </g>
          )
        })}

        {/* The threshold. */}
        <line
          x1={PAD.left}
          x2={PAD.left + innerW}
          y1={thresholdY}
          y2={thresholdY}
          stroke={CHART.rule}
          strokeWidth="1"
          strokeDasharray="3 3"
        />
        <text
          x={PAD.left + innerW}
          y={thresholdY - 5}
          textAnchor="end"
          fill={CHART.axis}
          fontSize="9"
          fontFamily="var(--typeface-mono)"
        >
          threshold {threshold}%
        </text>

        <path d={areaPath} fill="url(#lxReliabilityFill)" />
        <path
          d={linePath}
          fill="none"
          stroke={CHART.silver}
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {points.map((point, index) => (
          <circle
            key={point.id ?? index}
            cx={point.x}
            cy={point.y}
            r={hovered === index ? 4 : 2.5}
            fill={point.score < threshold ? CHART.crimson : CHART.silver}
            stroke="none"
          />
        ))}

        {activePoint && (
          <line
            x1={activePoint.x}
            x2={activePoint.x}
            y1={PAD.top}
            y2={PAD.top + innerH}
            stroke={CHART.rule}
            strokeWidth="1"
          />
        )}

        {/* Time axis: first, last, and a middle label. */}
        <text x={PAD.left} y={HEIGHT - 6} fill={CHART.axis} fontSize="10" fontFamily="var(--typeface-mono)">
          {points[0].time}
        </text>
        {points.length > 2 && (
          <text
            x={PAD.left + innerW / 2}
            y={HEIGHT - 6}
            textAnchor="middle"
            fill={CHART.axis}
            fontSize="10"
            fontFamily="var(--typeface-mono)"
          >
            {points[Math.floor(points.length / 2)].time}
          </text>
        )}
        <text
          x={PAD.left + innerW}
          y={HEIGHT - 6}
          textAnchor="end"
          fill={CHART.axis}
          fontSize="10"
          fontFamily="var(--typeface-mono)"
        >
          {points[points.length - 1].time}
        </text>
      </svg>

      {activePoint && (
        <div
          className="pointer-events-none absolute top-3 z-10 max-w-[18rem] rounded-[var(--radius-control)] border border-[color:var(--rule)] bg-surface-panel px-3 py-2"
          style={{
            left: Math.min(Math.max(activePoint.x + 10, 4), width - 200),
          }}
        >
          <p className="font-mono text-[var(--size-micro)] text-silver-500">{activePoint.fullTime}</p>
          <p className="mt-0.5 text-[var(--size-body-sm)] text-silver-100">
            {activePoint.query}
          </p>
          <p
            className="mt-1 font-mono text-[0.75rem] tabular-nums"
            style={{
              color:
                activePoint.score < threshold ? CHART.crimsonLight : CHART.silver,
            }}
          >
            {activePoint.score}% · {activePoint.status}
          </p>
        </div>
      )}
    </div>
  )
}
