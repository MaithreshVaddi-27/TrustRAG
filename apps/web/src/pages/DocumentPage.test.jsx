import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DocumentPage from './DocumentPage'

const { kbService } = vi.hoisted(() => ({
  kbService: {
    getDocument: vi.fn(),
    get: vi.fn(),
  },
}))

vi.mock('@/services/api', () => ({
  kbService,
  modelService: { getProviders: vi.fn() },
}))

vi.mock('@/services/auth', () => ({
  authService: { logout: vi.fn() },
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({ user: { email: 'tester@example.com', name: 'Tester' } }),
}))

vi.mock('@/hooks/useBackendHealth', () => ({
  default: () => ({ isOnline: true, isChecking: false, recheck: vi.fn() }),
}))

vi.mock('@/lib/clipboard', () => ({
  copyToClipboard: vi.fn().mockResolvedValue(true),
}))

const DOC = {
  id: 'doc1',
  knowledge_base_id: 'kb1',
  filename: 'service-api-v3.txt',
  file_size: 1484,
  content_hash: 'a'.repeat(64),
  ingestion_status: 'completed',
  error_message: null,
  effective_from: null,
  effective_until: null,
  created_at: '2026-01-02T10:00:00Z',
}

const COLLECTION = {
  id: 'kb1',
  name: 'Service API v3',
  description: 'Public API contract and rate limits.',
  embedding_model: 'BAAI/bge-small-en-v1.5',
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  return render(
    <MemoryRouter initialEntries={['/documents/doc1']}>
      <QueryClientProvider client={client}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/knowledge-bases" element={<p>the corpus ledger</p>} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('DocumentPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    kbService.getDocument.mockResolvedValue(DOC)
    kbService.get.mockResolvedValue(COLLECTION)
  })

  it('names the document and the collection it was indexed into', async () => {
    renderPage()

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'service-api-v3.txt', level: 1 }),
      ).toBeInTheDocument()
    })

    // The collection is a second request, so its row fills in after the
    // heading does.
    await waitFor(() => {
      expect(screen.getByText('Service API v3')).toBeInTheDocument()
    })
  })

  it('shows the full content hash, not a truncated one', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('a'.repeat(64))).toBeInTheDocument()
    })
  })

  it('reports the vector space the document was embedded into', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('BAAI/bge-small-en-v1.5')).toBeInTheDocument()
    })
  })

  it('shows the validity window as two named bounds, not a hidden field', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Effective from')).toBeInTheDocument()
    })
    expect(screen.getByText('Effective until')).toBeInTheDocument()
  })

  it('leaves an unset bound as a dash rather than a fabricated date', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Effective from')).toBeInTheDocument()
    })

    const row = screen.getByText('Effective from').closest('.lx-deflist__row')
    expect(row.querySelector('dd').textContent).toBe('—')
  })

  it('reports the window when the document has one', async () => {
    kbService.getDocument.mockResolvedValue({
      ...DOC,
      effective_from: '2026-01-01T00:00:00Z',
      effective_until: '2026-06-30T00:00:00Z',
    })

    renderPage()

    await waitFor(() => {
      const row = screen
        .getByText('Effective from')
        .closest('.lx-deflist__row')
      expect(row.querySelector('dd').textContent).not.toBe('—')
    })

    const untilRow = screen
      .getByText('Effective until')
      .closest('.lx-deflist__row')
    expect(untilRow.querySelector('dd').textContent).not.toBe('—')
  })

  it('shows the backend error message when an ingestion failed', async () => {
    kbService.getDocument.mockResolvedValue({
      ...DOC,
      ingestion_status: 'failed',
      error_message: 'Embedding dimension mismatch',
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Embedding dimension mismatch')).toBeInTheDocument()
    })
    expect(screen.getByText('Ingestion failed')).toBeInTheDocument()
  })

  it('offers a way back to the corpus ledger', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /All collections/ })).toBeInTheDocument()
    })
  })
})
