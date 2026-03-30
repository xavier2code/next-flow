"""SkillService: CRUD operations for Skill model.

Mirrors MCPServerService pattern with cursor pagination.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill
from app.schemas.skill import SkillUpdate


class SkillService:
    """Static methods for Skill CRUD operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        tenant_id: str,
        name: str,
        version: str,
        description: str,
        skill_type: str,
        permissions: dict,
        package_url: str,
        manifest: dict,
    ) -> Skill:
        """Create a new Skill record."""
        skill = Skill(
            tenant_id=tenant_id,
            name=name,
            version=version,
            description=description,
            skill_type=skill_type,
            permissions=permissions,
            package_url=package_url,
            manifest=manifest,
            status="inactive",
        )
        db.add(skill)
        await db.flush()
        await db.refresh(skill)
        return skill

    @staticmethod
    async def get_for_tenant(
        db: AsyncSession,
        tenant_id: str | None,
        skill_id: str,
    ) -> Skill | None:
        """Get a skill by ID, optionally filtered by tenant."""
        query = select(Skill).where(Skill.id == skill_id)
        if tenant_id is not None:
            query = query.where(Skill.tenant_id == tenant_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Skill | None:
        """Get a skill by name (unique)."""
        result = await db.execute(select(Skill).where(Skill.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_tenant(
        db: AsyncSession,
        tenant_id: str | None,
        cursor_ts=None,
        cursor_id: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Skill], bool]:
        """List skills with cursor pagination."""
        query = select(Skill).order_by(Skill.created_at.desc(), Skill.id.desc())
        if tenant_id is not None:
            query = query.where(Skill.tenant_id == tenant_id)
        if cursor_ts is not None and cursor_id is not None:
            query = query.where(
                (Skill.created_at, Skill.id) < (cursor_ts, cursor_id)
            )
        query = query.limit(limit + 1)
        result = await db.execute(query)
        items = list(result.scalars().all())
        has_more = len(items) > limit
        return items[:limit], has_more

    @staticmethod
    async def update(db: AsyncSession, skill: Skill, data: SkillUpdate) -> Skill:
        """Update skill metadata -- only provided fields."""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(skill, field, value)
        await db.flush()
        await db.refresh(skill)
        return skill

    @staticmethod
    async def delete(db: AsyncSession, skill: Skill) -> None:
        """Delete a skill record."""
        await db.delete(skill)
        await db.flush()
