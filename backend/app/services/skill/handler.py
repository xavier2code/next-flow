"""SkillToolHandler: HTTP invocation to sandbox sidecar.

Per D-23: HTTP POST to sandbox sidecar with classified error handling.
Mirrors MCPToolHandler pattern with duck-typed ToolHandler Protocol.
"""

from typing import Any

import httpx
import structlog

from app.services.skill.errors import (
    SkillToolConnectionError,
    SkillToolExecutionError,
    SkillToolTimeoutError,
)

logger = structlog.get_logger()


class SkillToolHandler:
    """ToolHandler that routes skill tool calls to sandbox via HTTP.

    Per D-23: HTTP API communication with sandbox sidecar.
    Duck-types ToolHandler Protocol: async def invoke(self, params: dict) -> Any.
    Mirrors MCPToolHandler pattern with classified errors.
    """

    def __init__(
        self, container_url: str, tool_name: str, timeout: float = 30.0
    ) -> None:
        self._url = f"{container_url}/tools/{tool_name}"
        self._tool_name = tool_name
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def invoke(self, params: dict) -> Any:
        """Invoke skill tool via HTTP POST to sandbox sidecar.

        Args:
            params: Tool parameters to send as JSON body.

        Returns:
            JSON response from the sandbox sidecar.

        Raises:
            SkillToolTimeoutError: On request timeout.
            SkillToolConnectionError: On connection failure.
            SkillToolExecutionError: On non-2xx HTTP response or other errors.
        """
        try:
            resp = await self._client.post(self._url, json=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            raise SkillToolTimeoutError(self._tool_name, self._timeout)
        except httpx.ConnectError as e:
            raise SkillToolConnectionError(self._tool_name, str(e))
        except SkillToolTimeoutError:
            raise
        except SkillToolConnectionError:
            raise
        except Exception as e:
            raise SkillToolExecutionError(self._tool_name, str(e))

    async def cleanup(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
