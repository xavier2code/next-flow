import { cn } from '@/lib/utils'

const STATUS_COLORS: Record<string, string> = {
  connected: 'bg-green-500',
  connecting: 'bg-yellow-500',
  disconnected: 'bg-red-500',
  error: 'bg-red-500',
}

interface StatusDotProps {
  status: string
  className?: string
}

export function StatusDot({ status, className }: StatusDotProps) {
  const colorClass = STATUS_COLORS[status.toLowerCase()] ?? 'bg-gray-500'
  return (
    <div
      className={cn('h-2.5 w-2.5 shrink-0 rounded-full', colorClass, className)}
      title={status}
    />
  )
}
