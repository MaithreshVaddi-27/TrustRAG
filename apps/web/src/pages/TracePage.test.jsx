import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TracePage from './TracePage'

const { analysisService, kbService } = vi.hoisted(() => ({
  analysisService: { trace: vi.fn(), get: vi.fn() },
  kbService: { list: vi.fn() },
}))

vi.mock('@/services/api', () => ({
  analysisService,
  kbService,
  modelService: { getProviders: vi.fn() },
}))

vi.mock('@/services/auth', () => ({
  authService: { logout: vi.fn() },
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({ user: { email: 'tester@example.com' } }),
}))

vi.mock('@/hooks/useBackendHealth', () => ({
  default: () => ({ isOnline: true, isChecking: false, recheck: vi.fn() }),
}))

const EVENTS = [
  {
    event: 'retrieval.completed',
    timestamp: '2026-11-12T03:00:00Z',
    data: { message: 'Retrieved 4 verified segments', latency_ms: 259 },
  },
  {
    event: 'generation.completed',
    timestamp: '2026-11-12T03:00:02Z',
    data: { message: 'Generation completed', latency_ms: 2160 },
  },
]

const ANALYSIS = {
  id: 'an1',
  query: 'What rate limits does the service apply?',
  status: 'abstained',
  knowledge_base_id: 'kb1',
  llm_provider: 'ollama',
  llm_model: 'gemma3:1b',
  reliability: { score: 0, status: 'ABSTAINED' },
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  return render(
    <MemoryRouter initialEntries={['/traces/an1']}>
      <QueryClientProvider client={client}>
        <Routes>
          <Route path="/traces/:id" element={<TracePage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('TracePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    analysisService.trace.mockResolvedValue(EVENTS)
    analysisService.get.mockResolvedValue(ANALYSIS)
    kbService.list.mockResolvedValue([
      { id: 'kb1', name: 'Service API v3', document_count: 1 },
    ])
  })

  it('names the run the trace belongs to', async () => {
    // Regression: the page showed the events and nothing else. A trace
    // without the question, the collection and the verdict is a log, not a
    // record.
    renderPage()

    await waitFor(() => {
      expect(
        screen.getByText(/What rate limits does the service apply\?/),
      ).toBeTruthy()
    })

    expect(screen.getByText('Service API v3')).toBeTruthy()
    expect(screen.getByText('ollama · gemma3:1b')).toBeTruthy()
  })

  it('reports the event count and the stage time the pipeline measured', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('2')).toBeTruthy()
    })
    expect(screen.getByText('2.42s')).toBeTruthy()
  })

  it('says plainly that the run abstained', async () => {
    renderPage()

    await waitFor(() => {
      expect(
        screen.getByText(/The run produced no answer/),
      ).toBeTruthy()
    })
  })
})
