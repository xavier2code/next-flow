import { Button } from '@/components/ui/button'

const EXAMPLE_PROMPTS = [
  '帮我写一段Python代码',
  '解释一下什么是MCP协议',
  '帮我分析一篇文章',
]

interface WelcomeScreenProps {
  onSelectPrompt: (text: string) => void
}

export default function WelcomeScreen({ onSelectPrompt }: WelcomeScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <h2 className="text-lg font-semibold">你好！我是 NextFlow 助手</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        选择下方的示例开始对话，或直接输入你的问题。
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <Button
            key={prompt}
            variant="outline"
            size="sm"
            onClick={() => onSelectPrompt(prompt)}
          >
            {prompt}
          </Button>
        ))}
      </div>
    </div>
  )
}
