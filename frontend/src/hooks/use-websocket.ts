import { useEffect, useRef, useCallback, useState } from 'react'
import type { ConnectionStatus } from '@/types/ws-events'
import { useChatStore } from '@/stores/chat-store'

interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus
}

const MAX_RECONNECT_ATTEMPTS = 5
const BASE_DELAY = 1000 // 1s, doubles each attempt

export function useWebSocket(token: string | null): UseWebSocketReturn {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const tokenRef = useRef(token)

  // Keep token ref in sync
  useEffect(() => {
    tokenRef.current = token
  }, [token])

  const connect = useCallback(() => {
    const currentToken = tokenRef.current
    if (!currentToken) return

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.onopen = null
      wsRef.current.onclose = null
      wsRef.current.onmessage = null
      wsRef.current.onerror = null
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close()
      }
    }

    setConnectionStatus('connecting')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/chat?token=${currentToken}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setConnectionStatus('connected')
      reconnectAttemptsRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        useChatStore.getState().handleWSEvent(parsed)
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      setConnectionStatus('disconnected')
      attemptReconnect()
    }

    ws.onerror = () => {
      // Error event is followed by close event, which handles reconnect
    }
  }, [])

  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      return
    }

    const delay = BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current)
    reconnectAttemptsRef.current += 1

    reconnectTimerRef.current = setTimeout(async () => {
      // Try to refresh token before reconnecting
      try {
        const { useAuthStore } = await import('@/stores/auth-store')
        await useAuthStore.getState().refreshTokens()
      } catch {
        // Refresh failed, stop reconnecting
        return
      }
      connect()
    }, delay)
  }, [connect])

  useEffect(() => {
    if (token) {
      connect()
    }

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.onopen = null
        wsRef.current.onclose = null
        wsRef.current.onmessage = null
        wsRef.current.onerror = null
        if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.close()
        }
        wsRef.current = null
      }
    }
  }, [token, connect])

  return { connectionStatus }
}
