import { memo } from 'react'
import { clsx } from 'clsx'

/**
 * TrustRAG — brand mark · "Overlap".
 *
 * The claim is a solid Chrome Silver disc; the corpus is a Chrome Silver ring.
 * Exactly half the claim is grounded inside the evidence, and the single Laser
 * Crimson point sits at the centre of that supported half — support is the
 * overlap; everything outside it is unsupported.
 *
 * Redrawn for the Obsidian / Chrome Silver / Laser Crimson system.
 * Flat linework only — no gradients, filters, or live text.
 *
 * The `framed` and `glow` props are accepted but ignored; the mark carries
 * its own boundary.
 */

export const TrustRagEmblem = memo(function TrustRagEmblem({
  size = 32,
  className = '',
  title,
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 256 256"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx('shrink-0 select-none', className)}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {/* The claim — a solid disc. */}
      <circle cx="177" cy="128" r="54" fill="#cdcbcA" />

      {/* The corpus — the evidence boundary. Half the claim is grounded in it. */}
      <circle cx="101" cy="128" r="76" stroke="#a3a2a0" strokeWidth="18" />

      {/* Verdict point — the single crimson dot, in the supported half. */}
      <circle cx="154" cy="128" r="11" fill="#d41514" />
    </svg>
  )
})
