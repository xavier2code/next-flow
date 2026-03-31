"""MCPToolHandler: bridges MCP client calls to the Tool Registry.

Per D-11: Errors as ToolMessage -- classified errors for LLM explanation.
Per D-12: Fixed timeout (30 seconds) for all MCP tool invocations.
Per D-13: Four classified error types for precise failure communication.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.services.mcp.client import MCPClient
from app.services.mcp.errors import (
    MCPToolConnectionError,
    MCPToolExecutionError,
    MCPToolTimeoutError,
)

logger = structlog.get_logger()


class MCPToolHandler:
    """ToolHandler implementation that routes to MCP client.

    Implements ToolHandler Protocol (duck typing): async def invoke(self, params: dict) -> Any.
    Each handler wraps one MCP tool on one server with timeout and classified errors.
    """

    def __init__(
        self,
        client: MCPClient,
        tool_name: str,
        timeout: float = 30.0,
    ) -> None:
        self._client = client
        self._tool_name = tool_name
        self._timeout = timeout

    async def invoke(self, params: dict) -> Any:
        """Invoke MCP tool with timeout and classified errors (D-12, D-13)."""
        try:
            result = await asyncio.wait_for(
                self._client.call_tool(self._tool_name, params),
                timeout=self._timeout,
            )
            return result
        except asyncio.TimeoutError:
            raise MCPToolTimeoutError(self._tool_name, self._timeout)
        except ConnectionError as e:
            raise MCPToolConnectionError(self._tool_name, str(e))
        except MCPToolTimeoutError:
            raise  # Re-raise classified errors
        except MCPToolConnectionError:
            raise  # Re-raise classified errors
        except Exception as e:
            raise MCPToolExecutionError(self._tool_name, str(e))
