import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import KnowledgeBasesPage from './KnowledgeBasesPage'

const { kbService, modelService } = vi.hoisted(() => ({
  kbService: { list: vi.fn(), create: vi.fn(), delete: vi.fn() },
  modelService: { getProviders: vi.fn() },
}))

vi.mock('@/services/api', () => ({
  kbService,
  modelService,
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

const COLLECTIONS = [
  {
    id: 'kb1',
    name: 'Service API v3',
    description: 'Public API contract and rate limits.',
    document_count: 3,
    embedding_model: 'BAAI/bge-small-en-v1.5',
    created_at: '2026-01-02T10:00:00Z',
  },
  {
    id: 'kb2',
    name: 'Retention Policy 2026',
    description: 'Deletion schedules.',
    document_count: 0,
    embedding_model: null,
    created_at: '2026-01-01T10:00:00Z',
  },
]

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <KnowledgeBasesPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('KnowledgeBasesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    kbService.list.mockResolvedValue(COLLECTIONS)
    modelService.getProviders.mockResolvedValue({
      active_provider: 'ollama',
      active_model: 'gemma3:1b',
      providers: { ollama: { connected: true, default_model: 'gemma3:1b' } },
    })
  })

  it('lists collections as a specification, not as a stack of cards', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Service API v3')).toBeInTheDocument()
    })

    expect(screen.getByRole('columnheader', { name: 'Collection' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Documents' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Vector space' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Created' })).toBeInTheDocument()

    // The vector space is reported per collection, and an unpinned one says so.
    expect(screen.getAllByText('bge-small-en-v1.5').length).toBeGreaterThan(0)
    expect(screen.getByText('Not pinned')).toBeInTheDocument()
  })

  it('shows the document count as a figure', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Service API v3')).toBeInTheDocument()
    })
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('offers an inline form rather than a dialog to create a collection', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Service API v3')).toBeInTheDocument()
    })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await waitFor(() => {
      screen.getByRole('button', { name: /New collection/i }).click()
    })

    expect(screen.getByRole('form', { name: 'Create a collection' })).toBeInTheDocument()
    expect(screen.getByLabelText('Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Description')).toBeInTheDocument()
  })

  it('creates a collection from the inline form', async () => {
    kbService.create.mockResolvedValue({ id: 'kb3' })
    renderPage()

    await waitFor(() => {
      screen.getByRole('button', { name: /New collection/i }).click()
    })

    const name = await screen.findByLabelText('Name')
    const description = screen.getByLabelText('Description')

    // React controlled inputs need the native setter to register a change.
    const setValue = (element, value) => {
      const prototype = Object.getPrototypeOf(element)
      Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value)
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }
    setValue(name, 'New Corpus')
    setValue(description, 'A description')

    const submit = await screen.findByRole('button', { name: 'Create collection' })
    await waitFor(() => expect(submit).not.toBeDisabled())
    fireEvent.submit(submit.closest('form'))

    await waitFor(() => {
      expect(kbService.create).toHaveBeenCalled()
    })
    // React Query passes the mutation context as a second argument, so the
    // payload is the first one.
    expect(kbService.create.mock.calls[0][0]).toEqual({
      name: 'New Corpus',
      description: 'A description',
    })
  })

  it('teaches the interface when there are no collections', async () => {
    kbService.list.mockResolvedValue([])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('No collections yet')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Create a collection' })).toBeInTheDocument()
  })
})
