import { Routes, Route, Navigate } from 'react-router'
import LoginPage from '@/components/auth/LoginPage'
import RegisterPage from '@/components/auth/RegisterPage'
import ProtectedRoute from '@/pages/ProtectedRoute'
import AppShell from '@/components/layout/AppShell'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<div className="flex h-full items-center justify-center text-muted-foreground">选择或创建一个对话开始聊天</div>} />
          <Route path="/conversations/:id" element={<div className="flex h-full items-center justify-center text-muted-foreground">对话加载中...</div>} />
          <Route path="/manage/agents" element={<div className="flex h-full items-center justify-center text-muted-foreground">智能体管理</div>} />
          <Route path="/manage/skills" element={<div className="flex h-full items-center justify-center text-muted-foreground">技能管理</div>} />
          <Route path="/manage/servers" element={<div className="flex h-full items-center justify-center text-muted-foreground">MCP 服务器管理</div>} />
          <Route path="/settings" element={<div className="flex h-full items-center justify-center text-muted-foreground">用户设置</div>} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
