import { useUiStore } from '@/stores/ui-store'
import ConversationList from '@/components/chat/ConversationList'

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
  return (
    <div className="flex h-full flex-col">
      <div className="p-4">
        <h2 className="text-base font-semibold">管理</h2>
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        <p className="text-sm text-muted-foreground">选择管理类别</p>
      </div>
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
        <p className="text-sm text-muted-foreground">设置选项</p>
      </div>
    </div>
  )
}
