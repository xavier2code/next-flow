"""Unit tests for MCPClient: transport selection, fallback, connect/disconnect, list_tools, call_tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.mcp.client import MCPClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_streamable_http_cm(read_stream, write_stream, session_params):
    """Create a mock async context manager for streamable_http_client."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=(read_stream, write_stream, session_params))
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_sse_cm(read_stream, write_stream):
    """Create a mock async context manager for sse_client."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=(read_stream, write_stream))
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_session_cm(session_obj):
    """Create a mock async context manager for ClientSession."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_obj)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_mock_session():
    """Create a mock ClientSession with standard methods."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock()
    session.call_tool = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMCPClientConnect:
    """Tests for MCPClient connect/disconnect and transport selection."""

    @patch("app.services.mcp.client.ClientSession")
    @patch("app.services.mcp.client.sse_client")
    @patch("app.services.mcp.client.streamable_http_client")
    async def test_connect_streamable_http(
        self, mock_streamable_http, mock_sse, mock_session_cls
    ):
        """Test 1: MCPClient connects via streamable_http when transport_type='streamable_http'."""
        session = _make_mock_session()
        session_cm = _make_session_cm(session)
        mock_session_cls.return_value = session_cm

        transport_cm = _make_streamable_http_cm(
            AsyncMock(), AsyncMock(), AsyncMock()
        )
        mock_streamable_http.return_value = transport_cm

        client = MCPClient(
            server_url="http://localhost:8080/mcp",
            server_name="test_server",
            transport_type="streamable_http",
        )

        await client.connect()

        # Verify streamable_http_client was called with the URL
        mock_streamable_http.assert_called_once_with("http://localhost:8080/mcp")
        # Verify SSE was NOT attempted
        mock_sse.assert_not_called()
        # Verify session was initialized
        session.initialize.assert_called_once()
        # Verify client is connected
        assert client.is_connected is True

    @patch("app.services.mcp.client.ClientSession")
    @patch("app.services.mcp.client.sse_client")
    @patch("app.services.mcp.client.streamable_http_client")
    async def test_connect_fallback_to_sse(
        self, mock_streamable_http, mock_sse, mock_session_cls
    ):
        """Test 2: MCPClient falls back to SSE when streamable_http raises Exception."""
        # streamable_http_client raises on __aenter__
        transport_cm_fail = AsyncMock()
        transport_cm_fail.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
        transport_cm_fail.__aexit__ = AsyncMock(return_value=False)
        mock_streamable_http.return_value = transport_cm_fail

        # SSE succeeds
        session = _make_mock_session()
        session_cm = _make_session_cm(session)
        mock_session_cls.return_value = session_cm

        sse_cm = _make_sse_cm(AsyncMock(), AsyncMock())
        mock_sse.return_value = sse_cm

        client = MCPClient(
            server_url="http://localhost:8080/mcp",
            server_name="test_server",
            transport_type="streamable_http",
        )

        await client.connect()

        # Verify streamable_http was attempted first
        mock_streamable_http.assert_called_once()
        # Verify SSE was used as fallback
        mock_sse.assert_called_once_with("http://localhost:8080/mcp")
        # Verify session was initialized via SSE
        session.initialize.assert_called_once()
        assert client.is_connected is True

    @patch("app.services.mcp.client.ClientSession")
    @patch("app.services.mcp.client.sse_client")
    @patch("app.services.mcp.client.streamable_http_client")
    async def test_connect_sse_only(
        self, mock_streamable_http, mock_sse, mock_session_cls
    ):
        """Test 7: MCPClient with transport_type='sse' connects via SSE without attempting streamable_http."""
        session = _make_mock_session()
        session_cm = _make_session_cm(session)
        mock_session_cls.return_value = session_cm

        sse_cm = _make_sse_cm(AsyncMock(), AsyncMock())
        mock_sse.return_value = sse_cm

        client = MCPClient(
            server_url="http://localhost:8080/mcp",
            server_name="test_server",
            transport_type="sse",
        )

        await client.connect()

        # Verify streamable_http was NOT attempted
        mock_streamable_http.assert_not_called()
        # Verify SSE was used
        mock_sse.assert_called_once_with("http://localhost:8080/mcp")
        session.initialize.assert_called_once()
        assert client.is_connected is True


class TestMCPClientOperations:
    """Tests for MCPClient list_tools and call_tool."""

    async def test_list_tools(self):
        """Test 3: MCPClient.list_tools() calls session.list_tools() and returns list of dicts."""
        client = MCPClient(
            server_url="http://localhost:8080/mcp",
            server_name="test_server",
        )
        # Simulate a connected session
        mock_session = AsyncMock()

        tool_a = MagicMock()
        tool_a.name = "get_forecast"
        tool_a.description = "Get weather forecast"
        tool_a.inputSchema = {"type": "object", "properties": {"city": {"type": "string"}}}

        tool_b = MagicMock()
        tool_b.name = "get_alerts"
        tool_b.description = "Get weather alerts"
        tool_b.inputSchema = {"type": "object", "properties": {}}

        mock_result = MagicMock()
        mock_result.tools = [tool_a, tool_b]
        mock_session.list_tools = AsyncMock(return_value=mock_result)

        client._session = mock_session

        tools = await client.list_tools()

        assert len(tools) == 2
        assert tools[0] == {
            "name": "get_forecast",
            "description": "Get weather forecast",
            "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}},
        }
        assert tools[1] == {
            "name": "get_alerts",
            "description": "Get weather alerts",
            "inputSchema": {"type": "object", "properties": {}},
        }

    async def test_call_tool(self):
        """Test 4: MCPClient.call_tool() calls session.call_tool() with tool_name and arguments."""
        client = MCPClient(
            server_url="http://localhost:8080/mcp",
            server_name="test_server",
        )
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = "42 degrees"
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        client._session = mock_session

        result = await client.call_tool("my_tool", {"arg": "val"})

        mock_session.call_tool.assert_called_once_with("my_tool", {"arg": "val"})
        assert result is mock_result


class TestMCPClientLifecycle:
    """Tests for MCPClient disconnect and is_connected."""

    @patch("app.services.mcp.client.ClientSession")
    @patch("app.services.mcp.client.sse_client")
    @patch("app.services.mcp.client.streamable_http_client")
    async def test_disconnect(
        self, mock_streamable_http, mock_sse, mock_session_cls
    ):
        """Test 5: MCPClient.disconnect() exits both session and transport context managers and sets session to None."""
        session = _make_mock_session()
        session_cm = _make_session_cm(session)
        mock_session_cls.return_value = session_cm

        transport_cm = _make_streamable_http_cm(
            AsyncMock(), AsyncMock(), AsyncMock()
        )
        mock_streamable_http.return_value = transport_cm

        client = MCPClient(
            server_url="http://localhost:8080/mcp",
            server_name="test_server",
        )

        await client.connect()
        assert client.is_connected is True

        await client.disconnect()

        # Verify context managers were exited
        session_cm.__aexit__.assert_called_once()
        transport_cm.__aexit__.assert_called_once()
        # Verify session is None
        assert client._session is None
        assert client.is_connected is False

    def test_is_connected_false_before_connect(self):
        """Test 6: MCPClient.is_connected returns False before connect."""
        client = MCPClient(
            server_url="http://localhost:8080/mcp",
            server_name="test_server",
        )
        assert client.is_connected is False
