import { useParams } from 'react-router'
import { useWebSocket } from '@/hooks/use-websocket'
import { useAuthStore } from '@/stores/auth-store'
import ChatView from '@/components/chat/ChatView'

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const accessToken = useAuthStore((s) => s.accessToken)
  const { connectionStatus } = useWebSocket(accessToken)

  return (
    <ChatView
      conversationId={id}
      connectionStatus={connectionStatus}
    />
  )
}
