"""MCP Client: wraps MCP SDK ClientSession for a single external MCP server.

Per D-02: Per-server independent MCPClient instances.
Per D-06: Transport auto-fallback -- prefer Streamable HTTP, fallback to legacy SSE.
"""

from __future__ import annotations

from typing import Any

import structlog
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.client.sse import sse_client

logger = structlog.get_logger()


class MCPClient:
    """Wraps MCP SDK ClientSession for a single external MCP server.

    Each MCPClient owns one ClientSession connected to one server.
    Handles connection establishment, transport selection, tool discovery, and invocation.
    """

    def __init__(
        self,
        server_url: str,
        server_name: str,
        transport_type: str = "streamable_http",
    ) -> None:
        self.server_url = server_url
        self.server_name = server_name
        self.transport_type = transport_type
        self._session: ClientSession | None = None
        self._session_ctx: Any | None = None
        self._transport_ctx: Any | None = None

    async def connect(self) -> None:
        """Establish connection with transport auto-fallback (D-06).

        If transport_type is "streamable_http", tries Streamable HTTP first,
        falls back to SSE on connection failure.
        If transport_type is "sse", connects directly via SSE.
        """
        if self.transport_type == "streamable_http":
            try:
                await self._connect_streamable_http()
                logger.info(
                    "mcp_client_connected",
                    server=self.server_name,
                    transport="streamable_http",
                )
                return
            except Exception as e:
                logger.warning(
                    "mcp_streamable_http_failed",
                    server=self.server_name,
                    error=str(e),
                    fallback="sse",
                )
                await self._connect_sse()
                logger.info(
                    "mcp_client_connected",
                    server=self.server_name,
                    transport="sse_fallback",
                )
        else:
            await self._connect_sse()
            logger.info(
                "mcp_client_connected",
                server=self.server_name,
                transport="sse",
            )

    async def _connect_streamable_http(self) -> None:
        """Connect via Streamable HTTP transport."""
        self._transport_ctx = streamable_http_client(self.server_url)
        read_stream, write_stream, _session_id = await self._transport_ctx.__aenter__()
        self._session_ctx = ClientSession(read_stream, write_stream)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()

    async def _connect_sse(self) -> None:
        """Connect via legacy SSE transport."""
        self._transport_ctx = sse_client(self.server_url)
        read_stream, write_stream, _session_id = await self._transport_ctx.__aenter__()
        self._session_ctx = ClientSession(read_stream, write_stream)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()

    async def list_tools(self) -> list[dict]:
        """Call tools/list on the connected server.

        Returns list of dicts with keys: name, description, inputSchema.
        """
        if self._session is None:
            raise RuntimeError("Not connected")
        result = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in result.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a specific tool on this server."""
        if self._session is None:
            raise RuntimeError("Not connected")
        result = await self._session.call_tool(tool_name, arguments)
        return result

    async def disconnect(self) -> None:
        """Clean up session and transport context managers."""
        if self._session_ctx is not None:
            try:
                await self._session_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("mcp_session_cleanup_error", server=self.server_name, error=str(e))
        if self._transport_ctx is not None:
            try:
                await self._transport_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("mcp_transport_cleanup_error", server=self.server_name, error=str(e))
        self._session = None
        self._session_ctx = None
        self._transport_ctx = None

    @property
    def is_connected(self) -> bool:
        """Return True if session is active."""
        return self._session is not None
