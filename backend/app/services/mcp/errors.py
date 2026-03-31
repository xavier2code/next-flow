"""Classified error hierarchy for MCP tool invocation.

Per D-13: Four error types with distinct messages for LLM explanation.
"""


class MCPToolError(Exception):
    """Base error for MCP tool invocation failures."""

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        super().__init__(message)


class MCPToolTimeoutError(MCPToolError):
    """Timeout: server too slow (D-13 type 2)."""

    def __init__(self, tool_name: str, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(
            tool_name,
            f"MCP tool '{tool_name}' timed out after {timeout}s. "
            f"The server may be overloaded or unreachable.",
        )


class MCPToolConnectionError(MCPToolError):
    """Connection failure: server unreachable (D-13 type 1)."""

    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(
            tool_name,
            f"MCP tool '{tool_name}' failed: server unreachable. {detail}",
        )


class MCPToolProtocolError(MCPToolError):
    """Protocol error: MCP SDK level error (D-13 type 3)."""

    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(
            tool_name,
            f"MCP tool '{tool_name}' protocol error: {detail}",
        )


class MCPToolExecutionError(MCPToolError):
    """Tool execution error: server returned error result (D-13 type 4)."""

    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(
            tool_name,
            f"MCP tool '{tool_name}' execution error: {detail}",
        )
