import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useChatStore } from '@/stores/chat-store'
import { useUiStore } from '@/stores/ui-store'
import { apiClient } from '@/lib/api-client'
import { useCreateConversation } from '@/hooks/use-conversations'
import type { ConnectionStatus } from '@/types/ws-events'
import ConnectionStatusIndicator from './ConnectionStatus'
import AgentDropdown from './AgentDropdown'
import MessageBubble from './MessageBubble'
import StreamingText from './StreamingText'
import WelcomeScreen from './WelcomeScreen'
import InputBox from './InputBox'
import SidePanel from './SidePanel'

interface ChatViewProps {
  conversationId?: string
  connectionStatus: ConnectionStatus
}

export default function ChatView({
  conversationId,
  connectionStatus,
}: ChatViewProps) {
  const navigate = useNavigate()
  const {
    messages,
    streamingMessage,
    isStreaming,
    currentConversationId,
    setCurrentConversation,
    addUserMessage,
  } = useChatStore()
  const sidePanelOpen = useUiStore((s) => s.sidePanelOpen)
  const createConversation = useCreateConversation()
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load messages when conversation changes (via sidebar click or URL navigation)
  useEffect(() => {
    if (!conversationId) return

    if (conversationId !== currentConversationId) {
      setCurrentConversation(conversationId)
    }

    apiClient
      .get<{ id: string; conversation_id: string; role: string; content: string; created_at: string }[]>(
        `/api/v1/conversations/${conversationId}/messages`,
      )
      .then((data) => {
        if (Array.isArray(data)) {
          useChatStore.getState().setMessages(data)
        }
      })
      .catch(() => {
        // Conversation may not exist
      })
  }, [conversationId])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage])

  const handleSend = async (text: string) => {
    let activeConversationId = currentConversationId

    // Step 1: Ensure we have a conversation
    if (!activeConversationId) {
      try {
        const result = await createConversation.mutateAsync({
          title: text.slice(0, 50),
        })
        activeConversationId = result.id
        setCurrentConversation(activeConversationId)
        navigate(`/conversations/${activeConversationId}`)
      } catch {
        // Failed to create conversation - show error
        return
      }
    }

    // Step 2: Optimistically show the user message
    addUserMessage(text)

    // Step 3: Send message to backend (returns 202)
    try {
      await apiClient.post(
        `/api/v1/conversations/${activeConversationId}/messages`,
        { content: text },
      )
    } catch {
      // Message send failed - streaming events won't arrive
    }
  }

  const hasMessages = messages.length > 0 || streamingMessage

  return (
    <div className="flex h-full flex-col">
      {/* Header: 48px */}
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-4">
          <AgentDropdown
            value={selectedAgentId}
            onAgentChange={setSelectedAgentId}
          />
        </div>
        <ConnectionStatusIndicator status={connectionStatus} />
      </div>

      {/* Content area: flex-1, split between messages and side panel */}
      <div className="flex flex-1 overflow-hidden">
        {/* Message stream */}
        <div className="flex flex-1 flex-col">
          <div className="flex-1 overflow-y-auto p-4">
            {!hasMessages ? (
              <WelcomeScreen onSelectPrompt={handleSend} />
            ) : (
              <div className="space-y-4">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                {streamingMessage && (
                  <StreamingText
                    content={streamingMessage.content}
                    isStreaming={isStreaming}
                  />
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input box: fixed bottom */}
          <InputBox onSend={handleSend} />
        </div>

        {/* Side panel: 320px, collapsible */}
        {sidePanelOpen && <SidePanel />}
      </div>
    </div>
  )
}
