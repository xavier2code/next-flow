import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New Conversation", max_length=255)
    agent_id: uuid.UUID | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    agent_id: uuid.UUID | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    agent_id: uuid.UUID | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
