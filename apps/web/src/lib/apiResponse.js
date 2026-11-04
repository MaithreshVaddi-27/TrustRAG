/**
 * TRUSTRAG — Standardized API response handling, retry logic, and error normalization.
 *
 * Called by: services/api.js (to wrap service methods), hooks/useAnalysisStream.js (for retry on analysis calls), any component making API calls
 * No existing file serves this purpose - new utility for Phase 3 API layer hardening
 * Reads/writes: Standardizes axios responses to { data, meta, error } shape, provides retry with exponential backoff
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */

// ─── Error Codes ───────────────────────────────────────────────────────────────
export const ERROR_CODES = {
  // Network / connectivity
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  CONNECTION_REFUSED: 'CONNECTION_REFUSED',

  // HTTP status based
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT: 'CONFLICT',
  UNPROCESSABLE_ENTITY: 'UNPROCESSABLE_ENTITY',
  RATE_LIMITED: 'RATE_LIMITED',
  SERVER_ERROR: 'SERVER_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',

  // Application specific
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  TICKET_EXPIRED: 'TICKET_EXPIRED',
  ANALYSIS_NOT_FOUND: 'ANALYSIS_NOT_FOUND',
  KB_NOT_FOUND: 'KB_NOT_FOUND',
  PROVIDER_UNAVAILABLE: 'PROVIDER_UNAVAILABLE',

  // Unknown
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
}

// ─── Retry Configuration ───────────────────────────────────────────────────────
const DEFAULT_RETRY_CONFIG = {
  maxAttempts: 3,
  baseDelayMs: 500,
  maxDelayMs: 8000,
  backoffMultiplier: 2,
  jitterFactor: 0.3,
  // Status codes that trigger retry
  retryableStatuses: new Set([408, 429, 500, 502, 503, 504]),
  // Error codes that trigger retry
  retryableCodes: new Set([
    ERROR_CODES.NETWORK_ERROR,
    ERROR_CODES.TIMEOUT,
    ERROR_CODES.CONNECTION_REFUSED,
    ERROR_CODES.SERVER_ERROR,
    ERROR_CODES.SERVICE_UNAVAILABLE,
    ERROR_CODES.RATE_LIMITED,
  ]),
}

// ─── Standardized Response Shape ───────────────────────────────────────────────
/**
 * @template T
 * @typedef {Object} ApiResponse
 * @property {T|null} data - The response payload on success
 * @property {Object|null} meta - Metadata (pagination, timing, etc.)
 * @property {ApiError|null} error - Error info on failure
 */

/**
 * @typedef {Object} ApiError
 * @property {string} code - Machine-readable error code from ERROR_CODES
 * @property {string} message - Human-readable message
 * @property {number} [status] - HTTP status code
 * @property {Object} [details] - Additional error details (validation errors, etc.)
 * @property {string} [requestId] - Server request ID for tracing
 */

// ─── Utility Functions ─────────────────────────────────────────────────────────

/**
 * Normalize any error into a standard ApiError shape
 */
export function normalizeError(err) {
  // Already normalized
  if (err?.code && ERROR_CODES[err.code]) {
    return err
  }

  // Axios error
  if (err?.response) {
    const status = err.response.status
    const data = err.response.data
    const requestId = err.response.headers?.['x-request-id']

    // Validation errors (422)
    if (status === 422 && data?.error?.message) {
      let details = data.error.message
      if (Array.isArray(details)) {
        details = details.map(m => {
          if (typeof m === 'object' && m?.loc && m?.msg) {
            const field = Array.isArray(m.loc)
              ? m.loc.filter(l => !['body', 'query', 'path'].includes(l)).join('.')
              : ''
            return field ? `${field}: ${m.msg}` : m.msg
          }
          return String(m)
        }).join('; ')
      }
      return {
        code: ERROR_CODES.VALIDATION_ERROR,
        message: details,
        status,
        details,
        requestId,
      }
    }

    // Map status codes to error codes
    const statusCodeMap = {
      401: ERROR_CODES.UNAUTHORIZED,
      403: ERROR_CODES.FORBIDDEN,
      404: ERROR_CODES.NOT_FOUND,
      409: ERROR_CODES.CONFLICT,
      422: ERROR_CODES.UNPROCESSABLE_ENTITY,
      429: ERROR_CODES.RATE_LIMITED,
      500: ERROR_CODES.SERVER_ERROR,
      502: ERROR_CODES.SERVER_ERROR,
      503: ERROR_CODES.SERVICE_UNAVAILABLE,
      504: ERROR_CODES.SERVICE_UNAVAILABLE,
    }

    const code = statusCodeMap[status] || ERROR_CODES.UNKNOWN_ERROR
    const message = data?.error?.message || data?.detail || err.message || `HTTP ${status}`

    return {
      code,
      message: typeof message === 'string' ? message : JSON.stringify(message),
      status,
      details: data?.error?.details,
      requestId,
    }
  }

  // Network errors
  if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout')) {
    return {
      code: ERROR_CODES.TIMEOUT,
      message: 'Request timed out. Please try again.',
      status: 408,
    }
  }
  if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Network Error')) {
    return {
      code: ERROR_CODES.NETWORK_ERROR,
      message: 'Network error. Check your connection and try again.',
      status: 0,
    }
  }
  if (err?.code === 'ERR_CONNECTION_REFUSED' || err?.message?.includes('Connection refused')) {
    return {
      code: ERROR_CODES.CONNECTION_REFUSED,
      message: 'Cannot connect to server. Is the backend running?',
      status: 0,
    }
  }

  // Generic error
  return {
    code: ERROR_CODES.UNKNOWN_ERROR,
    message: err?.message || 'An unexpected error occurred',
    status: err?.response?.status,
    details: err?.response?.data,
  }
}

