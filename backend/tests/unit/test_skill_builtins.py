"""Tests for load_skill and run_skill_script built-in tools."""

import json
import pytest

from app.services.tool_registry.builtins import (
    register_builtin_tools,
    set_skill_manager,
)
from app.services.tool_registry.registry import ToolRegistry


class MockSkillManager:
    """Mock SkillManager for builtins testing."""

    def __init__(self):
        self._content = {"weather-query": "# Weather Query\nGet weather data."}
        self._scripts = {}

    def get_skill_content(self, name: str) -> str | None:
        return self._content.get(name)

    def run_script_skill(self, skill_name: str, params: dict) -> dict:
        if skill_name not in self._scripts:
            raise RuntimeError(f"Skill not found: {skill_name}")
        return {"output": f"executed {skill_name}", "params": params}


@pytest.fixture(autouse=True)
def _reset_skill_manager():
    """Reset module-level reference between tests."""
    import app.services.tool_registry.builtins as mod

    old = mod._skill_manager_ref
    mod._skill_manager_ref = None
    yield
    mod._skill_manager_ref = old


class TestLoadSkillTool:
    """Tests for the load_skill built-in tool."""

    def test_load_skill_registered(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)
        tool = registry.get_tool("load_skill")
        assert tool is not None
        assert "name" in tool.schema.get("properties", {})
        assert "name" in tool.schema.get("required", [])

    @pytest.mark.asyncio
    async def test_load_skill_returns_content(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)
        set_skill_manager(MockSkillManager())

        tool = registry.get_tool("load_skill")
        result = await tool.handler({"name": "weather-query"})
        assert "Weather Query" in result

    @pytest.mark.asyncio
    async def test_load_skill_unknown_name(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)
        set_skill_manager(MockSkillManager())

        tool = registry.get_tool("load_skill")
        result = await tool.handler({"name": "nonexistent"})
        assert "Skill not found" in result

    @pytest.mark.asyncio
    async def test_load_skill_no_manager(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)

        tool = registry.get_tool("load_skill")
        result = await tool.handler({"name": "anything"})
        assert "not available" in result


class TestRunSkillScriptTool:
    """Tests for the run_skill_script built-in tool."""

    def test_run_skill_script_registered(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)
        tool = registry.get_tool("run_skill_script")
        assert tool is not None
        assert "skill_name" in tool.schema.get("properties", {})
        assert "skill_name" in tool.schema.get("required", [])

    @pytest.mark.asyncio
    async def test_run_skill_script_executes(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)
        mgr = MockSkillManager()
        mgr._scripts["data-processor"] = True
        set_skill_manager(mgr)

        tool = registry.get_tool("run_skill_script")
        result = await tool.handler(
            {"skill_name": "data-processor", "params": {"input": "test"}}
        )
        parsed = json.loads(result)
        assert "output" in parsed

    @pytest.mark.asyncio
    async def test_run_skill_script_not_found(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)
        mgr = MockSkillManager()
        set_skill_manager(mgr)

        tool = registry.get_tool("run_skill_script")
        result = await tool.handler({"skill_name": "nonexistent"})
        assert "failed" in result

    @pytest.mark.asyncio
    async def test_run_skill_script_no_manager(self):
        registry = ToolRegistry()
        register_builtin_tools(registry)

        tool = registry.get_tool("run_skill_script")
        result = await tool.handler({"skill_name": "anything"})
        assert "not available" in result
