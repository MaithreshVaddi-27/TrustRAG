import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FormattedAnswer } from './FormattedAnswer'

/**
 * FormattedAnswer is the component that renders the product's actual output
 * (LLM answer text). It had 0% coverage (audit T-10): a broken citation
 * renderer, a dropped [Segment N] marker, or an HTML-passthrough regression
 * would ship silently.
 */

describe('FormattedAnswer rendering', () => {
  it('returns null for empty content instead of rendering an empty shell', () => {
    const { container } = render(<FormattedAnswer content="" />)
    expect(container.firstChild).toBeNull()
  })

  it('renders GFM tables (the reason remark-gfm is wired in)', () => {
    render(
      <FormattedAnswer
        content={['| Claim | Verdict |', '| --- | --- |', '| Revocation is fast | SUPPORTED |'].join('\n')}
      />
    )
    expect(screen.getByRole('table')).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Verdict' })).toBeTruthy()
    expect(screen.getByRole('cell', { name: 'SUPPORTED' })).toBeTruthy()
  })

  it('renders inline and fenced code, distinguishing the two', () => {
    const { container } = render(
      <FormattedAnswer content={'Use `bge-small` for embeddings.\n\n```python\nembed("hi")\n```'} />
    )
    // Inline code stays a bare <code>, not wrapped in <pre>.
    const inline = container.querySelector('code:not(pre code)')
    expect(inline?.textContent).toBe('bge-small')
    // Fenced code is wrapped in a <pre> block.
    const block = container.querySelector('pre code')
    expect(block?.textContent).toContain('embed("hi")')
  })

  it('preserves [Segment N] citation markers as visible text', () => {
    // The backend strips markers from `answer` but keeps them in
    // `answer_cited` for audit/eval. If a view renders the cited variant, the
    // markers must survive so an auditor can trace a claim to its segment.
    render(<FormattedAnswer content={'Revocation takes effect [Segment 3] within 60 seconds [Segment 7].'} />)
    expect(screen.getByText(/\[Segment 3\]/)).toBeTruthy()
    expect(screen.getByText(/\[Segment 7\]/)).toBeTruthy()
  })

  it('does NOT execute raw HTML injected via the answer', () => {
    // react-markdown escapes raw HTML by default (no rehype-raw). If a
    // rehype-raw slip ever lands, this becomes an XSS sink: LLM output is
    // attacker-influenceable via a poisoned retrieved document.
    const { container } = render(
      <FormattedAnswer content={'<img src="x" onerror="window.__pwned = true" />'} />
    )
    expect(container.querySelector('img')).toBeNull()
    expect(window.__pwned).toBeUndefined()
  })

  it('does not execute a <script> tag from answer content', () => {
    const { container } = render(<FormattedAnswer content={'<script>window.__pwned=1</script>'} />)
    expect(container.querySelector('script')).toBeNull()
    expect(window.__pwned).toBeUndefined()
  })

  it('renders headings, lists and blockquotes through the custom components', () => {
    const { container } = render(
      <FormattedAnswer
        content={'# Title\n\n- one\n- two\n\n> quoted finding'}
      />
    )
    expect(container.querySelector('h1')?.textContent).toContain('Title')
    expect(container.querySelectorAll('li')).toHaveLength(2)
    expect(container.querySelector('blockquote')?.textContent).toContain('quoted finding')
  })

  it('applies the caller className alongside the base classes', () => {
    const { container } = render(<FormattedAnswer content="hi" className="max-h-40" />)
    const root = container.firstChild
    expect(root.className).toContain('formatted-answer')
    expect(root.className).toContain('max-h-40')
  })
})
