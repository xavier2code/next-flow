// Entity types matching backend Pydantic schemas exactly

export interface User {
  id: string
  email: string
  display_name: string | null
  avatar_url: string | null
  role: string
  created_at: string
}

export interface Conversation {
  id: string
  title: string
  agent_id: string | null
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface Agent {
  id: string
  name: string
  system_prompt: string | null
  llm_config: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: string
  content: string
  created_at: string
}

export interface Skill {
  id: string
  name: string
  description: string | null
  version: string
  skill_type: string
  status: string
  permissions: Record<string, unknown> | null
  manifest: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface MCPServer {
  id: string
  name: string
  url: string
  transport_type: string
  status: string
  config: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ToolInfo {
  name: string
  namespaced_name: string
  description: string | null
  input_schema: Record<string, unknown> | null
}

// API response wrappers
export interface EnvelopeResponse<T> {
  data: T
  meta: Record<string, unknown> | null
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    cursor: string | null
    has_more: boolean
  }
}

export interface ApiError {
  error: {
    code: string
    message: string
  }
}

// Auth types (bare response, no envelope)
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name?: string
}

export interface RefreshRequest {
  refresh_token: string
}

// Settings
export interface SystemConfig {
  available_providers: string[]
  default_provider: string
  default_model: string
}

export interface UserSettings {
  preferences: Record<string, unknown>
}
