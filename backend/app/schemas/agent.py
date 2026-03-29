import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AgentCreate(BaseModel):
    name: str = Field(max_length=100)
    system_prompt: str | None = None
    llm_config: dict | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    llm_config: dict | None = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    system_prompt: str | None
    llm_config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def map_model_config(cls, values):
        if hasattr(values, "model_config"):
            # SQLAlchemy model instance
            raw = values.model_config
            object.__setattr__(values, "llm_config", raw)
        elif isinstance(values, dict):
            raw = values.get("model_config")
            values["llm_config"] = raw
        return values
