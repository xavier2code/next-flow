import type { ApiError } from '@/types/api'

class ApiClientError extends Error {
  code: string
  constructor(code: string, message: string) {
    super(message)
    this.code = code
    this.name = 'ApiClientError'
  }
}

// Refresh queue: prevent concurrent refresh race conditions
let refreshPromise: Promise<void> | null = null

// Token refresh timer
let refreshTimer: ReturnType<typeof setTimeout> | null = null

// Lazy getter functions -- set by auth store to avoid circular imports
let _getAccessToken: (() => string | null) | null = null
let _getRefreshToken: (() => string | null) | null = null
let _setTokens: ((accessToken: string, refreshToken: string) => void) | null = null
let _clearAuth: (() => void) | null = null

export function registerAuthCallbacks(callbacks: {
  getAccessToken: () => string | null
  getRefreshToken: () => string | null
  setTokens: (accessToken: string, refreshToken: string) => void
  clearAuth: () => void
}): void {
  _getAccessToken = callbacks.getAccessToken
  _getRefreshToken = callbacks.getRefreshToken
  _setTokens = callbacks.setTokens
  _clearAuth = callbacks.clearAuth
}

function getAccessToken(): string | null {
  return _getAccessToken?.() ?? null
}

function getRefreshToken(): string | null {
  return _getRefreshToken?.() ?? null
}

async function refreshTokens(): Promise<void> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    throw new ApiClientError('NO_REFRESH_TOKEN', 'No refresh token available')
  }

  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!response.ok) {
    // Refresh failed -- clear auth and redirect
    _clearAuth?.()
    window.location.href = '/login'
    throw new ApiClientError('REFRESH_FAILED', 'Token refresh failed')
  }

  const data = await response.json()
  _setTokens?.(data.access_token, data.refresh_token)
  startTokenRefreshTimer()
}

async function ensureRefreshed(): Promise<void> {
  if (refreshPromise) {
    return refreshPromise
  }
  refreshPromise = refreshTokens().finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}

function parseApiError(body: unknown): ApiClientError {
  const err = body as ApiError | undefined
  if (err?.error?.code && err?.error?.message) {
    return new ApiClientError(err.error.code, err.error.message)
  }
  return new ApiClientError('UNKNOWN', 'An unexpected error occurred')
}

// Auth endpoints that return bare objects (no envelope unwrapping)
const AUTH_PATHS = ['/api/v1/auth/login', '/api/v1/auth/register', '/api/v1/auth/refresh', '/api/v1/auth/me']

function isAuthPath(path: string): boolean {
  return AUTH_PATHS.some((p) => path.startsWith(p))
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  isRetry = false,
): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const options: RequestInit = {
    method,
    headers,
  }

  if (body !== undefined) {
    options.body = JSON.stringify(body)
  }

  const response = await fetch(path, options)

  // Handle 401 with refresh retry
  if (response.status === 401 && !isRetry) {
    try {
      await ensureRefreshed()
      return request<T>(method, path, body, true)
    } catch {
      // Refresh failed, already redirected
      throw new ApiClientError('AUTH_EXPIRED', 'Authentication expired')
    }
  }

  if (!response.ok) {
    let errorBody: unknown
    try {
      errorBody = await response.json()
    } catch {
      errorBody = null
    }
    throw parseApiError(errorBody)
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  const json = await response.json()

  // Auth endpoints return bare objects, no envelope unwrapping
  if (isAuthPath(path)) {
    return json as T
  }

  // Unwrap envelope response: { data: T, meta: ... }
  if (json && typeof json === 'object' && 'data' in json) {
    return json.data as T
  }

  return json as T
}

export const apiClient = {
  get<T>(path: string): Promise<T> {
    return request<T>('GET', path)
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>('POST', path, body)
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>('PATCH', path, body)
  },

  del(path: string): Promise<void> {
    return request<void>('DELETE', path)
  },
}

/**
 * Schedule a proactive token refresh at 80% of token lifetime.
 * Called on successful login. 15-min token * 0.8 = 12 minutes.
 */
export function startTokenRefreshTimer(): void {
  stopTokenRefreshTimer()
  const TWELVE_MINUTES = 12 * 60 * 1000
  refreshTimer = setTimeout(async () => {
    try {
      await refreshTokens()
    } catch {
      // Refresh failed, auth store already handles redirect
    }
  }, TWELVE_MINUTES)
}

export function stopTokenRefreshTimer(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer)
    refreshTimer = null
  }
}

export { ApiClientError }
