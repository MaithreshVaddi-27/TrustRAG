import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AnswerTab } from './AnswerTab'

vi.mock('@/lib/clipboard', () => ({
  copyToClipboard: vi.fn().mockResolvedValue(true),
}))

const ANALYSIS = {
  id: 'an1',
  status: 'completed',
  query: 'What rate limits does the service apply?',
  answer: 'The API allows 600 requests per minute per tenant.',
  reliability: { score: 0.86, status: 'TRUSTED' },
  claims: [],
  evidence: [],
}

describe('AnswerTab', () => {
  it('renders the answer itself', async () => {
    // Regression: the answer was rendered through a lazy import whose
    // module exports the component by name, not by default. React.lazy
    // resolved to nothing and the whole view crashed the moment an answer
    // arrived — the product's one output could never be displayed.
    render(<AnswerTab analysis={ANALYSIS} />)

    await waitFor(() => {
      expect(
        screen.getByText(/600 requests per minute per tenant/),
      ).toBeTruthy()
    })
  })

  it('says plainly that the agent abstained', async () => {
    render(
      <AnswerTab
        analysis={{
          ...ANALYSIS,
          status: 'abstained',
          answer:
            "I couldn't verify an answer from this knowledge base: the retrieved evidence did not support a grounded response.",
          reliability: { score: 0, status: 'ABSTAINED' },
        }}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('The agent abstained')).toBeTruthy()
    })
  })
})
