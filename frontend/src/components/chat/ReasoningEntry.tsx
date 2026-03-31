import { useState } from 'react'
import { Brain } from 'lucide-react'
import { ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

interface ReasoningEntryProps {
  text: string
  state?: 'streaming' | 'done'
}

export default function ReasoningEntry({ text, state }: ReasoningEntryProps) {
  const [isOpen, setIsOpen] = useState(state === 'streaming')

  return (
    <Card className="p-3">
      <div className="flex items-center gap-2">
        <Brain className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-sm font-medium">思考</span>
        <Badge
          className={
            state === 'streaming'
              ? 'border-blue-500/20 bg-blue-500/10 text-xs text-blue-500'
              : 'border-green-500/20 bg-green-500/10 text-xs text-green-500'
          }
        >
          {state === 'streaming' ? '思考中...' : '完成'}
        </Badge>
      </div>

      <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-2">
        <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <ChevronDown
            className={`h-3 w-3 transition-transform ${
              isOpen ? 'rotate-0' : '-rotate-90'
            }`}
          />
          推理过程
        </CollapsibleTrigger>
        <CollapsibleContent>
          <p
            className={`mt-1 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground ${
              state === 'streaming' ? 'animate-pulse' : ''
            }`}
          >
            {text}
          </p>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
