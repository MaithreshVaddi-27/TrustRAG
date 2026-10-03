import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders the idle workbench prompt', () => {
    render(<EmptyState />)

    expect(screen.getByRole('heading', { name: 'Awaiting Pipeline Query' })).toBeInTheDocument()
    expect(screen.getByText('Interactive Verification Workbench')).toBeInTheDocument()
  })

  it('renders the feature cards', () => {
    render(<EmptyState />)

    expect(screen.getByText('Closed-Loop NLI')).toBeInTheDocument()
    expect(screen.getByText('Self-Healing Loop')).toBeInTheDocument()
  })

  it('renders the web grounding card only when enabled', () => {
    const { rerender } = render(<EmptyState />)
    expect(screen.queryByText('Web Grounding')).not.toBeInTheDocument()

    rerender(<EmptyState enableWebSearch />)
    expect(screen.getByText('Web Grounding')).toBeInTheDocument()
  })
})
