import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router'
import { useAuthStore } from '@/stores/auth-store'

export default function ProtectedRoute() {
  const { isAuthenticated, accessToken, validateToken } = useAuthStore()
  const [isValidating, setIsValidating] = useState(true)

  useEffect(() => {
    if (accessToken) {
      validateToken().finally(() => setIsValidating(false))
    } else {
      setIsValidating(false)
    }
  }, [accessToken, validateToken])

  if (isValidating) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
