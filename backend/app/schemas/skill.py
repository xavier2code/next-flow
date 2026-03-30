"""Pydantic schemas for Skill CRUD endpoints.

Per D-34: Mirrors mcp_server.py pattern.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SkillResponse(BaseModel):
    """Response schema for a single skill."""

    id: uuid.UUID
    name: str
    description: str | None = None
    version: str
    skill_type: str
    status: str
    permissions: dict | None = None
    manifest: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillUpdate(BaseModel):
    """Update schema for skill metadata -- description only."""

    description: str | None = None


class SkillToolResponse(BaseModel):
    """Response schema for a skill's registered tools."""

    name: str
    namespaced_name: str
    description: str | None = None
    input_schema: dict | None = None
