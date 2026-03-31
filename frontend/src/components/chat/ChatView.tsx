import { useEffect, useRef, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { useNavigate } from 'react-router'
import { useChatStore } from '@/stores/chat-store'
import { useUiStore } from '@/stores/ui-store'
import { useCreateConversation, useUpdateConversation, useConversation } from '@/hooks/use-conversations'
import { RefreshCw } from 'lucide-react'
import AgentDropdown from './AgentDropdown'
import ChatMessage from './ChatMessage'
import WelcomeScreen from './WelcomeScreen'
import InputBox from './InputBox'
import SidePanel from './SidePanel'

interface ChatViewProps {
  conversationId?: string
}

export default function ChatView({ conversationId }: ChatViewProps) {
  const navigate = useNavigate()
  const setCurrentConversation = useChatStore((s) => s.setCurrentConversation)
  const sidePanelOpen = useUiStore((s) => s.sidePanelOpen)
  const setSidePanelOpen = useUiStore((s) => s.setSidePanelOpen)
  const createConversation = useCreateConversation()
  const updateConversation = useUpdateConversation()
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)

  // Fetch conversation detail to restore agent selection
  const { data: conversationDetail } = useConversation(conversationId ?? null)

  // Sync selectedAgentId with conversation's agent_id
  useEffect(() => {
    if (conversationDetail) {
      setSelectedAgentId(conversationDetail.agent_id)
    }
  }, [conversationDetail?.agent_id])

  const activeConversationId = conversationId ?? useChatStore((s) => s.currentConversationId)

  // useChat configuration
  const chatApi = activeConversationId
    ? `/api/v1/conversations/${activeConversationId}/chat`
    : undefined

  const { messages, sendMessage, regenerate, stop, status, error } = useChat({
    transport: chatApi
      ? new DefaultChatTransport({
          api: chatApi,
          fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
            const token = localStorage.getItem('access_token')
            return fetch(input, {
              ...init,
              headers: {
                ...init?.headers,
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            })
          },
        })
      : undefined,
    onError: (err: Error) => {
      console.error('Chat error:', err)
    },
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Sync conversation ID when URL changes
  useEffect(() => {
    if (conversationId && conversationId !== useChatStore.getState().currentConversationId) {
      setCurrentConversation(conversationId)
    }
  }, [conversationId, setCurrentConversation])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-open side panel when tool invocations appear
  useEffect(() => {
    const hasToolInvocations = messages.some((m) =>
      m.parts.some((p) => p.type === 'dynamic-tool' || p.type.startsWith('tool-'))
    )
    if (hasToolInvocations) setSidePanelOpen(true)
  }, [messages, setSidePanelOpen])

  const handleAgentChange = (agentId: string) => {
    setSelectedAgentId(agentId)
    if (activeConversationId) {
      updateConversation.mutate({
        id: activeConversationId,
        agent_id: agentId,
      })
    }
  }

  const handleSend = async (text: string) => {
    let targetConversationId = activeConversationId

    // Step 1: Ensure we have a conversation
    if (!targetConversationId) {
      try {
        const result = await createConversation.mutateAsync({
          title: text.slice(0, 50),
          agent_id: selectedAgentId ?? undefined,
        })
        targetConversationId = result.id
        setCurrentConversation(targetConversationId)
        navigate(`/conversations/${targetConversationId}`)
        // After navigation, the useChat api will update via activeConversationId
        // Send the message on next tick so the hook reconfigures with the new conversation
        setTimeout(() => {
          sendMessage({ text })
        }, 0)
        return
      } catch {
        return
      }
    }

    // Step 2: Send via useChat
    sendMessage({ text })
  }

  const hasMessages = messages.length > 0

  return (
    <div className="flex h-full flex-col">
      {/* Header: 48px */}
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-4">
          <AgentDropdown
            value={selectedAgentId}
            onAgentChange={handleAgentChange}
          />
        </div>
        <div className="flex items-center gap-2">
          {status !== 'streaming' && status !== 'submitted' && messages.length > 0 && (
            <button
              onClick={() => regenerate()}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              <RefreshCw className="inline-block h-3.5 w-3.5" />
              <span className="ml-1">重新生成</span>
            </button>
          )}
          {status === 'streaming' && (
            <button
              onClick={stop}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Stop
            </button>
          )}
          {status === 'submitted' && (
            <span className="text-xs text-muted-foreground">Sending...</span>
          )}
          {error && (
            <span className="text-xs text-destructive">Error</span>
          )}
        </div>
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
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input box: fixed bottom */}
          <InputBox
            onSend={handleSend}
            disabled={status === 'submitted' || status === 'streaming'}
          />
        </div>

        {/* Side panel: 320px, collapsible */}
        {sidePanelOpen && <SidePanel messages={messages} />}
      </div>
    </div>
  )
}
