import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router'
import { useAuthStore } from '@/stores/auth-store'
import { useUiStore } from '@/stores/ui-store'
import { useWebSocket } from '@/hooks/use-websocket'
import ActivityBar from './ActivityBar'
import Sidebar from './Sidebar'

function useSyncNavFromRoute() {
  const location = useLocation()
  const { setActiveNav } = useUiStore()

  useEffect(() => {
    const pathname = location.pathname
    if (pathname.startsWith('/manage')) {
      setActiveNav('manage')
    } else if (pathname.startsWith('/settings')) {
      setActiveNav('settings')
    } else {
      setActiveNav('chat')
    }
  }, [location.pathname, setActiveNav])
}

export default function AppShell() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const setConnectionStatus = useUiStore((s) => s.setConnectionStatus)
  const { connectionStatus } = useWebSocket(accessToken)
  useSyncNavFromRoute()

  useEffect(() => {
    setConnectionStatus(connectionStatus)
  }, [connectionStatus, setConnectionStatus])

  return (
    <div className="flex h-screen">
      <ActivityBar />
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
