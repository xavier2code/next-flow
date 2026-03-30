"""Built-in tools registered at application startup.

Per D-12: Minimal built-in tools to validate the full registration chain.
Per D-13: Decorator-based registration.
"""

import json
from datetime import datetime, timezone

from app.services.tool_registry.registry import ToolRegistry

# Module-level reference set during lifespan initialization.
_skill_manager_ref = None


def set_skill_manager(manager) -> None:
    """Set the SkillManager reference for load_skill and run_skill_script tools."""
    global _skill_manager_ref
    _skill_manager_ref = manager


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
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    @registry.register(
        name="load_skill",
        schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The skill name to load full instructions for",
                },
            },
            "required": ["name"],
        },
    )
    async def load_skill(params: dict) -> str:
        """Load full SKILL.md content for a specific skill (per D-17, D-18)."""
        skill_name = params.get("name", "")
        if not _skill_manager_ref:
            return "Skill system not available."
        content = _skill_manager_ref.get_skill_content(skill_name)
        if content is None:
            return f"Skill not found: {skill_name}"
        return content

    @registry.register(
        name="run_skill_script",
        schema={
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The script-type skill to execute",
                },
                "params": {
                    "type": "object",
                    "description": "Parameters to pass to the skill script",
                },
            },
            "required": ["skill_name"],
        },
    )
    async def run_skill_script(params: dict) -> str:
        """Execute a script-type skill on demand (per D-21)."""
        skill_name = params.get("skill_name", "")
        script_params = params.get("params", {})
        if not _skill_manager_ref:
            return "Skill system not available."
        try:
            result = _skill_manager_ref.run_script_skill(skill_name, script_params)
            return json.dumps(result)
        except Exception as e:
            return f"Script execution failed for '{skill_name}': {e}"
