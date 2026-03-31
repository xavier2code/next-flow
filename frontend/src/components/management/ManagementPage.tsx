import { useState } from 'react'
import { useLocation } from 'react-router'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import AgentList from './AgentList'
import AgentDetail from './AgentDetail'
import SkillList from './SkillList'
import SkillDetail from './SkillDetail'
import MCPServerList from './MCPServerList'
import MCPServerDetail from './MCPServerDetail'

function getTabFromPath(pathname: string): string {
  if (pathname.includes('/manage/skills')) return 'skills'
  if (pathname.includes('/manage/servers')) return 'servers'
  return 'agents'
}

export default function ManagementPage() {
  const location = useLocation()
  const currentTab = getTabFromPath(location.pathname)

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [isCreatingAgent, setIsCreatingAgent] = useState(false)
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null)
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null)
  const [isCreatingServer, setIsCreatingServer] = useState(false)

  return (
    <div className="flex h-full flex-col">
      <Tabs defaultValue={currentTab} className="flex flex-1 flex-col">
        <TabsList variant="line" className="h-10 w-full justify-start rounded-none border-b bg-transparent px-4">
          <TabsTrigger value="agents">智能体</TabsTrigger>
          <TabsTrigger value="skills">技能</TabsTrigger>
          <TabsTrigger value="servers">MCP 服务器</TabsTrigger>
        </TabsList>

        <TabsContent value="agents" className="flex-1 overflow-hidden">
          <div className="flex h-full">
            <AgentList
              selectedAgentId={isCreatingAgent ? null : selectedAgentId}
              onSelectAgent={(id) => { setSelectedAgentId(id); setIsCreatingAgent(false) }}
              onCreateNew={() => { setIsCreatingAgent(true); setSelectedAgentId(null) }}
            />
            <div className="flex-1">
              <AgentDetail
                agentId={isCreatingAgent ? null : selectedAgentId}
                isNew={isCreatingAgent}
                onCreated={(id) => { setSelectedAgentId(id); setIsCreatingAgent(false) }}
                onCancel={() => { setIsCreatingAgent(false); setSelectedAgentId(null) }}
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="skills" className="flex-1 overflow-hidden">
          <div className="flex h-full">
            <SkillList
              selectedSkillId={selectedSkillId}
              onSelectSkill={setSelectedSkillId}
            />
            <div className="flex-1">
              <SkillDetail skillId={selectedSkillId} />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="servers" className="flex-1 overflow-hidden">
          <div className="flex h-full">
            <MCPServerList
              selectedServerId={isCreatingServer ? null : selectedServerId}
              onSelectServer={(id) => { setSelectedServerId(id); setIsCreatingServer(false) }}
              onCreateNew={() => { setIsCreatingServer(true); setSelectedServerId(null) }}
            />
            <div className="flex-1">
              <MCPServerDetail
                serverId={isCreatingServer ? null : selectedServerId}
                isNew={isCreatingServer}
                onCreated={(id) => { setSelectedServerId(id); setIsCreatingServer(false) }}
                onCancel={() => setIsCreatingServer(false)}
              />
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