/**
 * Check if an error is retryable based on config
 */
export function isRetryableError(err, config = DEFAULT_RETRY_CONFIG) {
  const normalized = normalizeError(err)
  if (config.retryableCodes.has(normalized.code)) return true
  if (normalized.status && config.retryableStatuses.has(normalized.status)) return true
  return false
}

/**
 * Calculate exponential backoff delay with jitter
 */
export function calculateBackoff(attempt, config = DEFAULT_RETRY_CONFIG) {
  const rawDelay = Math.min(
    config.baseDelayMs * Math.pow(config.backoffMultiplier, attempt),
    config.maxDelayMs
  )
  const jitter = rawDelay * config.jitterFactor * Math.random()
  return Math.floor(rawDelay + jitter)
}

/**
 * Sleep utility
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// ─── Retry Wrapper ─────────────────────────────────────────────────────────────

/**
 * Execute an async function with retry logic
 * @template T
 * @param {() => Promise<T>} fn - The async function to execute
 * @param {Object} options - Retry options
 * @param {number} options.maxAttempts - Max retry attempts (default: 3)
 * @param {Function} options.onRetry - Called on each retry: (attempt, error, delay) => void
 * @param {Object} options.retryConfig - Override default retry config
 * @returns {Promise<ApiResponse<T>>}
 */
export async function withRetry(fn, options = {}) {
  const {
    maxAttempts = DEFAULT_RETRY_CONFIG.maxAttempts,
    onRetry,
    retryConfig = DEFAULT_RETRY_CONFIG,
  } = options

  let lastError

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const result = await fn()
      return { data: result, meta: { attempt: attempt + 1 }, error: null }
    } catch (err) {
      lastError = err

      // Don't retry on last attempt
      if (attempt === maxAttempts - 1) break

      // Check if error is retryable
      if (!isRetryableError(err, retryConfig)) {
        break
      }

      const delay = calculateBackoff(attempt, retryConfig)

      if (onRetry) {
        onRetry(attempt + 1, normalizeError(err), delay)
      }

      await sleep(delay)
    }
  }

  // All attempts failed
  const normalized = normalizeError(lastError)
  return { data: null, meta: { attempts: maxAttempts }, error: normalized }
}

// ─── Request Wrapper with Standardized Response ────────────────────────────────

/**
 * Wrap an axios call to return standardized ApiResponse
 * @template T
 * @param {Promise} promise - The axios promise
 * @returns {Promise<ApiResponse<T>>}
 */
export async function toApiResponse(promise) {
  try {
    const response = await promise
    return {
      data: response.data,
      meta: {
        status: response.status,
        headers: response.headers,
      },
      error: null,
    }
  } catch (err) {
    return {
      data: null,
      meta: {
        status: err.response?.status,
      },
      error: normalizeError(err),
    }
  }
}

/**
 * Execute with retry AND standardized response
 * @template T
 * @param {() => Promise} fn - Function returning axios promise
 * @param {Object} options - Retry options
 * @returns {Promise<ApiResponse<T>>}
 */
export async function withRetryAndResponse(fn, options = {}) {
  return withRetry(async () => {
    const result = await fn()
    return result.data // axios response's data
  }, options)
}

// ─── Higher-Order Service Wrapper ──────────────────────────────────────────────

/**
 * Wrap a service method to add retry and standardized response
 * @template T, Args extends unknown[]
 * @param {function(...Args): Promise} serviceMethod - Original service method
 * @param {Object} options - Retry options
 * @returns {function(...Args): Promise<ApiResponse<T>>}
 */
export function withApiResponse(serviceMethod, options = {}) {
  return async (...args) => {
    return withRetryAndResponse(() => serviceMethod(...args), options)
  }
}

// ─── Batch Request Helper ──────────────────────────────────────────────────────

/**
 * Execute multiple requests in parallel with individual error handling
 * @template T
 * @param {Promise[]} promises - Array of axios promises
 * @returns {Promise<ApiResponse<T>[]>}
 */
export async function batchRequests(promises) {
  const results = await Promise.allSettled(promises.map(p => toApiResponse(p)))
  return results.map(r => r.status === 'fulfilled' ? r.value : {
    data: null,
    meta: null,
    error: normalizeError(r.reason),
  })
}

export default {
  ERROR_CODES,
  normalizeError,
  isRetryableError,
  calculateBackoff,
  withRetry,
  toApiResponse,
  withRetryAndResponse,
  withApiResponse,
  batchRequests,
  DEFAULT_RETRY_CONFIG,
}