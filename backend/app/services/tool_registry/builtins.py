"""Built-in tools registered at application startup.

Per D-12: Minimal built-in tools to validate the full registration chain.
Per D-13: Decorator-based registration.
"""

from datetime import datetime, timezone

from app.services.tool_registry.registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register built-in tools using decorator pattern."""

    @registry.register(
        name="get_current_time",
        schema={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone string (e.g., 'US/Eastern'). Defaults to UTC.",
                },
            },
            "required": [],
        },
    )
    async def get_current_time(params: dict) -> str:
        """Get the current date and time in the specified timezone."""
        # For v1, always return UTC regardless of timezone param.
        # Timezone handling can be enhanced later.
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
