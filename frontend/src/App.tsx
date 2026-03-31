import { Routes, Route, Navigate } from 'react-router'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<div>Login placeholder</div>} />
      <Route path="/register" element={<div>Register placeholder</div>} />
      <Route path="/" element={<div>Chat placeholder</div>} />
      <Route path="/conversations/:id" element={<div>Chat placeholder</div>} />
      <Route path="/manage/agents" element={<div>Agent management placeholder</div>} />
      <Route path="/manage/skills" element={<div>Skill management placeholder</div>} />
      <Route path="/manage/servers" element={<div>MCP management placeholder</div>} />
      <Route path="/settings" element={<div>Settings placeholder</div>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
