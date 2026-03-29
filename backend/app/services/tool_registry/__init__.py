"""Tool Registry service: unified tool registration and invocation."""

from app.services.tool_registry.registry import ToolNotFoundError, ToolRegistry


def get_tool_registry() -> ToolRegistry:
    """Create a new ToolRegistry instance.

    Used as a FastAPI dependency factory or lifespan initializer.
    """
    return ToolRegistry()


__all__ = ["ToolRegistry", "ToolNotFoundError", "get_tool_registry"]
