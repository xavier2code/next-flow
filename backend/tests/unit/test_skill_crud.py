"""Unit tests for SkillService CRUD, SkillResponse schema, and get_skill_manager dep.

Per D-34: SkillService mirrors MCPServerService pattern with cursor pagination.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.skill import SkillResponse, SkillUpdate, SkillToolResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill_model(
    id=None,
    name="weather-query",
    description="Query weather data",
    version="1.0.0",
    skill_type="service",
    status="inactive",
    permissions=None,
    manifest=None,
    tenant_id=None,
):
    """Create a mock Skill model object with all fields."""
    skill = MagicMock()
    skill.id = id or uuid.uuid4()
    skill.name = name
    skill.description = description
    skill.version = version
    skill.skill_type = skill_type
    skill.status = status
    skill.permissions = permissions or {}
    skill.manifest = manifest or {}
    skill.tenant_id = tenant_id
    skill.created_at = datetime.now(timezone.utc)
    skill.updated_at = datetime.now(timezone.utc)
    return skill


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestSkillResponseSchema:
    """Tests for SkillResponse Pydantic schema."""

    def test_from_attributes_true(self):
        """Test 1: SkillResponse accepts a Skill model with from_attributes=True."""
        skill = _make_skill_model()
        response = SkillResponse.model_validate(skill)
        assert response.name == "weather-query"
        assert response.version == "1.0.0"
        assert response.skill_type == "service"
        assert response.status == "inactive"

    def test_optional_fields_none(self):
        """Test: SkillResponse handles None description (optional field)."""
        skill = _make_skill_model(description=None)
        response = SkillResponse.model_validate(skill)
        assert response.description is None


class TestSkillUpdateSchema:
    """Tests for SkillUpdate schema."""

    def test_only_description_set(self):
        """Test 5: SkillUpdate only modifies provided fields."""
        update = SkillUpdate(description="New description")
        dumped = update.model_dump(exclude_unset=True)
        assert "description" in dumped
        assert len(dumped) == 1

    def test_no_fields_set(self):
        """Test: SkillUpdate with no fields produces empty dict."""
        update = SkillUpdate()
        dumped = update.model_dump(exclude_unset=True)
        assert len(dumped) == 0


class TestSkillToolResponseSchema:
    """Tests for SkillToolResponse schema."""

    def test_skill_tool_response(self):
        """Test: SkillToolResponse accepts tool data."""
        tool_resp = SkillToolResponse(
            name="get_weather",
            namespaced_name="skill__weather-query__get_weather",
            description="Get weather for a city",
            input_schema={"type": "object"},
        )
        assert tool_resp.name == "get_weather"
        assert tool_resp.namespaced_name == "skill__weather-query__get_weather"


# ---------------------------------------------------------------------------
# SkillService Tests
# ---------------------------------------------------------------------------


class TestSkillServiceCreate:
    """Tests for SkillService.create."""

    @pytest.mark.asyncio
    async def test_create_inserts_and_returns_skill(self):
        """Test 2: SkillService.create inserts a Skill record and returns it."""
        from app.services.skill_service import SkillService

        db = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        skill = await SkillService.create(
            db=db,
            tenant_id=str(uuid.uuid4()),
            name="weather-query",
            version="1.0.0",
            description="Query weather data",
            skill_type="service",
            permissions={"network": True},
            package_url="weather-query/1.0.0.zip",
            manifest={"tools": [{"name": "get_weather"}]},
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        db.refresh.assert_called_once()
        assert skill.name == "weather-query"
        assert skill.status == "inactive"


class TestSkillServiceGetByName:
    """Tests for SkillService.get_by_name."""

    @pytest.mark.asyncio
    async def test_get_by_name_returns_skill(self):
        """Test 3: SkillService.get_by_name returns skill by name."""
        from app.services.skill_service import SkillService

        db = AsyncMock()
        mock_skill = _make_skill_model()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_skill
        db.execute = AsyncMock(return_value=result_mock)

        skill = await SkillService.get_by_name(db, "weather-query")
        assert skill is not None
        assert skill.name == "weather-query"

    @pytest.mark.asyncio
    async def test_get_by_name_returns_none(self):
        """Test 3b: SkillService.get_by_name returns None when not found."""
        from app.services.skill_service import SkillService

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        skill = await SkillService.get_by_name(db, "nonexistent")
        assert skill is None


class TestSkillServiceListForTenant:
    """Tests for SkillService.list_for_tenant."""

    @pytest.mark.asyncio
    async def test_list_returns_paginated_results(self):
        """Test 4: SkillService.list_for_tenant returns paginated results with has_more."""
        from app.services.skill_service import SkillService

        db = AsyncMock()
        skills = [_make_skill_model(name=f"skill-{i}") for i in range(22)]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = skills
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        items, has_more = await SkillService.list_for_tenant(db, None, limit=20)
        assert len(items) == 20
        assert has_more is True

    @pytest.mark.asyncio
    async def test_list_no_more(self):
        """Test: list_for_tenant returns has_more=False when items <= limit."""
        from app.services.skill_service import SkillService

        db = AsyncMock()
        skills = [_make_skill_model(name=f"skill-{i}") for i in range(5)]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = skills
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        items, has_more = await SkillService.list_for_tenant(db, None, limit=20)
        assert len(items) == 5
        assert has_more is False


class TestSkillServiceUpdate:
    """Tests for SkillService.update."""

    @pytest.mark.asyncio
    async def test_update_modifies_provided_fields_only(self):
        """Test 5: SkillService.update modifies only fields in SkillUpdate."""
        from app.services.skill_service import SkillService

        db = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        skill = _make_skill_model(description="Old description")
        data = SkillUpdate(description="New description")

        result = await SkillService.update(db, skill, data)
        assert skill.description == "New description"
        db.flush.assert_called_once()
        db.refresh.assert_called_once()


class TestSkillServiceDelete:
    """Tests for SkillService.delete."""

    @pytest.mark.asyncio
    async def test_delete_removes_skill(self):
        """Test 6: SkillService.delete removes the skill record."""
        from app.services.skill_service import SkillService

        db = AsyncMock()
        db.delete = AsyncMock()
        db.flush = AsyncMock()

        skill = _make_skill_model()
        await SkillService.delete(db, skill)
        db.delete.assert_called_once_with(skill)
        db.flush.assert_called_once()


class TestGetSkillManagerDep:
    """Tests for get_skill_manager dependency."""

    def test_returns_skill_manager_from_state(self):
        """Test 7: get_skill_manager returns SkillManager from app.state."""
        from app.api.deps import get_skill_manager

        mock_request = MagicMock()
        mock_manager = MagicMock()
        mock_request.app.state.skill_manager = mock_manager

        result = get_skill_manager(mock_request)
        assert result is mock_manager
