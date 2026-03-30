"""Unit tests for Tool Registry: register, invoke, list_tools, decorator, builtins."""

import pytest

from app.services.tool_registry import ToolRegistry, ToolNotFoundError, get_tool_registry
from app.services.tool_registry.builtins import register_builtin_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class EchoHandler:
    """Simple async handler for testing: returns value * multiplier."""

    def __init__(self, multiplier: int = 1):
        self.multiplier = multiplier

    async def invoke(self, params: dict):
        return params.get("value", 0) * self.multiplier


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolRegistry:
    """Tests for ToolRegistry register / invoke / list_tools."""

    def test_registry_starts_empty(self):
        """Test 1: ToolRegistry starts empty, list_tools() returns []."""
        registry = ToolRegistry()
        assert registry.list_tools() == []

    def test_register_adds_tool(self):
        """Test 2: registry.register(name, schema, handler) adds tool."""
        registry = ToolRegistry()
        handler = EchoHandler()
        registry.register("echo", {"type": "object"}, handler)
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "echo"
        assert tools[0]["schema"] == {"type": "object"}

    async def test_invoke_routes_to_handler(self):
        """Test 3: registry.invoke(name, params) calls handler and returns result."""
        registry = ToolRegistry()
        handler = EchoHandler(multiplier=2)
        registry.register("echo", {"type": "object"}, handler)
        result = await registry.invoke("echo", {"value": 5})
        assert result == 10

    async def test_invoke_nonexistent_raises(self):
        """Test 4: registry.invoke('nonexistent', {}) raises ToolNotFoundError."""
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError) as exc_info:
            await registry.invoke("nonexistent", {})
        assert "nonexistent" in str(exc_info.value)

    async def test_decorator_registration(self):
        """Test 5: @registry.register(name, schema) registers decorated function."""
        registry = ToolRegistry()

        @registry.register(name="decorated", schema={"type": "object"})
        async def decorated_handler(params: dict):
            return params.get("value", 0) + 100

        result = await registry.invoke("decorated", {"value": 5})
        assert result == 105

    def test_register_builtin_tools(self):
        """Test 6: register_builtin_tools(registry) registers 'get_current_time'."""
        registry = ToolRegistry()
        register_builtin_tools(registry)
        names = [t["name"] for t in registry.list_tools()]
        assert "get_current_time" in names

    async def test_builtin_get_current_time(self):
        """Test 7: Invoking 'get_current_time' returns a string with the current time."""
        registry = ToolRegistry()
        register_builtin_tools(registry)
        result = await registry.invoke("get_current_time", {})
        assert isinstance(result, str)
        # Should contain a year pattern and UTC
        assert "UTC" in result or "20" in result

    async def test_builtin_get_current_time_with_timezone(self):
        """Test 8: get_current_time accepts optional 'timezone' param."""
        registry = ToolRegistry()
        register_builtin_tools(registry)
        result = await registry.invoke("get_current_time", {"timezone": "UTC"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_tool_registry_returns_instance(self):
        """Test 9: get_tool_registry() returns a new ToolRegistry instance."""
        registry = get_tool_registry()
        assert isinstance(registry, ToolRegistry)

    async def test_register_duplicate_overwrites(self):
        """Test 10: Registering duplicate name overwrites previous entry."""
        registry = ToolRegistry()

        handler_a = EchoHandler(multiplier=1)
        registry.register("dup", {"type": "object"}, handler_a)

        handler_b = EchoHandler(multiplier=3)
        registry.register("dup", {"type": "object"}, handler_b)

        result = await registry.invoke("dup", {"value": 4})
        # Should use handler_b (multiplier=3), not handler_a (multiplier=1)
        assert result == 12


class TestToolRegistryUnregister:
    """Tests for ToolRegistry.unregister(prefix) method."""

    def test_unregister_removes_matching_tools(self):
        """unregister('mcp__weather__') removes only tools with that prefix."""
        registry = ToolRegistry()
        handler = EchoHandler()
        registry.register("mcp__weather__get_forecast", {"type": "object"}, handler)
        registry.register("mcp__weather__get_alerts", {"type": "object"}, handler)
        registry.register("mcp__maps__directions", {"type": "object"}, handler)
        registry.register("get_current_time", {"type": "object"}, handler)

        removed = registry.unregister("mcp__weather__")
        assert removed == 2
        names = [t["name"] for t in registry.list_tools()]
        assert "mcp__weather__get_forecast" not in names
        assert "mcp__weather__get_alerts" not in names
        assert "mcp__maps__directions" in names
        assert "get_current_time" in names

    def test_unregister_returns_zero_when_no_match(self):
        """unregister with non-matching prefix returns 0, no tools removed."""
        registry = ToolRegistry()
        handler = EchoHandler()
        registry.register("get_current_time", {"type": "object"}, handler)
        removed = registry.unregister("mcp__nonexistent__")
        assert removed == 0
        assert len(registry.list_tools()) == 1

    def test_unregister_empty_registry(self):
        """unregister on empty registry returns 0."""
        registry = ToolRegistry()
        removed = registry.unregister("mcp__anything__")
        assert removed == 0
