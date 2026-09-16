import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders the idle workbench prompt', () => {
    render(<EmptyState onLoadSample={() => {}} />)

    expect(screen.getByRole('heading', { name: 'Awaiting Pipeline Query' })).toBeInTheDocument()
    expect(screen.getByText('Interactive Verification Workbench')).toBeInTheDocument()
  })

  it('invokes onLoadSample when the sample query button is clicked', () => {
    const onLoadSample = vi.fn()
    render(<EmptyState onLoadSample={onLoadSample} />)

    screen.getByRole('button', { name: /Load Sample Query/ }).click()

    expect(onLoadSample).toHaveBeenCalledTimes(1)
  })
})