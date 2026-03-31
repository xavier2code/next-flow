import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { MCPServer, ToolInfo } from '@/types/api'

export function useMCPServers() {
  return useQuery({
    queryKey: ['mcp-servers'],
    queryFn: () => apiClient.get<MCPServer[]>('/api/v1/mcp-servers'),
    refetchInterval: 30_000, // 30s polling for status updates
  })
}

export function useMCPServer(id: string | undefined) {
  return useQuery({
    queryKey: ['mcp-server', id],
    queryFn: () => apiClient.get<MCPServer>(`/api/v1/mcp-servers/${id}`),
    enabled: !!id,
  })
}

export function useCreateMCPServer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; url: string; transport_type?: string; config?: Record<string, unknown> }) =>
      apiClient.post<MCPServer>('/api/v1/mcp-servers', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] })
    },
  })
}

export function useUpdateMCPServer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Pick<MCPServer, 'name' | 'url' | 'transport_type' | 'config'>>) =>
      apiClient.patch<MCPServer>(`/api/v1/mcp-servers/${id}`, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] })
      queryClient.invalidateQueries({ queryKey: ['mcp-server', variables.id] })
    },
  })
}

export function useDeleteMCPServer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.del(`/api/v1/mcp-servers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] })
    },
  })
}

export function useMCPServerTools(id: string | undefined) {
  return useQuery({
    queryKey: ['mcp-server-tools', id],
    queryFn: () => apiClient.get<ToolInfo[]>(`/api/v1/mcp-servers/${id}/tools`),
    enabled: !!id,
  })
}
