import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Skill, ToolInfo } from '@/types/api'

export function useSkills() {
  return useQuery({
    queryKey: ['skills'],
    queryFn: () => apiClient.get<Skill[]>('/api/v1/skills'),
  })
}

export function useSkill(id: string | undefined) {
  return useQuery({
    queryKey: ['skill', id],
    queryFn: () => apiClient.get<Skill>(`/api/v1/skills/${id}`),
    enabled: !!id,
  })
}

export function useUploadSkill() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      // Use fetch directly to avoid Content-Type header (browser must set multipart boundary)
      const token = (await import('@/stores/auth-store')).useAuthStore.getState().accessToken
      const response = await fetch('/api/v1/skills', {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      })
      if (!response.ok) {
        const errorBody = await response.json().catch(() => null)
        throw errorBody?.error?.message || 'Upload failed'
      }
      const json = await response.json()
      return json.data as Skill
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
    },
  })
}

export function useToggleSkill() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, enable }: { id: string; enable: boolean }) => {
      const endpoint = enable ? 'enable' : 'disable'
      return apiClient.post<Skill>(`/api/v1/skills/${id}/${endpoint}`)
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      queryClient.invalidateQueries({ queryKey: ['skill', variables.id] })
    },
  })
}

export function useDeleteSkill() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.del(`/api/v1/skills/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
    },
  })
}

export function useSkillTools(id: string | undefined) {
  return useQuery({
    queryKey: ['skill-tools', id],
    queryFn: () => apiClient.get<ToolInfo[]>(`/api/v1/skills/${id}/tools`),
    enabled: !!id,
  })
}
