import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryInput } from './QueryInput'

/**
 * WCAG 2.5.3 (Label in Name) — the quick prompts are the one place in the
 * interface where the visible label and the accessible name are written
 * separately. The name is the whole prompt the button sends; the label is
 * the short chip text. The label has to be a run of words from the start of
 * the name, or the two disagree for a screen-reader user.
 */
describe('QueryInput quick prompts', () => {
  const renderInput = () =>
    render(
      <QueryInput
        query=""
        setQuery={vi.fn()}
        loading={false}
        handleSubmit={vi.fn()}
        handlePresetSelect={vi.fn()}
      />,
    )

  it('gives every chip an accessible name that contains its visible label', () => {
    renderInput()

    const chips = screen.getAllByRole('button')
    expect(chips.length).toBeGreaterThan(0)

    for (const chip of chips) {
      const visible = chip.textContent.trim()
      const name = chip.getAttribute('aria-label') ?? ''
      expect(name.length).toBeGreaterThan(0)
      // The visible words must appear, in order and without a gap, at the
      // start of the name.
      expect(name.startsWith(visible)).toBe(true)
    }
  })

  it('sends the full prompt, not the chip label', () => {
    const handlePresetSelect = vi.fn()
    render(
      <QueryInput
        query=""
        setQuery={vi.fn()}
        loading={false}
        handleSubmit={vi.fn()}
        handlePresetSelect={handlePresetSelect}
      />,
    )

    const chip = screen.getByRole('button', { name: 'Explain the key concepts in this document' })
    chip.click()

    expect(handlePresetSelect).toHaveBeenCalledWith(
      'Explain the key concepts in this document',
    )
  })

  it('keeps the tooltip and the accessible name in step', () => {
    renderInput()

    for (const chip of screen.getAllByRole('button')) {
      expect(chip.getAttribute('title')).toBe(chip.getAttribute('aria-label'))
    }
  })
})
