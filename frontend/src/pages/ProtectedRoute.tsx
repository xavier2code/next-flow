import { useEffect } from 'react'
import { Navigate, Outlet } from 'react-router'
import { useAuthStore } from '@/stores/auth-store'

export default function ProtectedRoute() {
  const { isAuthenticated, validateToken } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) {
      validateToken()
    }
  }, [isAuthenticated, validateToken])

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
