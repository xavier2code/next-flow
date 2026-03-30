"""Unit tests for SkillToolHandler HTTP invocation.

Per D-23: HTTP POST to sandbox sidecar with classified error handling.
Mirrors MCPToolHandler pattern.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.skill.errors import (
    SkillToolConnectionError,
    SkillToolExecutionError,
    SkillToolTimeoutError,
)
from app.services.skill.handler import SkillToolHandler


class TestSkillToolHandlerInvoke:
    """Test HTTP POST tool invocation."""

    @pytest.mark.asyncio
    async def test_invoke_sends_post_and_returns_json(self):
        """Per D-23: SkillToolHandler sends HTTP POST and returns JSON."""
        handler = SkillToolHandler(
            container_url="http://localhost:8080",
            tool_name="get_weather",
            timeout=30.0,
        )

        # Mock the httpx client post
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": "sunny", "temp": 72}
        mock_resp.raise_for_status = MagicMock()

        handler._client = AsyncMock()
        handler._client.post = AsyncMock(return_value=mock_resp)

        result = await handler.invoke({"city": "NYC"})

        handler._client.post.assert_called_once_with(
            "http://localhost:8080/tools/get_weather",
            json={"city": "NYC"},
        )
        assert result == {"result": "sunny", "temp": 72}

    @pytest.mark.asyncio
    async def test_invoke_raises_timeout_error(self):
        """Per D-23: Timeout raises SkillToolTimeoutError."""
        handler = SkillToolHandler(
            container_url="http://localhost:8080",
            tool_name="slow_tool",
            timeout=5.0,
        )

        handler._client = AsyncMock()
        handler._client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(SkillToolTimeoutError) as exc_info:
            await handler.invoke({"param": "value"})

        assert exc_info.value.tool_name == "slow_tool"
        assert exc_info.value.timeout == 5.0

    @pytest.mark.asyncio
    async def test_invoke_raises_connection_error(self):
        """Per D-23: Connection failure raises SkillToolConnectionError."""
        handler = SkillToolHandler(
            container_url="http://localhost:8080",
            tool_name="my_tool",
            timeout=30.0,
        )

        handler._client = AsyncMock()
        handler._client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(SkillToolConnectionError) as exc_info:
            await handler.invoke({"param": "value"})

        assert exc_info.value.tool_name == "my_tool"

    @pytest.mark.asyncio
    async def test_invoke_raises_execution_error_on_http_error(self):
        """Per D-23: Non-2xx HTTP response raises SkillToolExecutionError."""
        handler = SkillToolHandler(
            container_url="http://localhost:8080",
            tool_name="bad_tool",
            timeout=30.0,
        )

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        handler._client = AsyncMock()
        handler._client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(SkillToolExecutionError) as exc_info:
            await handler.invoke({"param": "value"})

        assert exc_info.value.tool_name == "bad_tool"

    @pytest.mark.asyncio
    async def test_invoke_raises_execution_error_on_generic_exception(self):
        """Generic exceptions also get wrapped in SkillToolExecutionError."""
        handler = SkillToolHandler(
            container_url="http://localhost:8080",
            tool_name="crash_tool",
            timeout=30.0,
        )

        handler._client = AsyncMock()
        handler._client.post = AsyncMock(
            side_effect=ValueError("unexpected error")
        )

        with pytest.raises(SkillToolExecutionError) as exc_info:
            await handler.invoke({"param": "value"})

        assert exc_info.value.tool_name == "crash_tool"


class TestSkillToolHandlerCleanup:
    """Test httpx client cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_closes_httpx_client(self):
        """Handler has a cleanup method that closes the httpx client."""
        handler = SkillToolHandler(
            container_url="http://localhost:8080",
            tool_name="get_weather",
            timeout=30.0,
        )

        handler._client = AsyncMock()
        handler._client.aclose = AsyncMock()

        await handler.cleanup()

        handler._client.aclose.assert_called_once()
