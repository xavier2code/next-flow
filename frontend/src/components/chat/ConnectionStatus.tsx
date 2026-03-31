import type { ConnectionStatus } from '@/types/ws-events'

interface ConnectionStatusProps {
  status: ConnectionStatus
}

export default function ConnectionStatusIndicator({
  status,
}: ConnectionStatusProps) {
  const dotClass =
    status === 'connected'
      ? 'bg-green-500'
      : status === 'connecting'
        ? 'bg-yellow-500'
        : 'bg-red-500'

  const label =
    status === 'connected'
      ? '已连接'
      : status === 'connecting'
        ? '连接中...'
        : '已断开'

  return (
    <div className="flex items-center gap-1.5">
      <div className={`h-2 w-2 rounded-full ${dotClass}`} />
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}
