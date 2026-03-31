import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router'
import { useUiStore } from '@/stores/ui-store'
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
  useSyncNavFromRoute()

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
