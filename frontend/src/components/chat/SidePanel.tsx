import { X } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { useChatStore } from '@/stores/chat-store'
import { useUiStore } from '@/stores/ui-store'
import ThinkingEntry from './ThinkingEntry'
import ToolCallCard from './ToolCallCard'
import ToolResultCard from './ToolResultCard'

type EntryType = 'thinking' | 'tool_call' | 'tool_result'

interface CombinedEntry {
  id: string
  entryType: EntryType
  timestamp: number
  // Thinking
  content?: string
  // Tool call
  name?: string
  args?: Record<string, unknown>
  // Tool result
  result?: unknown
}

export default function SidePanel() {
  const { thinkingEntries, toolCallEntries, toolResultEntries } = useChatStore()
  const setSidePanelOpen = useUiStore((s) => s.setSidePanelOpen)

  // Combine and sort all entries by timestamp
  const allEntries: CombinedEntry[] = [
    ...thinkingEntries.map((e) => ({
      id: e.id,
      entryType: 'thinking' as const,
      timestamp: e.timestamp,
      content: e.content,
    })),
    ...toolCallEntries.map((e) => ({
      id: e.id,
      entryType: 'tool_call' as const,
      timestamp: e.timestamp,
      name: e.name,
      args: e.args,
    })),
    ...toolResultEntries.map((e) => ({
      id: e.id,
      entryType: 'tool_result' as const,
      timestamp: e.timestamp,
      name: e.name,
      result: e.result,
    })),
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
              {allEntries.map((entry) => {
                if (entry.entryType === 'thinking') {
                  return (
                    <ThinkingEntry
                      key={entry.id}
                      content={entry.content ?? ''}
                      timestamp={entry.timestamp}
                    />
                  )
                }
                if (entry.entryType === 'tool_call') {
                  return (
                    <ToolCallCard
                      key={entry.id}
                      name={entry.name ?? ''}
                      args={entry.args ?? {}}
                      timestamp={entry.timestamp}
                    />
                  )
                }
                if (entry.entryType === 'tool_result') {
                  return (
                    <ToolResultCard
                      key={entry.id}
                      name={entry.name ?? ''}
                      result={entry.result}
                      timestamp={entry.timestamp}
                    />
                  )
                }
                return null
              })}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
