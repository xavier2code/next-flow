import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Agent, PaginatedResponse } from '@/types/api'

interface AgentListResult {
  data: Agent[]
  meta: {
    cursor: string | null
    has_more: boolean
  }
}

export function useAgents() {
  return useQuery<AgentListResult>({
    queryKey: ['agents'],
    queryFn: async () => {
      return apiClient.get<PaginatedResponse<Agent>>('/api/v1/agents')
    },
  })
}

export function useAgent(id: string | null) {
  return useQuery<Agent>({
    queryKey: ['agent', id],
    queryFn: () => apiClient.get<Agent>(`/api/v1/agents/${id}`),
    enabled: !!id,
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: {
      name: string
      system_prompt?: string
      llm_config?: Record<string, unknown>
    }) => apiClient.post<Agent>('/api/v1/agents', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: {
      id: string
      name?: string
      system_prompt?: string
      llm_config?: Record<string, unknown>
    }) => apiClient.patch<Agent>(`/api/v1/agents/${id}`, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['agent', variables.id] })
    },
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => apiClient.del(`/api/v1/agents/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}
