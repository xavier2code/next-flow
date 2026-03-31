import { useNavigate } from 'react-router'
import { MessageSquare, LayoutGrid, Settings } from 'lucide-react'
import { useUiStore } from '@/stores/ui-store'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const NAV_ITEMS = [
  {
    id: 'chat' as const,
    icon: MessageSquare,
    label: '对话',
    path: '/',
  },
  {
    id: 'manage' as const,
    icon: LayoutGrid,
    label: '管理',
    path: '/manage/agents',
  },
]

const BOTTOM_ITEM = {
  id: 'settings' as const,
  icon: Settings,
  label: '设置',
  path: '/settings',
}

export default function ActivityBar() {
  const navigate = useNavigate()
  const { activeNav, setActiveNav } = useUiStore()

  const handleNavClick = (id: 'chat' | 'manage' | 'settings', path: string) => {
    setActiveNav(id)
    navigate(path)
  }

  return (
    <div className="flex h-screen w-12 flex-col items-center border-r bg-card py-2">
      {/* Top icons */}
      <div className="flex flex-1 flex-col items-center gap-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = activeNav === item.id
          return (
            <Tooltip key={item.id}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => handleNavClick(item.id, item.path)}
                  className={`flex h-10 w-10 items-center justify-center rounded-md transition-colors ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          )
        })}
      </div>

      {/* Bottom icon */}
      <div className="mt-auto">
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => handleNavClick(BOTTOM_ITEM.id, BOTTOM_ITEM.path)}
              className={`flex h-10 w-10 items-center justify-center rounded-md transition-colors ${
                activeNav === BOTTOM_ITEM.id
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <BOTTOM_ITEM.icon className="h-5 w-5" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">{BOTTOM_ITEM.label}</TooltipContent>
        </Tooltip>
      </div>
    </div>
  )
}
