import { create } from 'zustand'

interface ChatState {
  currentConversationId: string | null
}

interface ChatActions {
  setCurrentConversation: (id: string | null) => void
}

export const useChatStore = create<ChatState & ChatActions>()((set) => ({
  currentConversationId: null,
  setCurrentConversation: (id) => {
    set({ currentConversationId: id })
  },
}))
