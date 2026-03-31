import { Routes, Route, Navigate } from 'react-router'
import LoginPage from '@/components/auth/LoginPage'
import RegisterPage from '@/components/auth/RegisterPage'
import ProtectedRoute from '@/pages/ProtectedRoute'
import AppShell from '@/components/layout/AppShell'
import ChatPage from '@/pages/ChatPage'
import ManagementPage from '@/components/management/ManagementPage'
import SettingsPage from '@/components/settings/SettingsPage'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<ChatPage />} />
          <Route path="/conversations/:id" element={<ChatPage />} />
          <Route path="/manage/agents" element={<ManagementPage />} />
          <Route path="/manage/skills" element={<ManagementPage />} />
          <Route path="/manage/servers" element={<ManagementPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
