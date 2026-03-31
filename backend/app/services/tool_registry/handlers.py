"""Tool handler Protocol and entry container.

Per D-11: Protocol-based handler pattern for unified tool invocation.
"""

from typing import Any, Protocol


class ToolHandler(Protocol):
    """Protocol defining the contract for tool handlers.

    All tool handlers (built-in, MCP, skill) must implement this protocol.
    """

    async def invoke(self, params: dict) -> Any: ...


class ToolEntry:
    """Container for a registered tool: name, description, schema, and handler."""

    def __init__(self, name: str, schema: dict, handler: ToolHandler, description: str = ""):
        self.name = name
        self.description = description
        self.schema = schema
        self.handler = handler
