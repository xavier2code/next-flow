import { describe, it, expect } from 'vitest'
import { useAuthStore } from '@/stores/auth-store'
import { useUiStore } from '@/stores/ui-store'
import { useChatStore } from '@/stores/chat-store'

describe('Store initialization', () => {
  it('auth store has correct initial state', () => {
    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('ui store has correct initial state', () => {
    const state = useUiStore.getState()
    expect(state.activeNav).toBe('chat')
    expect(state.sidePanelOpen).toBe(false)
    expect(state.sidebarCollapsed).toBe(false)
  })

  it('chat store has correct initial state', () => {
    const state = useChatStore.getState()
    expect(state.currentConversationId).toBeNull()
  })
})

describe('Chat store actions', () => {
  it('setCurrentConversation updates conversation id', () => {
    useChatStore.getState().setCurrentConversation('conv-123')
    expect(useChatStore.getState().currentConversationId).toBe('conv-123')
    // Reset
    useChatStore.getState().setCurrentConversation(null)
  })

  it('setCurrentConversation accepts null to clear', () => {
    useChatStore.getState().setCurrentConversation('conv-456')
    useChatStore.getState().setCurrentConversation(null)
    expect(useChatStore.getState().currentConversationId).toBeNull()
  })
})

describe('Ui store actions', () => {
  it('setActiveNav updates navigation', () => {
    useUiStore.getState().setActiveNav('manage')
    expect(useUiStore.getState().activeNav).toBe('manage')
    useUiStore.getState().setActiveNav('chat')
  })

  it('setSidePanelOpen updates panel state', () => {
    useUiStore.getState().setSidePanelOpen(true)
    expect(useUiStore.getState().sidePanelOpen).toBe(true)
    useUiStore.getState().setSidePanelOpen(false)
  })
})
