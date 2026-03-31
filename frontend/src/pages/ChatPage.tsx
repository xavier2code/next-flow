import { useParams } from 'react-router'
import { useUiStore } from '@/stores/ui-store'
import ChatView from '@/components/chat/ChatView'

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const connectionStatus = useUiStore((s) => s.connectionStatus)

  return (
    <ChatView
      conversationId={id}
      connectionStatus={connectionStatus}
    />
  )
}
