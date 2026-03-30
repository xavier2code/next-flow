"""Tests for skill tool registration/unregistration in ToolRegistry."""

import pytest

from app.services.tool_registry.registry import ToolRegistry


@pytest.fixture
def registry():
    return ToolRegistry()


class MockHandler:
    """Simple async handler for testing."""

    async def __call__(self, params: dict) -> str:
        return f"result: {params}"


class TestSkillToolRegistration:
    """Tests for registering skill tools with skill__ prefix."""

    def test_register_skill_tool(self, registry):
        handler = MockHandler()
        registry.register(
            name="skill__weather-query__get_weather",
            schema={"type": "object"},
            handler=handler,
        )
        tool = registry.get_tool("skill__weather-query__get_weather")
        assert tool is not None
        assert tool.name == "skill__weather-query__get_weather"

    @pytest.mark.asyncio
    async def test_invoke_skill_tool(self, registry):
        handler = MockHandler()
        registry.register(
            name="skill__weather-query__get_weather",
            schema={"type": "object"},
            handler=handler,
        )
        result = await registry.invoke(
            "skill__weather-query__get_weather", {"city": "Beijing"}
        )
        assert "Beijing" in result

    def test_unregister_skill_tools_by_prefix(self, registry):
        handler = MockHandler()
        registry.register(
            name="skill__weather-query__get_weather",
            schema={"type": "object"},
            handler=handler,
        )
        registry.register(
            name="skill__weather-query__get_forecast",
            schema={"type": "object"},
            handler=handler,
        )
        # Also register a non-skill tool
        registry.register(
            name="mcp__server__tool",
            schema={"type": "object"},
            handler=handler,
        )

        removed = registry.unregister("skill__weather-query__")
        assert removed == 2
        assert registry.get_tool("skill__weather-query__get_weather") is None
        assert registry.get_tool("skill__weather-query__get_forecast") is None
        # Non-skill tool should remain
        assert registry.get_tool("mcp__server__tool") is not None

    def test_unregister_multiple_skills_independently(self, registry):
        handler = MockHandler()
        registry.register(
            name="skill__weather__get",
            schema={"type": "object"},
            handler=handler,
        )
        registry.register(
            name="skill__stocks__get",
            schema={"type": "object"},
            handler=handler,
        )

        # Unregister only weather
        removed = registry.unregister("skill__weather__")
        assert removed == 1
        assert registry.get_tool("skill__weather__get") is None
        assert registry.get_tool("skill__stocks__get") is not None

    def test_bulk_unregister_all_skill_prefix(self, registry):
        handler = MockHandler()
        for i in range(5):
            registry.register(
                name=f"skill__svc__tool_{i}",
                schema={"type": "object"},
                handler=handler,
            )

        removed = registry.unregister("skill__svc__")
        assert removed == 5
        assert len(registry.list_tools()) == 0
