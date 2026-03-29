"""Tool Registry: unified registration and invocation interface.

Per D-11: In-memory registry (Python dict) with Protocol-based handler pattern.
Per D-13: Decorator-based registration for built-in tools.
Per D-14: All tools globally shared across all Agents in v1.
"""

from typing import Any, Callable

import structlog

from app.services.tool_registry.handlers import ToolEntry, ToolHandler

logger = structlog.get_logger()


class ToolNotFoundError(Exception):
    """Raised when invoking a tool that is not registered."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Tool not found: {name}")


class ToolRegistry:
    """In-memory tool registry with unified register/invoke interface.

    Tools are stored in a dict keyed by name. Registration overwrites
    existing entries with the same name (last-write-wins).
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolEntry] = {}

    def register(
        self,
        name: str | None = None,
        schema: dict | None = None,
        handler: ToolHandler | None = None,
    ) -> Callable | None:
        """Register a tool, or return a decorator for registration.

        Can be called directly: registry.register("name", schema, handler)
        Or as decorator: @registry.register(name="name", schema={...})
          async def my_handler(params): ...
        """
        # Direct call with all args
        if handler is not None and name is not None and schema is not None:
            self._tools[name] = ToolEntry(name, schema, handler)
            logger.info("tool_registered", name=name)
            return None

        # Decorator usage: @registry.register(name=..., schema=...)
        if name is not None and schema is not None:
            def decorator(fn: Callable) -> Callable:
                self._tools[name] = ToolEntry(name, schema, fn)
                logger.info("tool_registered", name=name, decorator=True)
                return fn
            return decorator

        raise ValueError("register() requires name and schema (and optionally handler)")

    async def invoke(self, name: str, params: dict) -> Any:
        """Invoke a registered tool by name with the given parameters.

        Args:
            name: The registered tool name.
            params: Parameters to pass to the tool handler.

        Returns:
            The result of the tool invocation.

        Raises:
            ToolNotFoundError: If no tool is registered with the given name.
        """
        entry = self._tools.get(name)
        if not entry:
            raise ToolNotFoundError(name)
        logger.info("tool_invoking", name=name)
        handler = entry.handler
        if hasattr(handler, "invoke"):
            result = await handler.invoke(params)
        else:
            result = await handler(params)
        logger.info("tool_invoked", name=name)
        return result

    def list_tools(self) -> list[dict]:
        """Return all registered tools with name and schema."""
        return [{"name": t.name, "schema": t.schema} for t in self._tools.values()]

    def get_tool(self, name: str) -> ToolEntry | None:
        """Get a tool entry by name, or None if not found."""
        return self._tools.get(name)
