"""Unit tests for MCPToolHandler: invoke, timeout, classified errors."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.mcp.handler import MCPToolHandler
from app.services.mcp.errors import (
    MCPToolConnectionError,
    MCPToolError,
    MCPToolExecutionError,
    MCPToolTimeoutError,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMCPToolHandlerInvoke:
    """Tests for MCPToolHandler.invoke() success and error paths."""

    async def test_invoke_success(self):
        """Test 1: MCPToolHandler.invoke() calls client.call_tool(tool_name, params) and returns result on success."""
        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value="result_data")

        handler = MCPToolHandler(
            client=mock_client,
            tool_name="test_tool",
            timeout=30.0,
        )

        result = await handler.invoke({"arg": "value"})

        mock_client.call_tool.assert_called_once_with("test_tool", {"arg": "value"})
        assert result == "result_data"

    async def test_invoke_timeout(self):
        """Test 2: MCPToolHandler.invoke() raises MCPToolTimeoutError when asyncio.TimeoutError occurs."""
        mock_client = MagicMock()

        async def slow_call(tool_name, args):
            await asyncio.sleep(100)

        mock_client.call_tool = slow_call

        handler = MCPToolHandler(
            client=mock_client,
            tool_name="test_tool",
            timeout=0.01,
        )

        with pytest.raises(MCPToolTimeoutError) as exc_info:
            await handler.invoke({"arg": "value"})

        error = exc_info.value
        assert error.tool_name == "test_tool"
        assert "timed out" in str(error)

    async def test_invoke_connection_error(self):
        """Test 3: MCPToolHandler.invoke() raises MCPToolConnectionError when ConnectionError occurs."""
        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(side_effect=ConnectionError("refused"))

        handler = MCPToolHandler(
            client=mock_client,
            tool_name="test_tool",
            timeout=30.0,
        )

        with pytest.raises(MCPToolConnectionError) as exc_info:
            await handler.invoke({"arg": "value"})

        error = exc_info.value
        assert "unreachable" in str(error)

    async def test_invoke_generic_exception(self):
        """Test 4: MCPToolHandler.invoke() raises MCPToolExecutionError on generic Exception."""
        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(side_effect=RuntimeError("something broke"))

        handler = MCPToolHandler(
            client=mock_client,
            tool_name="test_tool",
            timeout=30.0,
        )

        with pytest.raises(MCPToolExecutionError) as exc_info:
            await handler.invoke({"arg": "value"})

        error = exc_info.value
        assert "execution error" in str(error)


class TestMCPToolErrorAttributes:
    """Tests for MCP error type attributes."""

    def test_timeout_error_attributes(self):
        """Test 5: MCPToolTimeoutError carries tool_name and timeout value."""
        error = MCPToolTimeoutError("my_tool", 30.0)
        assert error.tool_name == "my_tool"
        assert error.timeout == 30.0
        assert "timed out" in str(error)
        assert "30" in str(error)

    def test_connection_error_attributes(self):
        """Test 6: MCPToolConnectionError carries tool_name."""
        error = MCPToolConnectionError("my_tool", "Connection refused")
        assert error.tool_name == "my_tool"
        assert "unreachable" in str(error)
