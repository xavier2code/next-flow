import { useEffect, useMemo, useRef, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import type { UIMessage } from '@ai-sdk/react'
import { useLocation, useNavigate } from 'react-router'
import { useChatStore } from '@/stores/chat-store'
import { useUiStore } from '@/stores/ui-store'
import { useAuthStore } from '@/stores/auth-store'
import { useCreateConversation, useUpdateConversation, useConversation, useMessages } from '@/hooks/use-conversations'
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
  const location = useLocation()
  const getAccessToken = useAuthStore((s) => s.accessToken)
  const setCurrentConversation = useChatStore((s) => s.setCurrentConversation)
  const sidePanelOpen = useUiStore((s) => s.sidePanelOpen)
  const setSidePanelOpen = useUiStore((s) => s.setSidePanelOpen)
  const createConversation = useCreateConversation()
  const updateConversation = useUpdateConversation()
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)

  // Fetch conversation detail to restore agent selection
  const { data: conversationDetail } = useConversation(conversationId ?? null)

  // Fetch historical messages and convert to UIMessage format
  const { data: historyMessages } = useMessages(conversationId ?? null)
  const initialMessages = useMemo<UIMessage[]>(() => {
    if (!historyMessages) return []
    return historyMessages.map((m) => ({
      id: m.id,
      role: m.role as UIMessage['role'],
      parts: [{ type: 'text' as const, text: m.content }],
      createdAt: new Date(m.created_at),
    }))
  }, [historyMessages])

  // Sync selectedAgentId with conversation's agent_id
  useEffect(() => {
    if (conversationDetail) {
      setSelectedAgentId(conversationDetail.agent_id)
    }
  }, [conversationDetail?.agent_id])

  // useChat — only configure transport when conversationId is available (key remount guarantees this)
  const chatApi = conversationId
    ? `/api/v1/conversations/${conversationId}/chat`
    : undefined

  const { messages, sendMessage, setMessages, regenerate, stop, status, error } = useChat({
    id: conversationId ?? 'new',
    transport: chatApi
      ? new DefaultChatTransport({
          api: chatApi,
          fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
            return fetch(input, {
              ...init,
              headers: {
                ...init?.headers,
                Authorization: `Bearer ${getAccessToken}`,
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

  // Load historical messages into useChat when they arrive from API
  useEffect(() => {
    if (historyMessages && historyMessages.length > 0 && messages.length === 0) {
      setMessages(
        historyMessages.map((m) => ({
          id: m.id,
          role: m.role as UIMessage['role'],
          parts: [{ type: 'text' as const, text: m.content }],
          createdAt: new Date(m.created_at),
        })),
      )
    }
  }, [historyMessages, messages.length, setMessages])

  // Sync conversation ID when URL changes
  useEffect(() => {
    if (conversationId && conversationId !== useChatStore.getState().currentConversationId) {
      setCurrentConversation(conversationId)
    }
  }, [conversationId, setCurrentConversation])

  // Send pending message passed via navigate state after remount
  const pendingTextRef = useRef<string | null>(
    (location.state as { pendingText?: string })?.pendingText ?? null,
  )
  useEffect(() => {
    if (pendingTextRef.current && chatApi) {
      const text = pendingTextRef.current
      pendingTextRef.current = null
      navigate(location.pathname, { replace: true })
      setTimeout(() => sendMessage({ text }), 0)
    }
  }, [chatApi, sendMessage, navigate, location.pathname])

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
    if (conversationId) {
      updateConversation.mutate({
        id: conversationId,
        agent_id: agentId,
      })
    }
  }

  const handleSend = async (text: string) => {
    // Step 1: Ensure we have a conversation
    if (!conversationId) {
      try {
        const result = await createConversation.mutateAsync({
          title: text.slice(0, 50),
          agent_id: selectedAgentId ?? undefined,
        })
        setCurrentConversation(result.id)
        // Navigate with pendingText — key remount will create fresh useChat, then effect sends the message
        navigate(`/conversations/${result.id}`, { state: { pendingText: text } })
      } catch {
        // Creation failed
      }
      return
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
