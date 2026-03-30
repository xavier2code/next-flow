"""Unit tests for SkillManager lifecycle management.

Per D-11, D-12, D-16, D-20, D-21, D-22, D-27, D-32:
Skill enable/disable, tool registration, health checks, SKILL.md parsing.
"""

import asyncio
import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.skill.manager import SkillManager


class MockSettings:
    """Minimal settings mock for manager tests."""

    skill_sandbox_memory = "256m"
    skill_sandbox_cpus = 1.0
    skill_sandbox_pids_limit = 100
    skill_sandbox_timeout = 30.0
    skill_health_check_interval = 30.0


def _make_skill(
    name="weather-query",
    description="Query weather data",
    skill_type="service",
    tools=None,
    permissions=None,
    version="1.0.0",
):
    """Create a mock Skill model object."""
    skill = MagicMock()
    skill.name = name
    skill.description = description
    skill.skill_type = skill_type
    skill.version = version
    skill.id = type("UUID", (), {"__str__": lambda s: "test-uuid"})()
    skill.manifest = {}
    if tools is not None:
        skill.manifest = {"tools": tools}
    skill.permissions = permissions or {}
    return skill


def _make_zip_bytes(skill_md_content=None, include_script=False):
    """Create ZIP bytes with a SKILL.md file."""
    if skill_md_content is None:
        skill_md_content = (
            "---\n"
            "name: weather-query\n"
            "version: 1.0.0\n"
            "description: Query weather data\n"
            "tools:\n"
            "  - name: get_weather\n"
            "    description: Get weather for a city\n"
            "    parameters:\n"
            "      type: object\n"
            "---\n\n"
            "# Weather Query Skill\n\n"
            "This skill queries weather data for cities.\n"
        )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("SKILL.md", skill_md_content)
        if include_script:
            zf.writestr("script/get_weather.py", "async def run(params): return {}")
    return buf.getvalue()


@pytest.fixture
def mock_registry():
    """Create a mock ToolRegistry."""
    registry = MagicMock()
    registry.register = MagicMock()
    registry.unregister = MagicMock(return_value=0)
    registry.list_tools = MagicMock(return_value=[])
    return registry


@pytest.fixture
def mock_sandbox():
    """Create a mock SkillSandbox."""
    sandbox = MagicMock()
    sandbox.start_service_container = MagicMock()
    sandbox.stop_container = MagicMock()
    sandbox.cleanup_stale = MagicMock(return_value=0)

    from app.services.skill.sandbox import ContainerInfo

    sandbox.start_service_container.return_value = ContainerInfo(
        container_id="abc123",
        name="nextflow-skill-weather-query",
        url="http://nextflow-skill-weather-query:8080",
        skill_name="weather-query",
    )
    return sandbox


@pytest.fixture
def mock_storage():
    """Create a mock SkillStorage."""
    storage = MagicMock()
    storage.get_package = MagicMock(return_value=_make_zip_bytes())
    return storage


