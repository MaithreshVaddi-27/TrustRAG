import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders the idle workbench prompt', () => {
    render(<EmptyState onLoadSample={() => {}} />)

    expect(screen.getByRole('heading', { name: 'Awaiting Pipeline Query' })).toBeInTheDocument()
    expect(screen.getByText('Interactive Verification Workbench')).toBeInTheDocument()
  })

})