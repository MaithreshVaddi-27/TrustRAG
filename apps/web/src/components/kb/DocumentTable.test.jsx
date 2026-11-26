import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DocumentTable from './DocumentTable'

const { kbService } = vi.hoisted(() => ({
  kbService: {
    listDocuments: vi.fn(),
    uploadDocument: vi.fn(),
    deleteDocument: vi.fn(),
  },
}))

vi.mock('@/services/api', () => ({ kbService }))

const KB = {
  id: 'kb1',
  name: 'Service API v3',
  description: 'Public API contract.',
}

function documentWith(status) {
  return {
    id: 'doc1',
    filename: 'notes.txt',
    file_size: 120,
    content_hash: 'a'.repeat(64),
    ingestion_status: status,
    error_message: null,
    created_at: '2026-01-02T10:00:00Z',
  }
}

function renderTable() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <DocumentTable kb={KB} pollIntervalMs={20} />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('DocumentTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('refreshes a pending document until ingestion completes', async () => {
    kbService.listDocuments
      .mockResolvedValueOnce([documentWith('pending')])
      .mockResolvedValue([documentWith('completed')])

    renderTable()

    expect(await screen.findByText('Indexing')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Indexed')).toBeInTheDocument()
    })
    expect(kbService.listDocuments.mock.calls.length).toBeGreaterThan(1)
  })

  it('stops polling once every document reached a terminal state', async () => {
    kbService.listDocuments.mockResolvedValue([documentWith('completed')])

    renderTable()

    expect(await screen.findByText('Indexed')).toBeInTheDocument()
    const callsAfterFirstFetch = kbService.listDocuments.mock.calls.length
    await new Promise((resolve) => setTimeout(resolve, 80))
    expect(kbService.listDocuments.mock.calls.length).toBe(callsAfterFirstFetch)
  })
})