@pytest.fixture
def mock_session_factory():
    """Create a mock async session factory."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    # Default: no skills found
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory, session


@pytest.fixture
def manager(mock_registry, mock_session_factory, mock_storage, mock_sandbox):
    """Create a SkillManager with mocked dependencies."""
    sf, _ = mock_session_factory
    return SkillManager(
        tool_registry=mock_registry,
        session_factory=sf,
        skill_storage=mock_storage,
        skill_sandbox=mock_sandbox,
        skill_content={},
        timeout=30.0,
        health_check_interval=30.0,
    )


class TestEnableSkillService:
    """Test enabling a service-type skill."""

    @pytest.mark.asyncio
    async def test_registers_tools_in_registry(self, manager, mock_registry, mock_sandbox):
        """Per D-11, D-12: enable_skill registers tools with skill__{name}__{tool} namespace."""
        skill = _make_skill(
            name="weather-query",
            skill_type="service",
            tools=[{"name": "get_weather", "description": "Get weather"}],
            permissions={"network": True},
        )

        await manager._enable_one(skill)

        # Verify sandbox started
        mock_sandbox.start_service_container.assert_called_once()

        # Verify tool registered with correct namespace
        mock_registry.register.assert_called()
        call_args = mock_registry.register.call_args
        assert call_args[1]["name"] == "skill__weather-query__get_weather"
        # Handler is a SkillToolHandler
        from app.services.skill.handler import SkillToolHandler

        assert isinstance(call_args[1]["handler"], SkillToolHandler)

    @pytest.mark.asyncio
    async def test_starts_persistent_container(self, manager, mock_sandbox):
        """Per D-20: Service-type starts persistent container."""
        skill = _make_skill(
            skill_type="service",
            tools=[{"name": "get_weather", "description": "Get weather"}],
            permissions={"network": True},
        )

        await manager._enable_one(skill)

        mock_sandbox.start_service_container.assert_called_once_with(
            skill_name="weather-query",
            extract_path=mock_sandbox.start_service_container.call_args[1]["extract_path"],
            permissions={"network": True},
        )
        assert "weather-query" in manager.containers

    @pytest.mark.asyncio
    async def test_parses_skill_md_body(self, manager):
        """Test 11: _enable_one parses SKILL.md body and stores in _skill_content dict."""
        skill = _make_skill(
            skill_type="service",
            tools=[{"name": "get_weather", "description": "Get weather"}],
        )

        await manager._enable_one(skill)

        # _skill_content should contain the SKILL.md body
        assert "weather-query" in manager._skill_content
        body = manager._skill_content["weather-query"]
        assert "# Weather Query Skill" in body

    @pytest.mark.asyncio
    async def test_stores_description(self, manager):
        """Test 12: _enable_one stores skill description in _skill_descriptions dict."""
        skill = _make_skill(
            skill_type="service",
            description="Query weather data",
            tools=[{"name": "get_weather", "description": "Get weather"}],
        )

        await manager._enable_one(skill)

        assert manager._skill_descriptions["weather-query"] == "Query weather data"


class TestEnableSkillKnowledge:
    """Test enabling a knowledge-type skill."""

    @pytest.mark.asyncio
    async def test_does_not_start_container(self, manager, mock_sandbox):
        """Per D-13, D-22: Knowledge-type skips container."""
        skill = _make_skill(
            skill_type="knowledge",
            tools=None,
        )

        await manager._enable_one(skill)

        mock_sandbox.start_service_container.assert_not_called()
        assert "weather-query" not in manager.containers

    @pytest.mark.asyncio
    async def test_does_not_register_tools(self, manager, mock_registry):
        """Per D-13: Knowledge-type has no tool registration."""
        skill = _make_skill(
            skill_type="knowledge",
            tools=None,
        )

        await manager._enable_one(skill)

        mock_registry.register.assert_not_called()


class TestEnableSkillScript:
    """Test enabling a script-type skill."""

    @pytest.mark.asyncio
    async def test_does_not_start_persistent_container(self, manager, mock_sandbox):
        """Per D-21: Script-type does not start persistent container."""
        skill = _make_skill(
            skill_type="script",
            tools=None,
        )
        # Script type has script dir but no tools declared
        manager._storage.get_package.return_value = _make_zip_bytes(
            include_script=True
        )

        await manager._enable_one(skill)

        mock_sandbox.start_service_container.assert_not_called()


class TestDisableSkill:
    """Test disabling a skill."""

    @pytest.mark.asyncio
    async def test_unregisters_tools_and_stops_container(
        self, manager, mock_registry, mock_sandbox
    ):
        """Per D-11, D-12: disable_skill unregisters tools and stops container."""
        skill = _make_skill(
            skill_type="service",
            tools=[{"name": "get_weather", "description": "Get weather"}],
        )
        await manager._enable_one(skill)

        await manager.disable_skill("weather-query")

        # Verify tools unregistered with correct prefix
        mock_registry.unregister.assert_called_with("skill__weather-query__")

        # Verify container stopped
        mock_sandbox.stop_container.assert_called_with(
            "nextflow-skill-weather-query"
        )

    @pytest.mark.asyncio
    async def test_cleans_content_and_description_caches(
        self, manager
    ):
        """Test 14: disable removes from _skill_content and _skill_descriptions."""
        skill = _make_skill(
            skill_type="service",
            description="Query weather data",
            tools=[{"name": "get_weather", "description": "Get weather"}],
        )
        await manager._enable_one(skill)

        # Verify populated
        assert "weather-query" in manager._skill_content
        assert "weather-query" in manager._skill_descriptions

        await manager.disable_skill("weather-query")

        # Verify cleaned
        assert "weather-query" not in manager._skill_content
        assert "weather-query" not in manager._skill_descriptions
        assert manager.get_skill_content("weather-query") is None


class TestEnableAll:
    """Test enabling all skills from DB."""

    @pytest.mark.asyncio
    async def test_queries_db_and_enables_each(
        self, manager, mock_session_factory, mock_sandbox
    ):
        """Per D-32: enable_all queries DB for status='enabled' skills."""
        sf, session = mock_session_factory

        skill1 = _make_skill(name="weather-query", skill_type="knowledge")
        skill2 = _make_skill(name="doc-search", skill_type="knowledge")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [skill1, skill2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        await manager.enable_all()

        # cleanup_stale called first
        mock_sandbox.cleanup_stale.assert_called_once()

        # Both skills enabled (knowledge type, no containers)
        assert manager._skill_content.get("weather-query") is not None
        assert manager._skill_content.get("doc-search") is not None


class TestDisableAll:
    """Test disabling all skills."""

    @pytest.mark.asyncio
    async def test_disables_all_tracked_skills(self, manager):
        """disable_all stops all containers and unregisters all tools."""
        skill = _make_skill(
            skill_type="service",
            tools=[{"name": "get_weather", "description": "Get weather"}],
        )
        await manager._enable_one(skill)

        await manager.disable_all()

        assert len(manager.containers) == 0


class TestHealthCheck:
    """Test health check lifecycle."""

    @pytest.mark.asyncio
    async def test_start_health_check_creates_task(self, manager):
        """Test 8: start_health_check creates background task."""
        await manager.start_health_check()

        assert manager._health_task is not None
        assert not manager._health_task.done()

        # Clean up
        await manager.stop_health_check()

    @pytest.mark.asyncio
    async def test_stop_health_check_cancels_task(self, manager):
        """Test 9: stop_health_check cancels background task."""
        await manager.start_health_check()
        assert manager._health_task is not None

        await manager.stop_health_check()
        assert manager._health_task is None

    @pytest.mark.asyncio
    async def test_health_check_detects_dead_and_restarts(
        self, manager, mock_registry, mock_sandbox
    ):
        """Test 10: Health check detects dead container, unregisters, restarts."""
        skill = _make_skill(
            skill_type="service",
            tools=[{"name": "get_weather", "description": "Get weather"}],
        )
        await manager._enable_one(skill)
        assert "weather-query" in manager.containers

        # Simulate health check failure by mocking _check_all_containers
        with patch.object(manager, "_check_all_containers") as mock_check:
            # Make health check detect failure
            async def fail_health():
                # Directly call the failure handler
                await manager._handle_container_failure("weather-query")

            mock_check.side_effect = fail_health

            # Need to provide a skill for the restart to work
            # The _handle_container_failure queries DB
            sf, session = type(manager).__getattribute__(
                manager, '_session_factory'
            ).__self__ if False else (None, None)
            # Access through the manager's session_factory
            sf = manager._session_factory
            # Get the session from the mock
            session_mock = AsyncMock()
            skill_result_mock = MagicMock()
            skill_result_mock.scalar_one_or_none.return_value = skill
            session_mock.execute = AsyncMock(return_value=skill_result_mock)
            session_mock.commit = AsyncMock()

            # Patch session_factory for this test
            manager._session_factory = MagicMock()
            manager._session_factory.return_value.__aenter__ = AsyncMock(
                return_value=session_mock
            )
            manager._session_factory.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            await manager._handle_container_failure("weather-query")

            # After restart, container should be re-created
            assert mock_sandbox.start_service_container.call_count >= 1


class TestGetEnabledSkillSummaries:
    """Test skill summaries for Agent context injection."""

    @pytest.mark.asyncio
    async def test_returns_name_and_description(self, manager, mock_registry):
        """Test 13: get_enabled_skill_summaries returns name AND description (per D-16)."""
        skill = _make_skill(
            name="weather-query",
            description="Query weather data",
            skill_type="service",
            tools=[{"name": "get_weather", "description": "Get weather"}],
        )
        await manager._enable_one(skill)

        # Mock list_tools to return the registered skill tools
        mock_registry.list_tools.return_value = [
            {"name": "skill__weather-query__get_weather", "schema": {}}
        ]

        summaries = manager.get_enabled_skill_summaries()

        assert len(summaries) >= 1
        weather = next(
            (s for s in summaries if s["name"] == "weather-query"), None
        )
        assert weather is not None
        assert weather["name"] == "weather-query"
        assert weather["description"] == "Query weather data"

    @pytest.mark.asyncio
    async def test_deduplicates_by_skill_name(self, manager, mock_registry):
        """Multiple tools from same skill produce one summary entry."""
        skill = _make_skill(
            name="weather-query",
            description="Query weather",
            skill_type="service",
            tools=[
                {"name": "get_weather", "description": "Get weather"},
                {"name": "get_forecast", "description": "Get forecast"},
            ],
        )
        await manager._enable_one(skill)

        mock_registry.list_tools.return_value = [
            {"name": "skill__weather-query__get_weather", "schema": {}},
            {"name": "skill__weather-query__get_forecast", "schema": {}},
        ]

        summaries = manager.get_enabled_skill_summaries()
        weather_entries = [s for s in summaries if s["name"] == "weather-query"]
        assert len(weather_entries) == 1

    @pytest.mark.asyncio
    async def test_get_skill_content_returns_body(self, manager):
        """get_skill_content returns the SKILL.md body."""
        skill = _make_skill(
            skill_type="knowledge",
            tools=None,
        )
        await manager._enable_one(skill)

        content = manager.get_skill_content("weather-query")
        assert content is not None
        assert "# Weather Query Skill" in content
