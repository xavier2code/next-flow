import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useSkill, useToggleSkill, useDeleteSkill, useSkillTools } from '@/hooks/use-skills'
import { useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Skill } from '@/types/api'

interface SkillDetailProps {
  skillId: string | null
}

export default function SkillDetail({ skillId }: SkillDetailProps) {
  const { data: skill, isLoading } = useSkill(skillId ?? undefined)
  const { data: tools } = useSkillTools(skillId ?? undefined)
  const toggleSkill = useToggleSkill()
  const deleteSkill = useDeleteSkill()
  const queryClient = useQueryClient()

  const [description, setDescription] = useState('')
  const [isEditingDesc, setIsEditingDesc] = useState(false)
  const [showDisableDialog, setShowDisableDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // Sync description when skill loads
  if (skill && description !== (skill.description ?? '') && !isEditingDesc) {
    setDescription(skill.description ?? '')
  }

  const handleToggle = (enable: boolean) => {
    if (!skillId) return
    if (!enable) {
      setShowDisableDialog(true)
      return
    }
    toggleSkill.mutate({ id: skillId, enable: true })
  }

  const handleConfirmDisable = () => {
    if (!skillId) return
    toggleSkill.mutate(
      { id: skillId, enable: false },
      { onSuccess: () => setShowDisableDialog(false) },
    )
  }

  const handleSaveDescription = () => {
    if (!skillId) return
    apiClient
      .patch<Skill>(`/api/v1/skills/${skillId}`, { description })
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ['skills'] })
        queryClient.invalidateQueries({ queryKey: ['skill', skillId] })
        setIsEditingDesc(false)
      })
  }

  const handleConfirmDelete = () => {
    if (!skillId) return
    deleteSkill.mutate(skillId, {
      onSuccess: () => setShowDeleteDialog(false),
    })
  }

  if (!skillId) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">选择一个技能查看详情</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (!skill) return null

  return (
    <ScrollArea className="h-full">
      <div className="p-6">
        <Card className="m-0 rounded-none border-0 shadow-none">
          <CardHeader className="px-0 pt-0">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg font-semibold">{skill.name}</CardTitle>
                <div className="mt-1 flex items-center gap-2">
                  <Badge variant="secondary">{skill.version}</Badge>
                  <Badge variant="outline">{skill.skill_type}</Badge>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="text-muted-foreground hover:text-destructive"
                onClick={() => setShowDeleteDialog(true)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="space-y-6 px-0 pb-0">
            {/* Description */}
            <div className="space-y-2">
              <Label>描述</Label>
              {isEditingDesc ? (
                <div className="space-y-2">
                  <Textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={handleSaveDescription}>
                      保存
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setIsEditingDesc(false)}>
                      取消
                    </Button>
                  </div>
                </div>
              ) : (
                <p
                  className="cursor-pointer rounded p-2 text-sm hover:bg-muted/50"
                  onClick={() => setIsEditingDesc(true)}
                >
                  {skill.description || '点击添加描述...'}
                </p>
              )}
            </div>

            <Separator />

            {/* Status toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>状态</Label>
                <p className="text-xs text-muted-foreground">
                  {skill.status === 'enabled' ? '技能已启用，工具已注册' : '技能已禁用，工具未注册'}
                </p>
              </div>
              <Switch
                checked={skill.status === 'enabled'}
                onChange={() => handleToggle(skill.status !== 'enabled')}
              />
            </div>

            <Separator />

            {/* Tools */}
            <div className="space-y-3">
              <Label>已注册工具</Label>
              {!tools || tools.length === 0 ? (
                <div className="rounded-lg border border-dashed p-4 text-center">
                  <p className="text-sm text-muted-foreground">未发现工具</p>
                  {skill.status === 'enabled' && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      技能已启用，但未发现可用工具。请检查技能包配置。
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {tools.map((tool) => (
                    <div key={tool.namespaced_name} className="rounded-lg border p-3">
                      <p className="font-mono text-sm font-medium">{tool.namespaced_name}</p>
                      {tool.description && (
                        <p className="mt-1 text-xs text-muted-foreground">{tool.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Permissions */}
            {skill.permissions && Object.keys(skill.permissions).length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <Label>权限</Label>
                  <pre className="overflow-auto rounded-lg bg-muted p-3 text-xs">
                    {JSON.stringify(skill.permissions, null, 2)}
                  </pre>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Disable confirmation */}
      <Dialog open={showDisableDialog} onOpenChange={setShowDisableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>禁用技能</DialogTitle>
            <DialogDescription>
              确定要禁用技能"{skill.name}"吗？相关工具将从注册表中移除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDisableDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmDisable}>
              禁用
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除技能</DialogTitle>
            <DialogDescription>
              确定要删除技能"{skill.name}"吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ScrollArea>
  )
}
