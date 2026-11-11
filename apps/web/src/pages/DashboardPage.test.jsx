import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from './DashboardPage'

// `vi.mock` factories are hoisted above the module body, so the mocked
// services have to be created with `vi.hoisted` to be in scope inside them.
const { kbService, analysisService, claimService, conflictService, modelService } =
  vi.hoisted(() => ({
    kbService: { list: vi.fn() },
    analysisService: { list: vi.fn() },
    claimService: { list: vi.fn() },
    conflictService: { list: vi.fn() },
    modelService: { getProviders: vi.fn() },
  }))

vi.mock('@/services/api', () => ({
  kbService,
  analysisService,
  claimService,
  conflictService,
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

const KB = {
  id: 'kb1',
  name: 'Service API v3',
  description: 'Public API contract.',
  document_count: 3,
  embedding_model: 'BAAI/bge-small-en-v1.5',
}

function analysis(overrides = {}) {
  return {
    id: 'a1',
    status: 'completed',
    query: 'What is the rate limit?',
    answer: 'The API allows 600 requests per minute per tenant.',
    created_at: new Date('2026-01-01T10:00:00Z').toISOString(),
    knowledge_base_id: 'kb1',
    reliability: { score: 0.82, status: 'TRUSTED' },
    ...overrides,
  }
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <DashboardPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('DashboardPage metrics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    kbService.list.mockResolvedValue([KB])
    claimService.list.mockResolvedValue([])
    conflictService.list.mockResolvedValue([])
    modelService.getProviders.mockResolvedValue({
      active_provider: 'ollama',
      active_model: 'gemma3:1b',
      providers: { ollama: { connected: true, default_model: 'gemma3:1b' } },
    })
  })

  it('averages reliability over delivered answers only', async () => {
    analysisService.list.mockResolvedValue([
      analysis({ id: 'a1', reliability: { score: 0.9, status: 'TRUSTED' } }),
      analysis({ id: 'a2', reliability: { score: 0.7, status: 'UNCERTAIN' } }),
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('80.0%')).toBeInTheDocument()
    })
    expect(screen.getByText(/Threshold 75% · 2 answers/)).toBeInTheDocument()
  })

  it('does not average an abstention into the reliability mean', async () => {
    // An abstention scores zero because there was no answer. Averaging it in
    // would report an unreliable answer where the system reported none.
    analysisService.list.mockResolvedValue([
      analysis({
        id: 'a1',
        status: 'abstained',
        reliability: { score: 0, status: 'FAILED' },
        answer: 'I could not verify an answer from this knowledge base.',
      }),
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('No verified answers yet')).toBeInTheDocument()
    })
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.queryByText('0.0%')).not.toBeInTheDocument()
  })

  it('counts a run that produced no answer as a run without an answer', async () => {
    analysisService.list.mockResolvedValue([
      analysis({ id: 'a1', status: 'abstained', reliability: { score: 0, status: 'FAILED' } }),
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('1 without an answer')).toBeInTheDocument()
    })
    expect(screen.queryByText('No runs yet')).not.toBeInTheDocument()
  })

  it('reports a run that produced no verified answer under needs attention', async () => {
    analysisService.list.mockResolvedValue([
      analysis({ id: 'a1', status: 'abstained', reliability: { score: 0, status: 'FAILED' } }),
    ])

    renderPage()

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /1 run produced no verified answer/ }),
      ).toBeInTheDocument()
    })
  })

  it('says so plainly when there is nothing to attend to', async () => {
    analysisService.list.mockResolvedValue([analysis()])

    renderPage()

    await waitFor(() => {
      expect(
        screen.getByText(/No contradicted claims, no source conflicts/),
      ).toBeInTheDocument()
    })
  })

  it('lists contradicted claims and conflicts under needs attention', async () => {
    claimService.list.mockResolvedValue([
      { id: 'c1', text: 'A claim', state: 'CONTRADICTED' },
    ])
    conflictService.list.mockResolvedValue([
      { id: 'x1', title: 'Rate limits disagree', type: 'semantic', claim: '600 vs 1000' },
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/1 contradicted claim/)).toBeInTheDocument()
    })
    expect(screen.getByText('Rate limits disagree')).toBeInTheDocument()
  })

  it('names the collection each run was made against', async () => {
    analysisService.list.mockResolvedValue([analysis()])

    renderPage()

    await waitFor(() => {
      const activity = screen.getByRole('heading', { name: 'Activity' }).closest('section')
      expect(within(activity).getByText('Service API v3')).toBeInTheDocument()
    })
  })

  it('shows the primer only before the workspace has run anything', async () => {
    analysisService.list.mockResolvedValue([])
    const first = renderPage()

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /closed-loop reliability engine/i }),
      ).toBeInTheDocument()
    })

    first.unmount()

    analysisService.list.mockResolvedValue([analysis()])
    renderPage()

    // Wait for the run to actually load, otherwise the primer is still
    // correct because there is nothing to show yet.
    await waitFor(() => {
      expect(screen.getByText('1 answered')).toBeInTheDocument()
    })
    expect(
      screen.queryByRole('heading', { name: /closed-loop reliability engine/i }),
    ).not.toBeInTheDocument()
  })

  it('offers a way to create a collection when the workspace is empty', async () => {
    kbService.list.mockResolvedValue([])
    analysisService.list.mockResolvedValue([])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('No collections yet')).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: /Create a collection/ })).toBeInTheDocument()
  })
})
