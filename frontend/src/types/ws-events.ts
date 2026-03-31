export type WSEventType = 'thinking' | 'tool_call' | 'tool_result' | 'chunk' | 'done'

export interface WSEvent {
  type: WSEventType
  data: unknown
}

export interface ThinkingData {
  content: string
}

export interface ToolCallData {
  name: string
  args: Record<string, unknown>
  id?: string
}

export interface ToolResultData {
  name: string
  result: unknown
}

export interface ChunkData {
  content: string
}

export interface DoneData {
  thread_id?: string
  error?: string
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'
