"""Unit tests for MCPManager: lifecycle, tool sync, health check, reconnection."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.services.mcp.manager import MCPManager
from app.services.mcp.client import MCPClient
from app.services.mcp.handler import MCPToolHandler
from app.services.tool_registry import ToolRegistry


def make_mock_server(
    name: str,
    url: str = "http://localhost:8080",
    transport_type: str = "streamable_http",
    server_id: uuid.UUID | None = None,
):
    """Create a mock MCPServer-like object."""
    server = MagicMock()
    server.id = server_id or uuid.uuid4()
    server.name = name
    server.url = url
    server.transport_type = transport_type
    server.config = None
    server.status = "disconnected"
    return server


def make_mock_client(
    server_name: str = "test_server",
    tools: list[dict] | None = None,
    connected: bool = True,
):
    """Create a mock MCPClient with all necessary attributes."""
    client = AsyncMock(spec=MCPClient)
    client.server_name = server_name
    client.is_connected = connected
    client._session = MagicMock() if connected else None
    client.list_tools = AsyncMock(return_value=tools or [])
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.call_tool = AsyncMock(return_value={"result": "ok"})
    return client


def make_session_factory(sessions=None):
    """Create a mock async_sessionmaker that returns sessions via async context manager.

    Args:
        sessions: list of sessions to yield on each call. If None, yields a default empty session.
    """
    if sessions is None:
        sessions = []

    _index = 0

    @asynccontextmanager
    async def factory():
        nonlocal _index
        if _index < len(sessions):
            session = sessions[_index]
            _index += 1
        else:
            session = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result_mock)
            session.commit = AsyncMock()
        yield session

    return factory


@pytest.fixture
def registry():
    """Create a fresh ToolRegistry for each test."""
    return ToolRegistry()


@pytest.fixture
def manager(registry):
    """Create an MCPManager with a default session factory."""
    session_factory = make_session_factory()
    return MCPManager(
        tool_registry=registry,
        session_factory=session_factory,
        timeout=30.0,
        health_check_interval=60.0,
    )


def _setup_mcpclient_mock(mock_clients_by_name):
    """Return a side_effect function that assigns mock client attributes to new MCPClient instances.

    Usage: patch("app.services.mcp.manager.MCPClient", side_effect=fn)
    When MCPClient(...) is called, it still creates a real MCPClient but we override
    connect/list_tools/disconnect/is_connected.
    """
    def client_factory(*args, **kwargs):
        name = kwargs.get("server_name", args[1] if len(args) > 1 else "unknown")
        mock = mock_clients_by_name.get(name)
        if mock:
            # Return the mock client directly
            return mock
        # Fallback: return a generic mock
        return make_mock_client(name)

    return client_factory


# ---- Test 1: connect_all creates clients and syncs tools ----


@pytest.mark.asyncio
async def test_connect_all_creates_clients_and_syncs_tools(registry):
    """connect_all creates MCPClient for each MCPServer record, connects them, syncs tools."""
    server_a = make_mock_server("weather", "http://weather:8080")
    server_b = make_mock_server("calendar", "http://calendar:9090")

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [server_a, server_b]
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()

    session_factory = make_session_factory(sessions=[session])
    manager = MCPManager(
        tool_registry=registry,
        session_factory=session_factory,
        timeout=30.0,
        health_check_interval=60.0,
    )

    tools_weather = [{"name": "get_forecast", "description": "Get weather", "inputSchema": {"type": "object"}}]
    tools_calendar = [{"name": "list_events", "description": "List events", "inputSchema": {"type": "object"}}]

    mock_client_a = make_mock_client("weather", tools=tools_weather)
    mock_client_b = make_mock_client("calendar", tools=tools_calendar)

    clients = {"weather": mock_client_a, "calendar": mock_client_b}
    factory = _setup_mcpclient_mock(clients)

    with patch("app.services.mcp.manager.MCPClient", side_effect=factory):
        await manager.connect_all()

    assert len(manager.clients) == 2
    assert "weather" in manager.clients
    assert "calendar" in manager.clients
    assert registry.get_tool("mcp__weather__get_forecast") is not None
    assert registry.get_tool("mcp__calendar__list_events") is not None
    mock_client_a.connect.assert_awaited_once()
    mock_client_b.connect.assert_awaited_once()


# ---- Test 2: connect_all uses asyncio.gather for parallel connections ----


@pytest.mark.asyncio
async def test_connect_all_parallel_connections(registry):
    """connect_all with asyncio.gather -- connections run in parallel."""
    server_a = make_mock_server("srv_a")
    server_b = make_mock_server("srv_b")

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [server_a, server_b]
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()

    session_factory = make_session_factory(sessions=[session])
    manager = MCPManager(
        tool_registry=registry,
        session_factory=session_factory,
        timeout=30.0,
        health_check_interval=60.0,
    )

    mock_client_a = make_mock_client("srv_a")
    mock_client_b = make_mock_client("srv_b")
    clients = {"srv_a": mock_client_a, "srv_b": mock_client_b}
    factory = _setup_mcpclient_mock(clients)

    with patch("app.services.mcp.manager.MCPClient", side_effect=factory), \
         patch("app.services.mcp.manager.asyncio.gather", wraps=asyncio.gather) as spy_gather:
        await manager.connect_all()
        spy_gather.assert_called_once()

    assert len(manager.clients) == 2


# ---- Test 3: connect_all continues on individual server failure ----


@pytest.mark.asyncio
async def test_connect_all_continues_on_failure(registry):
    """connect_all logs errors but continues on individual server failure."""
    server_good = make_mock_server("good_server")
    server_bad = make_mock_server("bad_server")

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [server_good, server_bad]
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()

    session_factory = make_session_factory(sessions=[session])
    manager = MCPManager(
        tool_registry=registry,
        session_factory=session_factory,
        timeout=30.0,
        health_check_interval=60.0,
    )

    mock_client_good = make_mock_client("good_server")

    def client_factory(*args, **kwargs):
        name = kwargs.get("server_name", "unknown")
        if name == "bad_server":
            raise ConnectionError("Connection refused")
        return mock_client_good

    with patch("app.services.mcp.manager.MCPClient", side_effect=client_factory):
        await manager.connect_all()

    assert "good_server" in manager.clients
    assert "bad_server" not in manager.clients


# ---- Test 4: disconnect_all ----


@pytest.mark.asyncio
async def test_disconnect_all(manager, registry):
    """disconnect_all disconnects all clients and clears clients dict."""
    client_a = make_mock_client("alpha")
    client_b = make_mock_client("beta")
    manager.clients = {"alpha": client_a, "beta": client_b}

    await manager.disconnect_all()

    client_a.disconnect.assert_awaited_once()
    client_b.disconnect.assert_awaited_once()
    assert len(manager.clients) == 0


# ---- Test 5: sync_tools registers namespaced ----


@pytest.mark.asyncio
async def test_sync_tools_registers_namespaced(manager, registry):
    """sync_tools registers each tool as mcp__{server}__{tool} in ToolRegistry."""
    client = make_mock_client(
        "weather",
        tools=[{"name": "get_forecast", "description": "Get weather", "inputSchema": {"type": "object"}}],
    )

    await manager._sync_tools("weather", client)

    entry = registry.get_tool("mcp__weather__get_forecast")
    assert entry is not None
    assert isinstance(entry.handler, MCPToolHandler)


# ---- Test 6: sync_tools on reconnect unregisters old first ----


@pytest.mark.asyncio
async def test_sync_tools_reconnect_unregisters_old_first(manager, registry):
    """sync_tools on reconnect unregisters old tools first, then registers new ones."""
    old_handler = AsyncMock()
    registry.register(name="mcp__weather__old_tool", schema={"type": "object"}, handler=old_handler)
    assert registry.get_tool("mcp__weather__old_tool") is not None

    client = make_mock_client(
        "weather",
        tools=[{"name": "new_tool", "description": "New tool", "inputSchema": {"type": "object"}}],
    )

    await manager._sync_tools("weather", client)

    assert registry.get_tool("mcp__weather__old_tool") is None
    assert registry.get_tool("mcp__weather__new_tool") is not None


# ---- Test 7: connect_server single ----


@pytest.mark.asyncio
async def test_connect_server_single(registry):
    """connect_server creates a single MCPClient, connects, syncs tools, updates status."""
    server = make_mock_server("weather", "http://weather:8080")

    # Session for _update_server_status
    status_session = AsyncMock()
    status_result = MagicMock()
    status_result.scalar_one_or_none.return_value = server
    status_session.execute = AsyncMock(return_value=status_result)
    status_session.commit = AsyncMock()

    session_factory = make_session_factory(sessions=[status_session])
    manager = MCPManager(
        tool_registry=registry,
        session_factory=session_factory,
        timeout=30.0,
        health_check_interval=60.0,
    )

    tools = [{"name": "get_forecast", "description": "Get weather", "inputSchema": {"type": "object"}}]
    mock_client = make_mock_client("weather", tools=tools)

    def client_factory(*args, **kwargs):
        return mock_client

    with patch("app.services.mcp.manager.MCPClient", side_effect=client_factory):
        await manager.connect_server(server)

    assert "weather" in manager.clients
    assert registry.get_tool("mcp__weather__get_forecast") is not None
    assert server.status == "connected"
    mock_client.connect.assert_awaited_once()


# ---- Test 8: disconnect_server cleans up ----


@pytest.mark.asyncio
async def test_disconnect_server_cleans_up(manager, registry):
    """disconnect_server disconnects client, unregisters tools, removes from clients dict."""
    client = make_mock_client("weather")
    manager.clients = {"weather": client}

    handler = AsyncMock()
    registry.register(name="mcp__weather__get_forecast", schema={"type": "object"}, handler=handler)
    registry.register(name="mcp__weather__get_alerts", schema={"type": "object"}, handler=handler)
    assert registry.get_tool("mcp__weather__get_forecast") is not None
    assert registry.get_tool("mcp__weather__get_alerts") is not None

    await manager.disconnect_server("weather")

    client.disconnect.assert_awaited_once()
    assert "weather" not in manager.clients
    assert registry.get_tool("mcp__weather__get_forecast") is None
    assert registry.get_tool("mcp__weather__get_alerts") is None
