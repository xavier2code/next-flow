import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

interface ThinkingEntryProps {
  content: string
  timestamp: number
}

export default function ThinkingEntry({ content, timestamp }: ThinkingEntryProps) {
  const [isOpen, setIsOpen] = useState(false)

  const time = new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-muted">
        <ChevronDown
          className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${
            isOpen ? 'rotate-0' : '-rotate-90'
          }`}
        />
        <span className="text-xs font-medium text-muted-foreground">
          思考过程
        </span>
        <span className="ml-auto text-xs text-muted-foreground">{time}</span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="px-2 pb-2 pl-7">
          <p className="text-sm leading-relaxed text-muted-foreground">
            {content}
          </p>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
