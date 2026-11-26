import { describe, it, expect, vi, beforeEach } from 'vitest'

/**
 * A mutation is not idempotent. Retrying a create that answered 500 can
 * leave two collections, two documents or two analysis runs behind, and
 * the retry looks successful while the duplicate sits in the database.
 * Reads may be retried; writes may not.
 */
const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/lib/api', () => ({
  default: {
    get: (...args) => mocks.get(...args),
    post: (...args) => mocks.post(...args),
    delete: (...args) => mocks.delete(...args),
  },
}))

const { kbService, analysisService } = await import('@/services/api')

beforeEach(() => {
  mocks.get.mockReset()
  mocks.post.mockReset()
  mocks.delete.mockReset()
})

describe('service retry policy', () => {
  it('does not retry a knowledge-base create', async () => {
    mocks.post.mockRejectedValue({ response: { status: 500, data: {} } })

    await expect(kbService.create({ name: 'x' })).rejects.toBeTruthy()
    expect(mocks.post).toHaveBeenCalledTimes(1)
  })

  it('does not retry a document upload', async () => {
    mocks.post.mockRejectedValue({ response: { status: 503, data: {} } })

    await expect(kbService.uploadDocument('kb1', new File([], 'a.txt'))).rejects.toBeTruthy()
    expect(mocks.post).toHaveBeenCalledTimes(1)
  })

  it('does not retry a knowledge-base delete', async () => {
    mocks.delete.mockRejectedValue({ response: { status: 500, data: {} } })

    await expect(kbService.delete('kb1')).rejects.toBeTruthy()
    expect(mocks.delete).toHaveBeenCalledTimes(1)
  })

  it('does not retry an analysis create', async () => {
    mocks.post.mockRejectedValue({ response: { status: 500, data: {} } })

    await expect(
      analysisService.create({ knowledge_base_id: 'kb1', query: 'q' }),
    ).rejects.toBeTruthy()
    expect(mocks.post).toHaveBeenCalledTimes(1)
  })

  it('still retries a read', async () => {
    mocks.get
      .mockRejectedValueOnce({ response: { status: 500, data: {} } })
      .mockResolvedValueOnce({ data: [] })

    await expect(kbService.list()).resolves.toEqual([])
    expect(mocks.get).toHaveBeenCalledTimes(2)
  })
})
