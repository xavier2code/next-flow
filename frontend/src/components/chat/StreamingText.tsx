import MarkdownRenderer from './MarkdownRenderer'

interface StreamingTextProps {
  content: string
  isStreaming: boolean
}

export default function StreamingText({
  content,
  isStreaming,
}: StreamingTextProps) {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
        <span className="text-xs text-muted-foreground">AI</span>
      </div>
      <div className="max-w-[75%] rounded-2xl bg-card p-4 text-card-foreground">
        {content && <MarkdownRenderer content={content} />}
        {isStreaming && (
          <span className="animate-pulse text-muted-foreground">|</span>
        )}
      </div>
    </div>
  )
}
