"""Settings REST endpoints: user preferences and system configuration."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.envelope import EnvelopeResponse
from app.schemas.settings import UserSettingsResponse, UserSettingsUpdate, SystemConfigResponse
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[UserSettingsResponse]:
    user_settings = await SettingsService.get_or_create(db, str(current_user.id))
    await db.commit()
    return EnvelopeResponse(data=UserSettingsResponse.model_validate(user_settings))


@router.patch("")
async def update_settings(
    data: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[UserSettingsResponse]:
    user_settings = await SettingsService.update_settings(
        db, str(current_user.id), data
    )
    await db.commit()
    return EnvelopeResponse(data=UserSettingsResponse.model_validate(user_settings))


@router.get("/system")
async def get_system_config() -> EnvelopeResponse[SystemConfigResponse]:
    config = SettingsService.get_system_config()
    return EnvelopeResponse(data=SystemConfigResponse(**config))
