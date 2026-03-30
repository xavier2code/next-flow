"""REST endpoints for skill management.

Per D-34: Mirrors mcp_servers.py pattern with cursor pagination.
Per D-07, D-31: Hot-update on duplicate name.
"""

import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_skill_manager
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.envelope import EnvelopeResponse, PaginatedResponse, PaginationMeta, encode_cursor, decode_cursor
from app.schemas.skill import SkillResponse, SkillUpdate, SkillToolResponse
from app.services.skill_service import SkillService
from app.services.skill.validator import validate_skill_zip
from app.services.skill.storage import SkillStorage

logger = get_logger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("", status_code=201, response_model=EnvelopeResponse[SkillResponse])
async def upload_skill(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skill_manager=Depends(get_skill_manager),
):
    """Upload a skill ZIP package. Hot-updates if name already exists (per D-07, D-31)."""
    # Read ZIP bytes
    zip_bytes = await file.read()

    # Write to temp file for validation
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_bytes)
        tmp_path = tmp.name

    try:
        # Validate ZIP structure and parse SKILL.md
        validation = validate_skill_zip(tmp_path)
        metadata = validation["metadata"]
        body = validation["body"]
        skill_type = validation["skill_type"]
    finally:
        os.unlink(tmp_path)

    name = metadata["name"]
    version = metadata.get("version", "0.0.1")
    description = metadata.get("description", "")

    # Check for existing skill with same name (hot-update per D-07, D-31)
    old_skill = await SkillService.get_by_name(db, name)
    was_enabled = False
    if old_skill:
        was_enabled = old_skill.status == "enabled"
        if was_enabled:
            await skill_manager.disable_skill(old_skill.name)
        await SkillService.delete(db, old_skill)

    # Store ZIP in MinIO
    package_url = skill_manager._storage.store_package(name, version, zip_bytes)

    # Create new skill record
    skill = await SkillService.create(
        db=db,
        tenant_id=str(current_user.id),
        name=name,
        version=version,
        description=description,
        skill_type=skill_type,
        permissions=metadata.get("permissions", {}),
        package_url=package_url,
        manifest=metadata,
    )

    # Re-enable if was enabled (per D-31)
    if was_enabled:
        await skill_manager.enable_skill(skill)

    await db.commit()

    return EnvelopeResponse(data=SkillResponse.model_validate(skill))


@router.get("", response_model=PaginatedResponse[SkillResponse])
async def list_skills(
    cursor: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List skills with cursor pagination."""
    cursor_ts, cursor_id = None, None
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)

    skills, has_more = await SkillService.list_for_tenant(
        db,
        tenant_id=None,
        cursor_ts=cursor_ts,
        cursor_id=cursor_id,
        limit=limit,
    )

    next_cursor = None
    if has_more and skills:
        last = skills[-1]
        next_cursor = encode_cursor(last.created_at, str(last.id))

    return PaginatedResponse(
        data=[SkillResponse.model_validate(s) for s in skills],
        meta=PaginationMeta(cursor=next_cursor, has_more=has_more),
    )


@router.get("/{skill_id}", response_model=EnvelopeResponse[SkillResponse])
async def get_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get skill detail by ID."""
    skill = await SkillService.get_for_tenant(db, None, str(skill_id))
    if not skill:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message=f"Skill not found: {skill_id}")
    return EnvelopeResponse(data=SkillResponse.model_validate(skill))


@router.patch("/{skill_id}", response_model=EnvelopeResponse[SkillResponse])
async def update_skill(
    skill_id: uuid.UUID,
    data: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update skill metadata."""
    skill = await SkillService.get_for_tenant(db, None, str(skill_id))
    if not skill:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message=f"Skill not found: {skill_id}")

    updated = await SkillService.update(db, skill, data)
    await db.commit()
    return EnvelopeResponse(data=SkillResponse.model_validate(updated))


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skill_manager=Depends(get_skill_manager),
):
    """Delete skill: disable first, delete from MinIO, delete from DB."""
    skill = await SkillService.get_for_tenant(db, None, str(skill_id))
    if not skill:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message=f"Skill not found: {skill_id}")

    # Disable first (stop container, unregister tools)
    try:
        await skill_manager.disable_skill(skill.name)
    except Exception:
        logger.warning("skill_disable_on_delete_failed", skill=skill.name)

    # Delete from MinIO
    try:
        skill_manager._storage.delete_package(skill.name, skill.version)
    except Exception:
        logger.warning("skill_minio_delete_failed", skill=skill.name)

    # Delete from DB
    await SkillService.delete(db, skill)
    await db.commit()


@router.post("/{skill_id}/enable", response_model=EnvelopeResponse[SkillResponse])
async def enable_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skill_manager=Depends(get_skill_manager),
):
    """Enable a skill: start container, register tools."""
    skill = await SkillService.get_for_tenant(db, None, str(skill_id))
    if not skill:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message=f"Skill not found: {skill_id}")

    await skill_manager.enable_skill(skill)
    await db.commit()

    # Refresh skill to get updated status
    await db.refresh(skill)
    return EnvelopeResponse(data=SkillResponse.model_validate(skill))


@router.post("/{skill_id}/disable", response_model=EnvelopeResponse[SkillResponse])
async def disable_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skill_manager=Depends(get_skill_manager),
):
    """Disable a skill: stop container, unregister tools."""
    skill = await SkillService.get_for_tenant(db, None, str(skill_id))
    if not skill:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message=f"Skill not found: {skill_id}")

    await skill_manager.disable_skill(skill.name)
    await db.commit()

    await db.refresh(skill)
    return EnvelopeResponse(data=SkillResponse.model_validate(skill))


@router.get("/{skill_id}/tools", response_model=EnvelopeResponse[list[SkillToolResponse]])
async def list_skill_tools(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skill_manager=Depends(get_skill_manager),
):
    """List registered tools for a skill."""
    skill = await SkillService.get_for_tenant(db, None, str(skill_id))
    if not skill:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message=f"Skill not found: {skill_id}")

    prefix = f"skill__{skill.name}__"
    tools = []
    for tool in skill_manager._registry.list_tools():
        if tool["name"].startswith(prefix):
            parts = tool["name"].split("__")
            tool_name = parts[2] if len(parts) >= 3 else tool["name"]
            tools.append(
                SkillToolResponse(
                    name=tool_name,
                    namespaced_name=tool["name"],
                    description=tool.get("schema", {}).get("description"),
                    input_schema=tool.get("schema"),
                )
            )

    return EnvelopeResponse(data=tools)
