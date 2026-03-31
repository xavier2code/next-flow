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
    expect(state.messages).toEqual([])
    expect(state.streamingMessage).toBeNull()
    expect(state.thinkingEntries).toEqual([])
    expect(state.toolCallEntries).toEqual([])
    expect(state.toolResultEntries).toEqual([])
    expect(state.currentConversationId).toBeNull()
    expect(state.isStreaming).toBe(false)
  })
})

describe('Chat store WS event handling', () => {
  it('handles chunk event', () => {
    const store = useChatStore.getState()
    store.handleWSEvent({ type: 'chunk', data: { content: 'Hello' } })
    const updated = useChatStore.getState()
    expect(updated.streamingMessage).not.toBeNull()
    expect(updated.streamingMessage?.content).toBe('Hello')
    // Reset
    useChatStore.getState().clearStreamingState()
  })

  it('handles done event', () => {
    const store = useChatStore.getState()
    // First add a streaming message
    store.handleWSEvent({ type: 'chunk', data: { content: 'Test' } })
    // Then done
    store.handleWSEvent({ type: 'done', data: { thread_id: 'test-thread' } })
    const updated = useChatStore.getState()
    expect(updated.streamingMessage).toBeNull()
    expect(updated.isStreaming).toBe(false)
    expect(updated.messages.length).toBe(1)
    expect(updated.messages[0].role).toBe('assistant')
    expect(updated.messages[0].content).toBe('Test')
  })

  it('handles thinking event', () => {
    useChatStore.getState().clearStreamingState()
    useChatStore.getState().handleWSEvent({ type: 'thinking', data: { content: 'Thinking...' } })
    const updated = useChatStore.getState()
    expect(updated.thinkingEntries.length).toBe(1)
    expect(updated.thinkingEntries[0].content).toBe('Thinking...')
  })

  it('handles tool_call event', () => {
    useChatStore.getState().clearStreamingState()
    useChatStore.getState().handleWSEvent({ type: 'tool_call', data: { name: 'search', args: { q: 'test' } } })
    const updated = useChatStore.getState()
    expect(updated.toolCallEntries.length).toBe(1)
    expect(updated.toolCallEntries[0].name).toBe('search')
  })

  it('handles tool_result event', () => {
    useChatStore.getState().clearStreamingState()
    useChatStore.getState().handleWSEvent({ type: 'tool_result', data: { name: 'search', result: 'found' } })
    const updated = useChatStore.getState()
    expect(updated.toolResultEntries.length).toBe(1)
    expect(updated.toolResultEntries[0].name).toBe('search')
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
