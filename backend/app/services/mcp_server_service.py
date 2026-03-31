"""MCP Server CRUD service with cursor-based pagination."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_server import MCPServer
from app.schemas.mcp_server import MCPServerCreate, MCPServerUpdate


class MCPServerService:
    """Business logic for MCP server CRUD."""

    @staticmethod
    async def create(
        db: AsyncSession, tenant_id: str, data: MCPServerCreate
    ) -> MCPServer:
        server = MCPServer(
            tenant_id=tenant_id,
            name=data.name,
            url=data.url,
            transport_type=data.transport_type,
            config=data.config,
            status="connecting",  # D-16: async registration
        )
        db.add(server)
        await db.flush()
        await db.refresh(server)
        return server

    @staticmethod
    async def get_for_tenant(
        db: AsyncSession, tenant_id: str | None, server_id: str
    ) -> MCPServer | None:
        query = select(MCPServer).where(MCPServer.id == server_id)
        if tenant_id is not None:
            query = query.where(MCPServer.tenant_id == tenant_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_tenant(
        db: AsyncSession,
        tenant_id: str | None,
        cursor_ts=None,
        cursor_id: str | None = None,
        limit: int = 20,
    ) -> tuple[list[MCPServer], bool]:
        query = (
            select(MCPServer)
            .order_by(MCPServer.created_at.desc(), MCPServer.id.desc())
        )
        if tenant_id is not None:
            query = query.where(MCPServer.tenant_id == tenant_id)

        if cursor_ts is not None and cursor_id is not None:
            query = query.where(
                (MCPServer.created_at, MCPServer.id) < (cursor_ts, cursor_id)
            )

        query = query.limit(limit + 1)
        result = await db.execute(query)
        items = list(result.scalars().all())
        has_more = len(items) > limit
        return items[:limit], has_more

    @staticmethod
    async def update(
        db: AsyncSession, server: MCPServer, data: MCPServerUpdate
    ) -> MCPServer:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(server, field, value)
        server.status = "connecting"  # Trigger reconnect
        await db.flush()
        await db.refresh(server)
        return server

    @staticmethod
    async def delete(db: AsyncSession, server: MCPServer) -> None:
        await db.delete(server)
        await db.flush()
