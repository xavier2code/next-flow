import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { UserSettings, SystemConfig } from '@/types/api'

export function useUserSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => apiClient.get<UserSettings>('/api/v1/settings'),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { preferences?: Record<string, unknown> }) =>
      apiClient.patch<UserSettings>('/api/v1/settings', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useSystemConfig() {
  return useQuery({
    queryKey: ['system-config'],
    queryFn: () => apiClient.get<SystemConfig>('/api/v1/settings/system'),
  })
}
