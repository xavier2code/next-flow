import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
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
  const { data: agentsData } = useAgents()
  const agents = agentsData?.data ?? []

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-medium text-muted-foreground">智能体</span>
      <Select value={value ?? undefined} onValueChange={onAgentChange}>
        <SelectTrigger className="h-8 w-[180px]">
          <SelectValue placeholder="选择智能体" />
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
