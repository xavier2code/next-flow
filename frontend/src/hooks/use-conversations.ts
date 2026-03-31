import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Conversation, PaginatedResponse } from '@/types/api'

interface ConversationListResult {
  data: Conversation[]
  meta: {
    cursor: string | null
    has_more: boolean
  }
}

export function useConversations(cursor?: string) {
  return useQuery<ConversationListResult>({
    queryKey: cursor ? ['conversations', cursor] : ['conversations'],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('limit', '20')
      if (cursor) params.set('cursor', cursor)
      return apiClient.get<PaginatedResponse<Conversation>>(
        `/api/v1/conversations?${params.toString()}`,
      )
    },
  })
}

export function useConversation(id: string | null) {
  return useQuery<Conversation>({
    queryKey: ['conversation', id],
    queryFn: () => apiClient.get<Conversation>(`/api/v1/conversations/${id}`),
    enabled: !!id,
  })
}

export function useCreateConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { title: string }) =>
      apiClient.post<Conversation>('/api/v1/conversations', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}

export function useDeleteConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => apiClient.del(`/api/v1/conversations/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}
