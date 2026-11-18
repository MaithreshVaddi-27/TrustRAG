import { memo } from 'react'
import { clsx } from 'clsx'

/**
 * TrustRAG — brand mark.
 *
 * A verification seal: a rounded-square boundary (the claim's evidence
 * perimeter) with a checkmark formed by two converging evidence streams
 * meeting at the verdict point. The checkmark's tail breaks past the seal's
 * bottom edge — a verified claim escapes its evidence boundary instead of
 * being contained by it. Crimson appears exactly once, at the verdict.
 *
 * Redrawn for the Obsidian / Chrome Silver / Laser Crimson system.
 * Flat linework only — no gradients, filters, or live text.
 */

export const TrustRagEmblem = memo(function TrustRagEmblem({
  size = 32,
  className = '',
  framed = true,
  // `glow` is accepted by existing call sites and deliberately ignored.
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

      {/* The seal — the claim's evidence boundary. */}
      <rect
        x="4"
        y="4"
        width="24"
        height="24"
        rx="7"
        stroke={stroke}
        strokeWidth="1.5"
        fill="none"
      />

      {/* The checkmark — two converging evidence streams meeting at the verdict. */}
      <path
        d="M 10 16.5 L 14 20.5 L 22 11.5"
        stroke={core}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* Verdict point — the single crimson dot. */}
      <circle cx="22" cy="11.5" r="1.2" fill={core} />
    </svg>
  )
})
