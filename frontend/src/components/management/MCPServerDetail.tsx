import { useState, useEffect } from 'react'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { StatusDot } from './StatusDot'
import { useMCPServer, useCreateMCPServer, useUpdateMCPServer, useDeleteMCPServer, useMCPServerTools } from '@/hooks/use-mcp-servers'

interface MCPServerDetailProps {
  serverId: string | null
  isNew: boolean
  onCreated?: (id: string) => void
  onCancel?: () => void
}

const STATUS_LABELS: Record<string, string> = {
  connected: '已连接',
  connecting: '连接中',
  disconnected: '已断开',
  error: '错误',
}

export default function MCPServerDetail({ serverId, isNew, onCreated, onCancel }: MCPServerDetailProps) {
  const { data: server, isLoading } = useMCPServer(isNew ? undefined : serverId ?? undefined)
  const { data: tools } = useMCPServerTools(isNew ? undefined : serverId ?? undefined)
  const createServer = useCreateMCPServer()
  const updateServer = useUpdateMCPServer()
  const deleteServer = useDeleteMCPServer()

  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [transportType, setTransportType] = useState('streamable_http')
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // Sync form when server data loads
  useEffect(() => {
    if (server) {
      setName(server.name)
      setUrl(server.url)
      setTransportType(server.transport_type)
    }
  }, [server])

  // Reset form for new server
  useEffect(() => {
    if (isNew) {
      setName('')
      setUrl('')
      setTransportType('streamable_http')
    }
  }, [isNew])

  const handleSave = () => {
    if (isNew) {
      createServer.mutate(
        { name, url, transport_type: transportType },
        {
          onSuccess: (data) => {
            onCreated?.(data.id)
          },
        },
      )
    } else if (serverId) {
      updateServer.mutate({
        id: serverId,
        name,
        url,
        transport_type: transportType,
      })
    }
  }

  const handleConfirmDelete = () => {
    if (!serverId) return
    deleteServer.mutate(serverId, {
      onSuccess: () => setShowDeleteDialog(false),
    })
  }

  if (!isNew && !serverId) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">选择一个服务器查看详情</p>
      </div>
    )
  }

  if (!isNew && isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6">
        <Card className="m-0 rounded-none border-0 shadow-none">
          <CardHeader className="px-0 pt-0">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold">
                {isNew ? '注册 MCP 服务器' : server?.name ?? '服务器详情'}
              </CardTitle>
              {!isNew && server && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:text-destructive"
                  onClick={() => setShowDeleteDialog(true)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </CardHeader>

          <CardContent className="space-y-6 px-0 pb-0">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="server-name">名称</Label>
              <Input
                id="server-name"
                placeholder="服务器名称"
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {/* URL */}
            <div className="space-y-2">
              <Label htmlFor="server-url">URL</Label>
              <Input
                id="server-url"
                placeholder="https://..."
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>

            {/* Transport */}
            <div className="space-y-2">
              <Label htmlFor="server-transport">传输方式</Label>
              <Select value={transportType} onValueChange={setTransportType}>
                <SelectTrigger id="server-transport">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="streamable_http">Streamable HTTP</SelectItem>
                  <SelectItem value="sse">SSE</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Save */}
            <div className="flex gap-3">
              <Button onClick={handleSave} disabled={!name.trim() || !url.trim()}>
                {isNew ? '注册' : '保存'}
              </Button>
              {isNew && onCancel && (
                <Button variant="outline" onClick={onCancel}>
                  取消
                </Button>
              )}
            </div>

            {/* Status & tools -- only for existing server */}
            {!isNew && server && (
              <>
                <Separator />

                {/* Status */}
                <div className="space-y-2">
                  <Label>连接状态</Label>
                  <div className="flex items-center gap-2">
                    <StatusDot status={server.status} />
                    <span className="text-sm">{STATUS_LABELS[server.status] ?? server.status}</span>
                  </div>
                </div>

                <Separator />

                {/* Tools */}
                <div className="space-y-3">
                  <Label>已发现工具</Label>
                  {!tools || tools.length === 0 ? (
                    <div className="rounded-lg border border-dashed p-4 text-center">
                      <p className="text-sm text-muted-foreground">未发现工具</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        服务器已连接，但未发现可用工具。请检查服务器配置。
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {tools.map((tool) => (
                        <div key={tool.namespaced_name} className="rounded-lg border p-3">
                          <p className="font-mono text-sm font-medium">{tool.namespaced_name}</p>
                          {tool.description && (
                            <p className="mt-1 text-xs text-muted-foreground">{tool.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Delete confirmation */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>移除服务器</DialogTitle>
            <DialogDescription>
              确定要移除 MCP 服务器"{server?.name}"吗？已发现的工具将变为不可用。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              移除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ScrollArea>
  )
}
