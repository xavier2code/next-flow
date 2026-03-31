import { useNavigate } from 'react-router'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useState } from 'react'
import { useConversations, useCreateConversation, useDeleteConversation } from '@/hooks/use-conversations'
import { useChatStore } from '@/stores/chat-store'
import EmptyState from '@/components/shared/EmptyState'

export default function ConversationList() {
  const navigate = useNavigate()
  const { data, isLoading } = useConversations()
  const createConversation = useCreateConversation()
  const deleteConversation = useDeleteConversation()
  const currentConversationId = useChatStore((s) => s.currentConversationId)
  const setCurrentConversation = useChatStore((s) => s.setCurrentConversation)

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const conversations = data?.data ?? []

  const handleCreate = async () => {
    try {
      const result = await createConversation.mutateAsync({
        title: '新对话',
      })
      setCurrentConversation(result.id)
      navigate(`/conversations/${result.id}`)
    } catch {
      // Creation failed
    }
  }

  const handleSelect = (id: string) => {
    setCurrentConversation(id)
    navigate(`/conversations/${id}`)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteConversation.mutateAsync(deleteTarget)
      if (currentConversationId === deleteTarget) {
        setCurrentConversation(null)
        navigate('/')
      }
    } catch {
      // Delete failed
    }
    setDeleteTarget(null)
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    if (days < 7) return `${days}天前`
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <h2 className="text-base font-semibold">对话</h2>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={handleCreate}
          disabled={createConversation.isPending}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* List */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="space-y-2 p-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex flex-col gap-2 rounded-lg p-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4">
            <EmptyState
              heading="暂无对话"
              body='点击"新建对话"开始你的第一次对话。'
            />
          </div>
        ) : (
          <div className="space-y-0.5 p-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors hover:bg-muted ${
                  currentConversationId === conv.id ? 'bg-primary/10' : ''
                }`}
                onClick={() => handleSelect(conv.id)}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">
                    {conv.title || '新对话'}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {formatTime(conv.updated_at)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0 opacity-0 group-hover:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation()
                    setDeleteTarget(conv.id)
                  }}
                >
                  <Trash2 className="h-3 w-3 text-muted-foreground" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除对话</DialogTitle>
            <DialogDescription>
              确定要删除这个对话吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
