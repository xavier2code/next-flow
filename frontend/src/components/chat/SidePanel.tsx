import { X } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { useChatStore } from '@/stores/chat-store'
import { useUiStore } from '@/stores/ui-store'

export default function SidePanel() {
  const { thinkingEntries, toolCallEntries, toolResultEntries } = useChatStore()
  const setSidePanelOpen = useUiStore((s) => s.setSidePanelOpen)

  // Combine and sort all entries by timestamp
  const allEntries = [
    ...thinkingEntries.map((e) => ({ ...e, entryType: 'thinking' as const })),
    ...toolCallEntries.map((e) => ({ ...e, entryType: 'tool_call' as const })),
    ...toolResultEntries.map((e) => ({ ...e, entryType: 'tool_result' as const })),
  ].sort((a, b) => a.timestamp - b.timestamp)

  return (
    <div className="flex h-full w-80 flex-col border-l bg-card">
      {/* Header */}
      <div className="flex h-12 items-center justify-between border-b px-4">
        <h3 className="text-base font-semibold">执行详情</h3>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setSidePanelOpen(false)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Entries list */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {allEntries.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              <span>等待执行事件</span>
              <span className="ml-1 animate-pulse">...</span>
            </div>
          ) : (
            <div className="space-y-3">
              {allEntries.map((entry) => (
                <div key={entry.id} className="text-xs text-muted-foreground">
                  [{entry.entryType}] {entry.id.slice(0, 8)}
                </div>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
