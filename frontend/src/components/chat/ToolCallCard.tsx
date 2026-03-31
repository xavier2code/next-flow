import { useState } from 'react'
import { Wrench } from 'lucide-react'
import { ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

interface ToolCallCardProps {
  name: string
  args: Record<string, unknown>
  timestamp: number
}

export default function ToolCallCard({ name, args, timestamp }: ToolCallCardProps) {
  const argsStr = JSON.stringify(args, null, 2)
  const isShort = argsStr.length < 100
  const [isOpen, setIsOpen] = useState(isShort)

  const time = new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  return (
    <Card className="p-3">
      <div className="flex items-center gap-2">
        <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-sm font-medium">{name}</span>
        <Badge variant="secondary" className="text-xs">
          调用
        </Badge>
        <span className="ml-auto text-xs text-muted-foreground">{time}</span>
      </div>

      {argsStr !== '{}' && (
        <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-2">
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
            <ChevronDown
              className={`h-3 w-3 transition-transform ${
                isOpen ? 'rotate-0' : '-rotate-90'
              }`}
            />
            参数
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre className="mt-1 overflow-x-auto rounded bg-muted p-2 text-xs font-mono">
              {argsStr}
            </pre>
          </CollapsibleContent>
        </Collapsible>
      )}
    </Card>
  )
}
