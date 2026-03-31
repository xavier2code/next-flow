import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from '@/components/ui/select'
import { useAgents } from '@/hooks/use-agents'

interface AgentDropdownProps {
  value: string | null
  onAgentChange: (agentId: string) => void
}

export default function AgentDropdown({
  value,
  onAgentChange,
}: AgentDropdownProps) {
  const { data: agents = [] } = useAgents()
  const selectedAgent = agents.find((a) => a.id === value)

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-medium text-muted-foreground">智能体</span>
      <Select value={value ?? undefined} onValueChange={(v: string | null) => { if (v) onAgentChange(v) }}>
        <SelectTrigger className="h-8 w-[180px]">
          <span className={!selectedAgent ? 'text-muted-foreground' : ''}>
            {selectedAgent?.name ?? '选择智能体'}
          </span>
        </SelectTrigger>
        <SelectContent>
          {agents.map((agent) => (
            <SelectItem key={agent.id} value={agent.id}>
              {agent.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
