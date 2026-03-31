import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useUiStore } from '@/stores/ui-store'

export default function Sidebar() {
  const { activeNav } = useUiStore()

  return (
    <div className="flex h-screen w-[260px] flex-col border-r bg-card">
      {activeNav === 'chat' && <ChatSidebar />}
      {activeNav === 'manage' && <ManageSidebar />}
      {activeNav === 'settings' && <SettingsSidebar />}
    </div>
  )
}

function ChatSidebar() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between p-4">
        <h2 className="text-base font-semibold">对话</h2>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">暂无对话</p>
          <p className="mt-1 text-xs text-muted-foreground">
            点击"新建对话"开始你的第一次对话。
          </p>
        </div>
      </div>
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
