"""Schema for the SSE chat endpoint."""

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    """Request body for the SSE chat endpoint.

    Compatible with Vercel AI SDK useChat POST body.
    The `id` field is the conversation ID (path param takes precedence).
    The `messages` field is sent by useChat but the backend uses LangGraph checkpoint
    for actual conversation state -- this field is for protocol compliance only.
    """

    id: str | None = None
    messages: list[dict] | None = None  # UIMessage[] from useChat
    message: str | None = None  # Alias for content (useChat may send either)
    content: str | None = Field(default=None, max_length=10000, description="User message text")

    @model_validator(mode="after")
    def extract_content(self) -> "ChatRequest":
        """Extract content from messages if content field is missing."""
        if self.content:
            return self
        # Try message field first
        if self.message:
            self.content = self.message
            return self
        # Extract from last user message in messages array
        if self.messages:
            for msg in reversed(self.messages):
                if msg.get("role") == "user":
                    parts = msg.get("parts", [])
                    for part in parts:
                        if isinstance(part, dict) and part.get("type") == "text":
                            self.content = part.get("text", "")
                            return self
        raise ValueError("No content found in request. Provide 'content', 'message', or 'messages' with a user message.")
