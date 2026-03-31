import type { UIMessage } from '@ai-sdk/react'
import { Bot, Sparkles } from 'lucide-react'
import MarkdownRenderer from './MarkdownRenderer'

interface ChatMessageProps {
  message: UIMessage
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  // For user messages, display content directly
  // For assistant messages, useChat handles streaming -- just render content
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? 'bg-primary/10' : 'bg-muted'
        }`}
      >
        {isUser ? (
          <Bot className="h-4 w-4 text-primary" />
        ) : (
          <Sparkles className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[75%] rounded-2xl p-4 ${
          isUser
            ? 'bg-primary/10 text-primary-foreground'
            : 'bg-card text-card-foreground'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <MarkdownRenderer content={message.content} />
        )}
      </div>
    </div>
  )
}
