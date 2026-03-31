"""Schema for the SSE chat endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for the SSE chat endpoint.

    Compatible with Vercel AI SDK useChat POST body.
    The `id` field is the conversation ID (path param takes precedence).
    The `messages` field is sent by useChat but the backend uses LangGraph checkpoint
    for actual conversation state -- this field is for protocol compliance only.
    """

    id: str | None = None
    messages: list[dict] | None = None  # UIMessage[] from useChat -- ignored by backend
    message: str | None = None  # Alias for content (useChat may send either)
    content: str = Field(min_length=1, max_length=10000, description="User message text")
