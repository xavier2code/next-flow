import { useRef } from 'react'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useSkills, useUploadSkill } from '@/hooks/use-skills'

interface SkillListProps {
  selectedSkillId: string | null
  onSelectSkill: (id: string | null) => void
}

export default function SkillList({ selectedSkillId, onSelectSkill }: SkillListProps) {
  const { data: skills, isLoading } = useSkills()
  const uploadSkill = useUploadSkill()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadSkill.mutate(file, {
        onSuccess: () => {
          // Reset file input
          if (fileInputRef.current) {
            fileInputRef.current.value = ''
          }
        },
      })
    }
  }

  return (
    <div className="flex h-full w-1/2 flex-col border-r">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="text-base font-semibold">技能</h2>
        <Button size="sm" onClick={() => fileInputRef.current?.click()} disabled={uploadSkill.isPending}>
          <Upload className="mr-1 h-4 w-4" />
          {uploadSkill.isPending ? '上传中...' : '上传技能'}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".zip"
          className="hidden"
          onChange={handleFileSelect}
        />
      </div>

      {/* List */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full rounded-lg" />
            ))}
          </div>
        ) : !skills || skills.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <p className="text-sm text-muted-foreground">暂无技能</p>
            <p className="mt-1 text-xs text-muted-foreground">
              点击"上传技能"来添加技能包。
            </p>
          </div>
        ) : (
          <div className="space-y-2 p-4">
            {skills.map((skill) => (
              <Card
                key={skill.id}
                className={`cursor-pointer p-3 transition-colors hover:bg-muted/50 ${
                  selectedSkillId === skill.id ? 'bg-primary/10 ring-1 ring-primary/20' : ''
                }`}
                onClick={() => onSelectSkill(skill.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-base font-semibold">{skill.name}</span>
                      <Badge variant="secondary" className="text-xs">{skill.version}</Badge>
                    </div>
                    {skill.description && (
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                        {skill.description}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <Badge variant={skill.status === 'enabled' ? 'default' : 'secondary'} className="text-xs">
                      {skill.status === 'enabled' ? '已启用' : '已禁用'}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {skill.skill_type}
                    </Badge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
