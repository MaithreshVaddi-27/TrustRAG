import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ClaimInspector } from './ClaimInspector'

vi.mock('@/lib/clipboard', () => ({
  copyToClipboard: vi.fn().mockResolvedValue(true),
}))

import { copyToClipboard } from '@/lib/clipboard'

const claims = [
  {
    id: 'c1',
    text: 'Alpha claim about RAG.',
    state: 'SUPPORTED',
    subject: 'RAG',
    predicate: 'improves',
    object: 'grounding',
    explanation: 'Supported by citation 1',
    evidence_ids: ['abc123'],
  },
  {
    id: 'c2',
    text: 'Beta claim about agents.',
    state: 'CONTRADICTED',
    subject: 'agents',
    predicate: 'halve',
    object: 'latency',
    explanation: 'Contradicts citation 2',
    evidence_ids: ['def456'],
  },
]

describe('ClaimInspector', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders all claims with per-state counts', () => {
    render(<ClaimInspector claims={claims} />)

    expect(screen.getByText('Alpha claim about RAG.')).toBeInTheDocument()
    expect(screen.getByText('Beta claim about agents.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Supported (1)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Contradicted (1)' })).toBeInTheDocument()
  })

  it('renders the empty state when there are no claims', () => {
    render(<ClaimInspector claims={[]} />)

    expect(screen.getByText('No Atomic Claims Extracted')).toBeInTheDocument()
  })

  it('filters to a single state when a filter tab is selected', () => {
    render(<ClaimInspector claims={claims} />)

    fireEvent.click(screen.getByRole('button', { name: /Contradicted \(1\)/ }))

    expect(screen.queryByText('Alpha claim about RAG.')).not.toBeInTheDocument()
    expect(screen.getByText('Beta claim about agents.')).toBeInTheDocument()
  })

  it('copies the claim assertion via the clipboard helper', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    render(<ClaimInspector claims={claims} />)

    fireEvent.click(screen.getAllByTitle('Copy claim assertion')[0])

    await waitFor(() => expect(copyToClipboard).toHaveBeenCalledWith('Alpha claim about RAG.'))
    await waitFor(() => expect(document.querySelector('.lucide-check')).toBeInTheDocument())
  })
})