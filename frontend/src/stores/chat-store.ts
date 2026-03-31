import { create } from 'zustand'
import type { Message, StreamingMessage, ThinkingEntry, ToolCallEntry, ToolResultEntry } from '@/types/api'
import type { WSEvent, ThinkingData, ToolCallData, ToolResultData, ChunkData, DoneData } from '@/types/ws-events'

interface ChatState {
  messages: Message[]
  streamingMessage: StreamingMessage | null
  thinkingEntries: ThinkingEntry[]
  toolCallEntries: ToolCallEntry[]
  toolResultEntries: ToolResultEntry[]
  currentConversationId: string | null
  isStreaming: boolean
}

interface ChatActions {
  setCurrentConversation: (id: string | null) => void
  addUserMessage: (content: string) => void
  handleWSEvent: (event: WSEvent) => void
  clearStreamingState: () => void
  setMessages: (messages: Message[]) => void
}

export const useChatStore = create<ChatState & ChatActions>()((set, get) => ({
  messages: [],
  streamingMessage: null,
  thinkingEntries: [],
  toolCallEntries: [],
  toolResultEntries: [],
  currentConversationId: null,
  isStreaming: false,

  setCurrentConversation: (id) => {
    set({
      currentConversationId: id,
      messages: [],
      streamingMessage: null,
      thinkingEntries: [],
      toolCallEntries: [],
      toolResultEntries: [],
      isStreaming: false,
    })
  },

  addUserMessage: (content) => {
    const { currentConversationId } = get()
    const msg: Message = {
      id: crypto.randomUUID(),
      conversation_id: currentConversationId ?? '',
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    set((state) => ({ messages: [...state.messages, msg] }))
    // Start streaming state
    set({
      streamingMessage: {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        isStreaming: true,
      },
      isStreaming: true,
    })
  },

  handleWSEvent: (event: WSEvent) => {
    switch (event.type) {
      case 'thinking': {
        const data = event.data as ThinkingData
        set((state) => ({
          thinkingEntries: [
            ...state.thinkingEntries,
            {
              id: crypto.randomUUID(),
              content: data.content,
              timestamp: Date.now(),
            },
          ],
        }))
        // Auto-open side panel via ui store
        import('@/stores/ui-store').then(({ useUiStore }) => {
          useUiStore.getState().setSidePanelOpen(true)
        })
        break
      }
      case 'tool_call': {
        const data = event.data as ToolCallData
        set((state) => ({
          toolCallEntries: [
            ...state.toolCallEntries,
            {
              id: data.id ?? crypto.randomUUID(),
              name: data.name,
              args: data.args,
              timestamp: Date.now(),
            },
          ],
        }))
        // Auto-open side panel via ui store
        import('@/stores/ui-store').then(({ useUiStore }) => {
          useUiStore.getState().setSidePanelOpen(true)
        })
        break
      }
      case 'tool_result': {
        const data = event.data as ToolResultData
        set((state) => ({
          toolResultEntries: [
            ...state.toolResultEntries,
            {
              id: crypto.randomUUID(),
              name: data.name,
              result: data.result,
              timestamp: Date.now(),
            },
          ],
        }))
        break
      }
      case 'chunk': {
        const data = event.data as ChunkData
        set((state) => {
          if (!state.streamingMessage) {
            return {
              streamingMessage: {
                id: crypto.randomUUID(),
                role: 'assistant' as const,
                content: data.content,
                isStreaming: true,
              },
              isStreaming: true,
            }
          }
          return {
            streamingMessage: {
              ...state.streamingMessage,
              content: state.streamingMessage.content + data.content,
            },
          }
        })
        break
      }
      case 'done': {
        const _data = event.data as DoneData
        const { streamingMessage } = get()
        if (streamingMessage) {
          const finalMsg: Message = {
            id: streamingMessage.id,
            conversation_id: get().currentConversationId ?? '',
            role: 'assistant',
            content: streamingMessage.content,
            created_at: new Date().toISOString(),
          }
          set((state) => ({
            messages: [...state.messages, finalMsg],
            streamingMessage: null,
            isStreaming: false,
          }))
        } else {
          set({ isStreaming: false })
        }
        break
      }
    }
  },

  clearStreamingState: () => {
    set({
      streamingMessage: null,
      thinkingEntries: [],
      toolCallEntries: [],
      toolResultEntries: [],
      isStreaming: false,
    })
  },

  setMessages: (messages) => {
    set({ messages })
  },
}))
