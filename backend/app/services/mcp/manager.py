"""MCPManager: orchestrates MCP server connections, health, and tool sync.

Per D-01: Startup/shutdown lifecycle in main.py lifespan.
Per D-02: Per-server independent MCPClient instances in a dict.
Per D-03: Synchronous startup -- block until all connections complete.
Per D-04: Periodic health check via background asyncio task.
Per D-05: Exponential backoff reconnection (1s, 2s, 4s... max 60s).
Per D-07: Connect-only discovery -- tools/list on initial connection and reconnect.
Per D-08: Reconnect refresh -- unregister old tools, register new ones.
Per D-09: Namespace format mcp__{server_name}__{tool_name}.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.mcp_server import MCPServer
from app.services.mcp.client import MCPClient
from app.services.mcp.handler import MCPToolHandler
from app.services.tool_registry import ToolRegistry

logger = structlog.get_logger()


class MCPManager:
    """Manages MCP server connections, health monitoring, and tool synchronization.

    Holds a dict of MCPClient instances keyed by server name.
    Provides connect_all/disconnect_all for lifespan integration.
    Runs background health check task for connection monitoring.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        timeout: float = 30.0,
        health_check_interval: float = 60.0,
    ) -> None:
        self._registry = tool_registry
        self._session_factory = session_factory
        self._timeout = timeout
        self._health_check_interval = health_check_interval
        self.clients: dict[str, MCPClient] = {}
        self._health_task: asyncio.Task | None = None

    async def connect_all(self) -> None:
        """Connect all registered MCP servers from database (D-03).

        Uses asyncio.gather for parallel connections (per Pitfall 4 in RESEARCH.md).
        Logs errors for individual failures but does not raise.
        """
        async with self._session_factory() as db:
            result = await db.execute(select(MCPServer))
            servers = list(result.scalars().all())

        if not servers:
            logger.info("mcp_no_servers_registered")
            return

        logger.info("mcp_connecting_servers", count=len(servers))

        async def _connect_one(server: MCPServer) -> None:
            try:
                await self.connect_server(server)
            except Exception as e:
                logger.error(
                    "mcp_server_connect_failed",
                    server=server.name,
                    error=str(e),
                )

        await asyncio.gather(*[_connect_one(s) for s in servers])
        connected = sum(1 for c in self.clients.values() if c.is_connected)
        logger.info("mcp_servers_connected", total=len(servers), connected=connected)

    async def connect_server(self, server: MCPServer) -> None:
        """Connect a single MCP server: create client, connect, sync tools.

        Updates server.status in database.
        """
        client = MCPClient(
            server_url=server.url,
            server_name=server.name,
            transport_type=server.transport_type,
        )
        await client.connect()
        self.clients[server.name] = client

        # Sync tools into registry
        await self._sync_tools(server.name, client)

        # Update status in database
        await self._update_server_status(server.id, "connected")

        logger.info(
            "mcp_server_connected",
            server=server.name,
        )

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect a single server and remove its tools from registry."""
        client = self.clients.pop(server_name, None)
        if client is None:
            return

        # Unregister all tools for this server
        prefix = f"mcp__{server_name}__"
        removed = self._registry.unregister(prefix)
        logger.info("mcp_tools_unregistered", server=server_name, count=removed)

        await client.disconnect()

    async def disconnect_all(self) -> None:
        """Disconnect all servers and clear tool registrations."""
        server_names = list(self.clients.keys())
        for name in server_names:
            await self.disconnect_server(name)
        logger.info("mcp_all_servers_disconnected")

    async def _sync_tools(self, server_name: str, client: MCPClient) -> None:
        """Discover tools from server and register in ToolRegistry (D-07, D-08, D-09).

        On reconnect: unregister old tools first, then register new ones.
        """
        prefix = f"mcp__{server_name}__"
        # Unregister any existing tools for this server (handles reconnect)
        self._registry.unregister(prefix)

        try:
            tools = await client.list_tools()
        except Exception as e:
            logger.error("mcp_tool_discovery_failed", server=server_name, error=str(e))
            return

        for tool in tools:
            tool_name = f"mcp__{server_name}__{tool['name']}"
            handler = MCPToolHandler(
                client=client,
                tool_name=tool["name"],
                timeout=self._timeout,
            )
            self._registry.register(
                name=tool_name,
                schema=tool.get("inputSchema", {"type": "object"}),
                handler=handler,
            )
            logger.info("mcp_tool_registered", tool=tool_name)

    async def _update_server_status(self, server_id: Any, status: str) -> None:
        """Update MCPServer status in database."""
        try:
            async with self._session_factory() as db:
                result = await db.execute(
                    select(MCPServer).where(MCPServer.id == server_id)
                )
                server = result.scalar_one_or_none()
                if server:
                    server.status = status
                    await db.commit()
        except Exception as e:
            logger.error(
                "mcp_status_update_failed",
                server_id=str(server_id),
                status=status,
                error=str(e),
            )

    async def start_health_check(self) -> None:
        """Start the background health check task (D-04)."""
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info("mcp_health_check_started", interval=self._health_check_interval)

    async def stop_health_check(self) -> None:
        """Stop the background health check task."""
        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

    async def _health_check_loop(self) -> None:
        """Background loop: check each connected server, trigger reconnect on failure."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_servers()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("mcp_health_check_error", error=str(e))

    async def _check_all_servers(self) -> None:
        """Check health of all connected servers."""
        for server_name, client in list(self.clients.items()):
            if not client.is_connected:
                continue
            try:
                # Lightweight health check: list_tools with short timeout
                await asyncio.wait_for(client.list_tools(), timeout=5.0)
            except Exception as e:
                logger.warning(
                    "mcp_server_health_check_failed",
                    server=server_name,
                    error=str(e),
                )
                await self._handle_server_failure(server_name)

    async def _handle_server_failure(self, server_name: str) -> None:
        """Handle a server health check failure: mark disconnected, attempt reconnect."""
        # Find server in database to update status
        await self._update_server_status_by_name(server_name, "disconnected")

        # Exponential backoff reconnection (D-05)
        backoff = 1.0
        max_backoff = 60.0
        while True:
            logger.info(
                "mcp_reconnect_attempt",
                server=server_name,
                backoff=backoff,
            )
            await asyncio.sleep(backoff)
            try:
                client = self.clients.get(server_name)
                if client:
                    await client.disconnect()
                    await client.connect()
                    await self._sync_tools(server_name, client)
                    await self._update_server_status_by_name(server_name, "connected")
                    logger.info("mcp_reconnected", server=server_name)
                    return
            except Exception as e:
                logger.warning(
                    "mcp_reconnect_failed",
                    server=server_name,
                    error=str(e),
                    next_backoff=min(backoff * 2, max_backoff),
                )
                backoff = min(backoff * 2, max_backoff)

    async def _update_server_status_by_name(
        self, server_name: str, status: str
    ) -> None:
        """Update MCPServer status by server name."""
        try:
            async with self._session_factory() as db:
                result = await db.execute(
                    select(MCPServer).where(MCPServer.name == server_name)
                )
                server = result.scalar_one_or_none()
                if server:
                    server.status = status
                    await db.commit()
        except Exception as e:
            logger.error(
                "mcp_status_update_failed",
                server_name=server_name,
                status=status,
                error=str(e),
            )
