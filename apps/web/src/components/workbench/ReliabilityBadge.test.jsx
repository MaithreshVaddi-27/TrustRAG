import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ReliabilityBadge } from './ReliabilityBadge'

/**
 * The badge's band is the reliability engine's verdict, not a threshold
 * invented here. TRUSTED is a judgement about claim coverage and
 * contradiction rate that a score alone cannot make, and an abstention is
 * not a failure — the run produced no answer, so it does not get the alarm
 * colour.
 */
describe('ReliabilityBadge', () => {
  it('reads the band from the verdict, not from the score', () => {
    render(<ReliabilityBadge score={1} status="TRUSTED" />)

    const badge = screen.getByText('100%').closest('span.inline-flex')
    expect(badge.className).toContain('text-silver-200')
    expect(badge.className).not.toContain('crimson')
  })

  it('gives a failed run the alarm colour', () => {
    render(<ReliabilityBadge score={0.2} status="FAILED" />)

    const badge = screen.getByText('20%').closest('span.inline-flex')
    expect(badge.className).toContain('crimson')
  })

  it('does not call an abstention a failure', () => {
    render(<ReliabilityBadge score={0} status="ABSTAINED" />)

    const badge = screen.getByText('0%').closest('span.inline-flex')
    expect(badge.className).not.toContain('crimson')
    expect(badge.className).toContain('text-silver-500')
  })

  it('falls back to the score when no verdict is supplied', () => {
    render(<ReliabilityBadge score={0.8} />)

    const badge = screen.getByText('80%').closest('span.inline-flex')
    expect(badge.className).toContain('text-silver-400')
  })

  it('normalises a score that arrived on a 0-100 scale', () => {
    render(<ReliabilityBadge score={87} status="UNCERTAIN" />)

    expect(screen.getByText('87%')).toBeInTheDocument()
  })
})
