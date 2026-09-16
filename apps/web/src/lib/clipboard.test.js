import { describe, it, expect, vi, afterEach } from 'vitest'
import { copyToClipboard } from './clipboard'

function stubClipboard(writeTextImpl) {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: writeTextImpl },
  })
}

describe('copyToClipboard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns false for nullish input', async () => {
    expect(await copyToClipboard(null)).toBe(false)
    expect(await copyToClipboard(undefined)).toBe(false)
  })

  it('uses navigator.clipboard when available', async () => {
    const writeText = vi.fn().mockResolvedValue()
    stubClipboard(writeText)

    await expect(copyToClipboard('hello')).resolves.toBe(true)
    expect(writeText).toHaveBeenCalledWith('hello')
  })

  it('falls back to execCommand when the clipboard API rejects', async () => {
    stubClipboard(vi.fn().mockRejectedValue(new Error('permission denied')))
    document.execCommand = vi.fn(() => true)

    await expect(copyToClipboard('hello')).resolves.toBe(true)
    expect(document.execCommand).toHaveBeenCalledWith('copy')
  })

  it('returns false when both paths fail', async () => {
    stubClipboard(vi.fn().mockRejectedValue(new Error('permission denied')))
    document.execCommand = vi.fn(() => false)

    await expect(copyToClipboard('hello')).resolves.toBe(false)
  })
})