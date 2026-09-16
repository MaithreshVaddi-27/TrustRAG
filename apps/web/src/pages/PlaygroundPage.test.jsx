import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PlaygroundPage from './PlaygroundPage'

vi.mock('@/services/api', () => ({
  kbService: { list: vi.fn().mockResolvedValue([]) },
  analysisService: {},
  modelService: {
    getProviders: vi.fn().mockResolvedValue({
      active_provider: 'llama_cpp',
      active_model: 'ibm-granite/granite-4.2-3b-GGUF:Q4_K_M',
      active_embedding_provider: 'huggingface',
      active_embedding_model: 'BAAI/bge-small-en-v1.5',
      providers: {
        llama_cpp: {
          connected: true,
          default_model: 'org/Picked-Model-GGUF:Q4_K_M',
          models: ['org/Picked-Model-GGUF:Q4_K_M'],
        },
      },
      embedding_providers: {
        huggingface: { connected: true, models: [] },
      },
    }),
  },
}))

vi.mock('@/services/auth', () => ({
  authService: { logout: vi.fn() },
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({ user: { email: 'tester@example.com' } }),
}))

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <PlaygroundPage />
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('PlaygroundPage engine selection', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('auto-selects the discovered default model so runs never use DEFAULT', async () => {
    renderPage()

    await waitFor(() => {
      const raw = localStorage.getItem('trustrag.playground.engine')
      expect(raw).toBeTruthy()
      expect(JSON.parse(raw).model).toBe('LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M')
    })

    // Top telemetry bar reflects the selection with the full id available.
    await waitFor(() => {
      const pill = document.querySelector('[title*="LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M"]')
      expect(pill).toBeTruthy()
    })
    // Pill text shows the short label (LFM2.5-1.2B-Instruct) — confirm the pill rendered.
    expect(
      screen.getAllByText((_, el) => el?.textContent?.includes('LFM2.5-1.2B-Instruct')).length
    ).toBeGreaterThan(0)
  })

  it('shows the offline warning when the providers query fails', async () => {
    // Regression: a failed /models/providers query left an empty model list
    // with no explanation. The offline banner must render instead.
    const { modelService } = await import('@/services/api')
    vi.mocked(modelService.getProviders).mockRejectedValueOnce(new Error('backend down'))
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Inference server offline')).toBeTruthy()
    })
  })
})
