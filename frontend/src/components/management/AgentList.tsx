import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAgents, useDeleteAgent } from '@/hooks/use-agents'

interface AgentListProps {
  selectedAgentId: string | null
  onSelectAgent: (id: string | null) => void
  onCreateNew: () => void
}

export default function AgentList({ selectedAgentId, onSelectAgent, onCreateNew }: AgentListProps) {
  const { data: agents, isLoading } = useAgents()
  const deleteAgent = useDeleteAgent()
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null)

  const handleConfirmDelete = () => {
    if (deleteTarget) {
      deleteAgent.mutate(deleteTarget.id, {
        onSuccess: () => {
          if (selectedAgentId === deleteTarget.id) {
            onSelectAgent(null)
          }
          setDeleteTarget(null)
        },
      })
    }
  }

  return (
    <div className="flex h-full w-1/2 flex-col border-r">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="text-base font-semibold">智能体</h2>
        <Button size="sm" onClick={onCreateNew}>
          <Plus className="mr-1 h-4 w-4" />
          创建智能体
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
        ) : !agents || agents.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <p className="text-sm text-muted-foreground">暂无智能体</p>
            <p className="mt-1 text-xs text-muted-foreground">
              点击"创建智能体"来配置你的第一个 AI 助手。
            </p>
          </div>
        ) : (
          <div className="space-y-2 p-4">
            {agents.map((agent) => (
              <Card
                key={agent.id}
                className={`cursor-pointer p-3 transition-colors hover:bg-muted/50 ${
                  selectedAgentId === agent.id ? 'bg-primary/10 ring-1 ring-primary/20' : ''
                }`}
                onClick={() => onSelectAgent(agent.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-base font-semibold">{agent.name}</span>
                      {agent.llm_config && typeof agent.llm_config === 'object' && 'model' in agent.llm_config && (
                        <Badge variant="secondary" className="text-xs">
                          {String(agent.llm_config.model)}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      创建于 {new Date(agent.created_at).toLocaleDateString('zh-CN')}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTarget({ id: agent.id, name: agent.name })
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除智能体</DialogTitle>
            <DialogDescription>
              确定要删除智能体"{deleteTarget?.name}"吗？相关的对话将保留。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
