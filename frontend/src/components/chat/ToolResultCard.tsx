import { CheckCircle } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ToolResultCardProps {
  name: string
  result: unknown
  timestamp: number
}

export default function ToolResultCard({ name, result, timestamp }: ToolResultCardProps) {
  const time = new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  const isString = typeof result === 'string'
  const displayText = isString
    ? (result as string)
    : JSON.stringify(result, null, 2)

  return (
    <Card className="p-3">
      <div className="flex items-center gap-2">
        <CheckCircle className="h-3.5 w-3.5 text-green-500" />
        <span className="text-sm font-medium">{name}</span>
        <Badge
          className="border-green-500/20 bg-green-500/10 text-xs text-green-500"
        >
          结果
        </Badge>
        <span className="ml-auto text-xs text-muted-foreground">{time}</span>
      </div>
      <div className="mt-2">
        {isString ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {displayText}
          </p>
        ) : (
          <pre className="overflow-x-auto rounded bg-muted p-2 text-xs font-mono">
            {displayText}
          </pre>
        )}
      </div>
    </Card>
  )
}
