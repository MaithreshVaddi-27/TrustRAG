/**
 * TEST-M4: SSE stream recovery behavior of openAnalysisStream.
 *
 * Verifies that when ticket issuance fails the caller gets a null source plus
 * onError (Driving the UI to fall back to polling — no EventSource is opened),
 * and that terminal/keep-alive/error event handling on a live stream behaves.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { openAnalysisStream } from '@/lib/api'

const mocks = vi.hoisted(() => ({
  post: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: () => ({
      defaults: {},
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      post: (...args) => mocks.post(...args),
    }),
  },
}))

function registerEventSourceMock() {
  const instances = []
  class MockEventSource {
    constructor(url) {
      this.url = url
      this.close = vi.fn()
      instances.push(this)
    }
    set onmessage(fn) {
      this._onmessage = fn
    }
    get onmessage() {
      return this._onmessage
    }
    set onerror(fn) {
      this._onerror = fn
    }
    get onerror() {
      return this._onerror
    }
  }
  vi.stubGlobal('EventSource', MockEventSource)
  return instances
}

let instances

beforeEach(() => {
  mocks.post.mockReset()
  instances = registerEventSourceMock()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('openAnalysisStream — recovery on failure (TEST-M4)', () => {
  it('returns null and calls onError when the stream-ticket mint fails, without opening a stream', async () => {
    mocks.post.mockRejectedValue(new Error('network down'))

    const onError = vi.fn()
    const onComplete = vi.fn()
    const result = await openAnalysisStream('analysis-123', {
      onError,
      onComplete,
    })

    expect(result).toBeNull()
    expect(onError).toHaveBeenCalledOnce()
    expect(onComplete).not.toHaveBeenCalled()
    expect(instances).toHaveLength(0)
  })

  it('opens an EventSource with the ticketed URL and never leaks the JWT into it', async () => {
    mocks.post.mockResolvedValue({ data: { ticket: 'streamticket-s3cret' } })

    const source = await openAnalysisStream('analysis-123')

    expect(source).not.toBeNull()
    expect(instances).toHaveLength(1)
    expect(instances[0].url).toContain('/api/v1/analyses/analysis-123/stream?ticket=streamticket-s3cret')
    expect(instances[0].url).not.toContain('access_token')
    expect(instances[0].url).not.toContain('Authorization')
  })

  it('calls onComplete and closes the source on a terminal event', async () => {
    mocks.post.mockResolvedValue({ data: { ticket: 't' } })

    const onEvent = vi.fn()
    const onComplete = vi.fn()
    await openAnalysisStream('analysis-123', { onEvent, onComplete })

    const source = instances[0]
    source.onmessage({ data: JSON.stringify({ event: 'analysis.completed', trace: [] }) })

    expect(source.close).toHaveBeenCalledOnce()
    expect(onComplete).toHaveBeenCalledOnce()
    expect(onEvent).toHaveBeenCalledOnce()
  })

  it('ignores server keep-alive ping heartbeats', async () => {
    mocks.post.mockResolvedValue({ data: { ticket: 't' } })

    const onEvent = vi.fn()
    const onComplete = vi.fn()
    await openAnalysisStream('analysis-123', { onEvent, onComplete })

    const source = instances[0]
    source.onmessage({ data: JSON.stringify({ event: 'ping' }) })

    expect(onEvent).not.toHaveBeenCalled()
    expect(onComplete).not.toHaveBeenCalled()
    expect(source.close).not.toHaveBeenCalled()
  })

  it('closes the source and reports onError when the stream fails mid-flight', async () => {
    mocks.post.mockResolvedValue({ data: { ticket: 't' } })

    const onError = vi.fn()
    await openAnalysisStream('analysis-123', { onError })

    const source = instances[0]
    const streamError = new Event('error')
    source.onerror(streamError)

    expect(source.close).toHaveBeenCalledOnce()
    expect(onError).toHaveBeenCalledWith(streamError)
  })
})