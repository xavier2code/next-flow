import { create } from 'zustand'
import type { User, TokenResponse } from '@/types/api'
import { apiClient, startTokenRefreshTimer, stopTokenRefreshTimer, registerAuthCallbacks } from '@/lib/api-client'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<void>
  setUser: (user: User) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  validateToken: () => Promise<void>
  clearAuth: () => void
}

export const useAuthStore = create<AuthState & AuthActions>()((set, get) => {
  // Register auth callbacks for api-client to avoid circular imports
  registerAuthCallbacks({
    getAccessToken: () => get().accessToken,
    getRefreshToken: () => get().refreshToken,
    setTokens: (accessToken: string, refreshToken: string) => {
      set({ accessToken, refreshToken, isAuthenticated: true })
    },
    clearAuth: () => {
      stopTokenRefreshTimer()
      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
      })
    },
  })

  return {
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,

    login: async (email: string, password: string) => {
      const tokens = await apiClient.post<TokenResponse>('/api/v1/auth/login', {
        email,
        password,
      })
      set({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
      })
      startTokenRefreshTimer()
      // Fetch user profile
      await get().validateToken()
    },

    register: async (email: string, password: string, displayName?: string) => {
      await apiClient.post('/api/v1/auth/register', {
        email,
        password,
        display_name: displayName,
      })
      // Auto-login after registration
      await get().login(email, password)
    },

    logout: async () => {
      const { refreshToken } = get()
      try {
        await apiClient.post('/api/v1/auth/logout', {
          refresh_token: refreshToken,
        })
      } catch {
        // Logout endpoint may fail, still clear local state
      }
      stopTokenRefreshTimer()
      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
      })
    },

    refreshTokens: async () => {
      const { refreshToken } = get()
      if (!refreshToken) return

      const tokens = await apiClient.post<TokenResponse>('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      })
      set({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      })
      startTokenRefreshTimer()
    },

    setUser: (user: User) => {
      set({ user })
    },

    setTokens: (accessToken: string, refreshToken: string) => {
      set({
        accessToken,
        refreshToken,
        isAuthenticated: true,
      })
    },

    validateToken: async () => {
      try {
        const user = await apiClient.get<User>('/api/v1/auth/me')
        set({ user, isAuthenticated: true })
      } catch {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      }
    },

    clearAuth: () => {
      stopTokenRefreshTimer()
      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
      })
    },
  }
})
