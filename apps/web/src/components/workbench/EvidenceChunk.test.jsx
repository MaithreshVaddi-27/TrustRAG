import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EvidenceChunk } from './EvidenceViewer'

vi.mock('@/lib/clipboard', () => ({
  copyToClipboard: vi.fn().mockResolvedValue(true),
}))

const base = {
  chunk_id: 'c1',
  text: 'Some evidence text about RAG grounding.',
  filename: 'doc.pdf',
  document_id: 'd1',
  method: 'hybrid',
}

function renderChunk(chunk) {
  return render(<EvidenceChunk chunk={chunk} rank={1} onCopy={() => {}} isCopied={false} />)
}

describe('EvidenceChunk integrity shield (fail-closed)', () => {
  it('shows the verified shield for VERIFIED chunks', () => {
    const { container } = renderChunk({ ...base, integrity_status: 'VERIFIED' })
    expect(container.querySelector('[title="Cryptographic provenance verified"]')).not.toBeNull()
  })

  it('labels EXTERNAL_UNAUDITED web chunks amber, never verified', () => {
    const { container } = renderChunk({
      ...base,
      integrity_status: 'EXTERNAL_UNAUDITED',
      url: 'https://example.com',
      method: 'mcp_tavily',
      chunk_id: 'web_0',
    })
    expect(container.querySelector('[title="Cryptographic provenance verified"]')).toBeNull()
    expect(screen.getByText('EXTERNAL_UNAUDITED')).toBeDefined()
    expect(screen.getByText('MCP')).toBeDefined()
  })

  it('treats missing status as UNVERIFIED, not verified', () => {
    const { container } = renderChunk({ ...base })
    expect(container.querySelector('[title="Cryptographic provenance verified"]')).toBeNull()
    expect(screen.getByText('UNVERIFIED')).toBeDefined()
  })
})
