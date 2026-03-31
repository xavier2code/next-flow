import { useAuthStore } from '@/stores/auth-store'

export function useAuth() {
  const store = useAuthStore()
  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    accessToken: store.accessToken,
    login: store.login,
    register: store.register,
    logout: store.logout,
    validateToken: store.validateToken,
  }
}
