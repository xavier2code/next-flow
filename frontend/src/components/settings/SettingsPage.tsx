import { useNavigate } from 'react-router'
import { LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useUiStore } from '@/stores/ui-store'
import { useAuthStore } from '@/stores/auth-store'

export default function SettingsPage() {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useUiStore()
  const { user, logout } = useAuthStore()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-2xl p-6">
        <h1 className="mb-6 text-lg font-semibold">设置</h1>

        {/* Appearance */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-base font-semibold">外观</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>深色模式</Label>
                <p className="text-xs text-muted-foreground">
                  切换深色/浅色界面主题
                </p>
              </div>
              <Switch
                checked={theme === 'dark'}
                onChange={() => toggleTheme()}
              />
            </div>
          </CardContent>
        </Card>

        {/* Account */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-base font-semibold">账户</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>邮箱</Label>
              <span className="text-sm text-muted-foreground">{user?.email ?? '-'}</span>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <Label>显示名称</Label>
              <span className="text-sm text-muted-foreground">{user?.display_name ?? '-'}</span>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <Label>角色</Label>
              <Badge variant="outline">{user?.role ?? '-'}</Badge>
            </div>
          </CardContent>
        </Card>

        {/* About */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-base font-semibold">关于</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-sm font-medium">NextFlow v1.0</p>
              <p className="text-xs text-muted-foreground">通用 Agent 平台</p>
            </div>
          </CardContent>
        </Card>

        {/* Logout */}
        <Button variant="destructive" className="w-full" onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          退出登录
        </Button>
      </div>
    </ScrollArea>
  )
}
