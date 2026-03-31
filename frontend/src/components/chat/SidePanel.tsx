import { X } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { useUiStore } from '@/stores/ui-store'
import type { UIMessage } from '@ai-sdk/react'
import ToolCallCard from './ToolCallCard'
import ToolResultCard from './ToolResultCard'

interface SidePanelProps {
  messages: UIMessage[]
}

interface CombinedEntry {
  id: string
  entryType: 'tool_call' | 'tool_result'
  toolName: string
  args?: Record<string, unknown>
  result?: unknown
}

export default function SidePanel({ messages }: SidePanelProps) {
  const setSidePanelOpen = useUiStore((s) => s.setSidePanelOpen)

  // Extract all tool invocations from messages, sorted by message order
  const allEntries: CombinedEntry[] = messages.flatMap((msg) =>
    (msg.toolInvocations ?? []).map((inv) => ({
      id: inv.toolCallId,
      entryType: inv.state === 'result' ? ('tool_result' as const) : ('tool_call' as const),
      toolName: inv.toolName,
      args: typeof inv.args === 'object' ? (inv.args as Record<string, unknown>) : undefined,
      result: inv.state === 'result' ? inv.result : undefined,
    }))
  )

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
              {allEntries.map((entry) =>
                entry.entryType === 'tool_call' ? (
                  <ToolCallCard
                    key={entry.id}
                    name={entry.toolName}
                    args={entry.args ?? {}}
                    timestamp={Date.now()}
                  />
                ) : (
                  <ToolResultCard
                    key={entry.id}
                    name={entry.toolName}
                    result={entry.result}
                    timestamp={Date.now()}
                  />
                )
              )}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
