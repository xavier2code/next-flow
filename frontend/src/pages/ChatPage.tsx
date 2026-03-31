import { useParams } from 'react-router'
import ChatView from '@/components/chat/ChatView'

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  return <ChatView conversationId={id} />
}
