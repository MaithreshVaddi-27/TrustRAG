import { memo } from 'react'
import { clsx } from 'clsx'

/**
 * TrustRAG — brand mark.
 *
 * Redrawn flat for the Obsidian / Chrome Silver / Laser Crimson system.
 * The previous mark was a gradient-glass shield with a glow; both are
 * excluded by the design direction, so this is linework only.
 *
 * The mark is an architectural "T" — a bar and a stem — with the calibrated
 * truth core at its foot in Laser Crimson. Crimson appears exactly once, at
 * the point where a claim is verified, and nowhere else in the mark.
 */

export const TrustRagEmblem = memo(function TrustRagEmblem({
  size = 32,
  className = '',
  framed = true,
  // `glow` is accepted by existing call sites and deliberately ignored: the
  // mark is flat linework now and emits no glow.
  title,
}) {
  const stroke = '#cdcbcA' // Chrome Silver
  const core = '#d41514' // Laser Crimson

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx('shrink-0 select-none', className)}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {framed && (
        <rect
          x="1"
          y="1"
          width="30"
          height="30"
          rx="8"
          stroke={stroke}
          strokeOpacity="0.34"
          strokeWidth="1"
        />
      )}

      {/* The T — the bar and the stem. */}
      <path
        d="M9 10.5h14M16 10.5v13"
        stroke={stroke}
        strokeWidth="2"
        strokeLinecap="square"
      />

      {/* Calibrated truth core — the verified point. */}
      <path d="M16 23.5l2.4 2.4L16 28.3l-2.4-2.4z" fill={core} />
    </svg>
  )
})
