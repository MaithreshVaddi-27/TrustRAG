import { memo } from 'react'
import { clsx } from 'clsx'

/**
 * VerificationSeal — the signature mark.
 *
 * Two opposing corner brackets, borrowed from the registration targets
 * printers use to check that two impressions land in the same place. That is
 * exactly what this product does with a claim and its evidence: it checks
 * that they align.
 *
 * The seal is Laser Crimson. It is the only place on the landing page where
 * crimson appears as a mark rather than as a verdict.
 */
const VerificationSeal = memo(function VerificationSeal({
  className = '',
  tone = 'crimson',
  size = 14,
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx('lx-seal', tone === 'silver' && 'lx-seal--silver', className)}
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M0.5 4V0.5h3.5"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="square"
      />
      <path
        d="M10 0.5h3.5V4"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="square"
      />
      <path
        d="M13.5 10v3.5H10"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="square"
      />
      <path
        d="M4 13.5H0.5V10"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="square"
      />
    </svg>
  )
})

export default VerificationSeal
