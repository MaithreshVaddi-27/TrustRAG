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

/**
 * TrustRagLogo — full brand lockup: mark plus wordmark.
 */
export const TrustRagLogo = memo(function TrustRagLogo({
  size = 'md', // 'sm' | 'md' | 'lg' | 'xl'
  showSubtitle = true,
  className = '',
  emblemOnly = false,
}) {
  const pixelSizes = {
    sm: 24,
    md: 32,
    lg: 40,
    xl: 56,
  }

  const px = pixelSizes[size] || 32

  return (
    <div className={clsx('flex items-center gap-2.5 select-none', className)}>
      <span className="shrink-0">
        <TrustRagEmblem size={px} framed />
      </span>

      {!emblemOnly && (
        <div className="flex flex-col leading-none">
          <span
            className={clsx(
              'font-display text-silver-050',
              size === 'sm' && 'text-xs',
              size === 'md' && 'text-sm sm:text-base',
              size === 'lg' && 'text-lg sm:text-xl',
              size === 'xl' && 'text-2xl',
            )}
          >
            TRUSTRAG
          </span>

          {showSubtitle && (
            <span
              className={clsx(
                'font-mono text-slate-500 mt-1',
                size === 'sm' && 'text-[9px]',
                size === 'md' && 'text-[10px]',
                size === 'lg' && 'text-[11px]',
                size === 'xl' && 'text-xs',
              )}
            >
              Reliability workbench
            </span>
          )}
        </div>
      )}
    </div>
  )
})
