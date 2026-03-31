import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Slider,
} from '@/components/ui/slider'
import { useAgent, useCreateAgent, useUpdateAgent } from '@/hooks/use-agents'
import { useSystemConfig } from '@/hooks/use-settings'

interface AgentDetailProps {
  agentId: string | null
  isNew: boolean
  onCreated?: (id: string) => void
  onCancel?: () => void
}

const DEFAULT_MODELS = ['openai', 'anthropic', 'ollama']

export default function AgentDetail({ agentId, isNew, onCreated, onCancel }: AgentDetailProps) {
  const { data: agent, isLoading } = useAgent(isNew ? undefined : agentId ?? undefined)
  const { data: systemConfig } = useSystemConfig()
  const createAgent = useCreateAgent()
  const updateAgent = useUpdateAgent()

  const [name, setName] = useState('')
  const [model, setModel] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [temperature, setTemperature] = useState(0.7)

  // Sync form with agent data when it loads or changes
  useEffect(() => {
    if (agent) {
      setName(agent.name)
      const llmConfig = agent.llm_config as Record<string, unknown> | null
      setModel((llmConfig?.model as string) ?? '')
      setSystemPrompt(agent.system_prompt ?? '')
      setTemperature((llmConfig?.temperature as number) ?? 0.7)
    }
  }, [agent])

  // Reset form for new agent
  useEffect(() => {
    if (isNew) {
      setName('')
      setModel('')
      setSystemPrompt('')
      setTemperature(0.7)
    }
  }, [isNew])

  const availableProviders = systemConfig?.available_providers ?? DEFAULT_MODELS

  const handleSave = () => {
    const llmConfig = { model: model || 'openai', temperature }
    if (isNew) {
      createAgent.mutate(
        { name, system_prompt: systemPrompt || undefined, llm_config: llmConfig },
        {
          onSuccess: (data) => {
            onCreated?.(data.id)
          },
        },
      )
    } else if (agentId) {
      updateAgent.mutate({
        id: agentId,
        name,
        system_prompt: systemPrompt || undefined,
        llm_config: llmConfig,
      })
    }
  }

  if (!isNew && !agentId) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">选择一个智能体查看详情</p>
      </div>
    )
  }

  if (!isNew && isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-auto">
      <Card className="m-0 rounded-none border-0 shadow-none">
        <CardHeader className="border-b px-6 py-4">
          <CardTitle className="text-lg font-semibold">
            {isNew ? '创建智能体' : '编辑智能体'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 px-6 py-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="agent-name">名称</Label>
            <Input
              id="agent-name"
              placeholder="智能体名称"
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Model */}
          <div className="space-y-2">
            <Label htmlFor="agent-model">模型</Label>
            <Select value={model} onValueChange={(v: string | null) => setModel(v ?? '')}>
              <SelectTrigger id="agent-model">
                <SelectValue placeholder="选择模型" />
              </SelectTrigger>
              <SelectContent>
                {availableProviders.map((provider) => (
                  <SelectItem key={provider} value={provider}>
                    {provider}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* System Prompt */}
          <div className="space-y-2">
            <Label htmlFor="agent-prompt">系统提示词</Label>
            <Textarea
              id="agent-prompt"
              placeholder="系统提示词..."
              maxLength={4000}
              rows={8}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">{systemPrompt.length}/4000</p>
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Temperature</Label>
              <span className="text-sm font-medium">{temperature.toFixed(1)}</span>
            </div>
            <Slider
              min={0}
              max={2}
              step={0.1}
              value={[temperature]}
              onValueChange={(value: number | readonly number[]) => {
                const v = Array.isArray(value) ? value[0] : value
                setTemperature(typeof v === 'number' ? v : 0)
              }}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>0.0 (精确)</span>
              <span>2.0 (创造)</span>
            </div>
          </div>

          <Separator />

          {/* Actions */}
          <div className="flex gap-3">
            <Button onClick={handleSave} disabled={!name.trim()}>
              {isNew ? '创建智能体' : '保存'}
            </Button>
            {isNew && onCancel && (
              <Button variant="outline" onClick={onCancel}>
                取消
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
