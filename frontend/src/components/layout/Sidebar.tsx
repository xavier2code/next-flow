import { useNavigate, useLocation } from 'react-router'
import { Plus, Cpu, Wrench, Server } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useUiStore } from '@/stores/ui-store'
import ConversationList from '@/components/chat/ConversationList'

const MANAGE_NAV_ITEMS = [
  { label: '智能体', icon: Cpu, path: '/manage/agents' },
  { label: '技能', icon: Wrench, path: '/manage/skills' },
  { label: 'MCP 服务器', icon: Server, path: '/manage/servers' },
]

export default function Sidebar() {
  const { activeNav } = useUiStore()

  return (
    <div className="flex h-screen w-[260px] flex-col border-r bg-card">
      {activeNav === 'chat' && <ConversationList />}
      {activeNav === 'manage' && <ManageSidebar />}
      {activeNav === 'settings' && <SettingsSidebar />}
    </div>
  )
}

function ManageSidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="flex h-full flex-col">
      <div className="p-4">
        <h2 className="text-base font-semibold">管理</h2>
      </div>
      <Separator />
      <nav className="flex flex-col p-2">
        {MANAGE_NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname.startsWith(item.path)
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}

function SettingsSidebar() {
  return (
    <div className="flex h-full flex-col">
      <div className="p-4">
        <h2 className="text-base font-semibold">设置</h2>
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        <p className="text-sm text-muted-foreground">在右侧面板中修改设置</p>
      </div>
    </div>
  )
}
