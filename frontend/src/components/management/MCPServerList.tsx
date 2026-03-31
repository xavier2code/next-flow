import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { StatusDot } from './StatusDot'
import { useMCPServers } from '@/hooks/use-mcp-servers'

interface MCPServerListProps {
  selectedServerId: string | null
  onSelectServer: (id: string | null) => void
  onCreateNew: () => void
}

const STATUS_LABELS: Record<string, string> = {
  connected: '已连接',
  connecting: '连接中',
  disconnected: '已断开',
  error: '错误',
}

export default function MCPServerList({ selectedServerId, onSelectServer, onCreateNew }: MCPServerListProps) {
  const { data: servers, isLoading } = useMCPServers()

  return (
    <div className="flex h-full w-1/2 flex-col border-r">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="text-base font-semibold">MCP 服务器</h2>
        <Button size="sm" onClick={onCreateNew}>
          <Plus className="mr-1 h-4 w-4" />
          注册服务器
        </Button>
      </div>

      {/* List */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full rounded-lg" />
            ))}
          </div>
        ) : !servers || servers.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <p className="text-sm text-muted-foreground">暂无 MCP 服务器</p>
            <p className="mt-1 text-xs text-muted-foreground">
              点击"注册服务器"来连接外部工具服务。
            </p>
          </div>
        ) : (
          <div className="space-y-2 p-4">
            {servers.map((server) => (
              <Card
                key={server.id}
                className={`cursor-pointer p-3 transition-colors hover:bg-muted/50 ${
                  selectedServerId === server.id ? 'bg-primary/10 ring-1 ring-primary/20' : ''
                }`}
                onClick={() => onSelectServer(server.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <span className="text-base font-semibold">{server.name}</span>
                    <p className="mt-1 truncate text-xs text-muted-foreground">{server.url}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <div className="flex items-center gap-1.5">
                      <StatusDot status={server.status} />
                      <span className="text-xs text-muted-foreground">
                        {STATUS_LABELS[server.status] ?? server.status}
                      </span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {server.transport_type}
                    </Badge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
