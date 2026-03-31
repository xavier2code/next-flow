"""Pydantic schemas for MCP server CRUD endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MCPServerCreate(BaseModel):
    """Schema for POST /mcp-servers."""

    name: str = Field(max_length=100)
    url: str = Field(max_length=500)
    transport_type: str = Field(default="streamable_http", max_length=20)
    config: dict | None = None


class MCPServerUpdate(BaseModel):
    """Schema for PATCH /mcp-servers/{id}."""

    name: str | None = None
    url: str | None = None
    transport_type: str | None = None
    config: dict | None = None


class MCPServerResponse(BaseModel):
    """Schema for MCP server in API responses."""

    id: uuid.UUID
    name: str
    url: str
    transport_type: str
    status: str
    config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPToolResponse(BaseModel):
    """Schema for a discovered MCP tool."""

    name: str
    namespaced_name: str
    description: str | None = None
    input_schema: dict | None = None
