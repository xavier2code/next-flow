import { Outlet } from 'react-router'
import { useAuthStore } from '@/stores/auth-store'
import { useWebSocket } from '@/hooks/use-websocket'
import ActivityBar from './ActivityBar'
import Sidebar from './Sidebar'

export default function AppShell() {
  const accessToken = useAuthStore((s) => s.accessToken)
  useWebSocket(accessToken)

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
