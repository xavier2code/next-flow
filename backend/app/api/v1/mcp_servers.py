"""MCP Server REST endpoints: CRUD with envelope responses."""

import asyncio

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_mcp_manager
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.envelope import (
    EnvelopeResponse,
    PaginatedResponse,
    PaginationMeta,
    encode_cursor,
    decode_cursor,
)
from app.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerResponse,
    MCPServerUpdate,
    MCPToolResponse,
)
from app.services.mcp.manager import MCPManager
from app.services.mcp_server_service import MCPServerService

router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])


async def _connect_and_update(mcp_manager: MCPManager, server) -> None:
    """Background task: connect server and update status."""
    try:
        await mcp_manager.connect_server(server)
    except Exception:
        pass  # Error already logged by MCPManager


async def _reconnect_server(
    mcp_manager: MCPManager, old_name: str, server
) -> None:
    """Background task: disconnect old, connect new."""
    try:
        await mcp_manager.disconnect_server(old_name)
        await mcp_manager.connect_server(server)
    except Exception:
        pass  # Error already logged


@router.post("", status_code=201)
async def register_server(
    data: MCPServerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[MCPServerResponse]:
    """Register a new MCP server (D-16: async registration)."""
    server = await MCPServerService.create(db, current_user.tenant_id, data)
    await db.commit()

    # Trigger async connection in background
    mcp_manager = get_mcp_manager(request)
    asyncio.create_task(_connect_and_update(mcp_manager, server))

    return EnvelopeResponse(data=MCPServerResponse.model_validate(server))


@router.get("")
async def list_servers(
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[MCPServerResponse]:
    """List all MCP servers for the authenticated user."""
    cursor_ts = None
    cursor_id = None
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)

    items, has_more = await MCPServerService.list_for_tenant(
        db, current_user.tenant_id, cursor_ts, cursor_id, limit
    )

    next_cursor = None
    if has_more and items:
        next_cursor = encode_cursor(items[-1].created_at, str(items[-1].id))

    return PaginatedResponse(
        data=[MCPServerResponse.model_validate(s) for s in items],
        meta=PaginationMeta(cursor=next_cursor, has_more=has_more),
    )


@router.get("/{server_id}")
async def get_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[MCPServerResponse]:
    """Get MCP server detail."""
    server = await MCPServerService.get_for_tenant(
        db, current_user.tenant_id, server_id
    )
    if server is None:
        raise NotFoundException(message="MCP server not found")
    return EnvelopeResponse(data=MCPServerResponse.model_validate(server))


@router.patch("/{server_id}")
async def update_server(
    server_id: str,
    data: MCPServerUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[MCPServerResponse]:
    """Update MCP server config. Triggers reconnect (D-14)."""
    server = await MCPServerService.get_for_tenant(
        db, current_user.tenant_id, server_id
    )
    if server is None:
        raise NotFoundException(message="MCP server not found")

    old_name = server.name
    server = await MCPServerService.update(db, server, data)
    await db.commit()

    # Disconnect old and reconnect with new config
    mcp_manager = get_mcp_manager(request)
    asyncio.create_task(_reconnect_server(mcp_manager, old_name, server))

    return EnvelopeResponse(data=MCPServerResponse.model_validate(server))


@router.delete("/{server_id}", status_code=204)
async def delete_server(
    server_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Deregister MCP server (D-17: disconnect, remove tools, delete record)."""
    server = await MCPServerService.get_for_tenant(
        db, current_user.tenant_id, server_id
    )
    if server is None:
        raise NotFoundException(message="MCP server not found")

    # Disconnect and remove tools
    mcp_manager = get_mcp_manager(request)
    await mcp_manager.disconnect_server(server.name)

    # Delete database record
    await MCPServerService.delete(db, server)
    await db.commit()
    return Response(status_code=204)


@router.get("/{server_id}/tools")
async def list_server_tools(
    server_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[list[MCPToolResponse]]:
    """List discovered tools for an MCP server."""
    server = await MCPServerService.get_for_tenant(
        db, current_user.tenant_id, server_id
    )
    if server is None:
        raise NotFoundException(message="MCP server not found")

    # Find tools in registry that belong to this server
    prefix = f"mcp__{server.name}__"
    tools = []
    for tool in request.app.state.tool_registry.list_tools():
        if tool["name"].startswith(prefix):
            tool_name = tool["name"].removeprefix(prefix)
            tools.append(
                MCPToolResponse(
                    name=tool_name,
                    namespaced_name=tool["name"],
                    description=None,
                    input_schema=tool.get("schema"),
                )
            )

    return EnvelopeResponse(data=tools)
