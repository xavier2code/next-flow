"""Settings service for user preferences and system configuration."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.models.settings import UserSettings
from app.schemas.settings import UserSettingsUpdate


class SettingsService:
    """Business logic for user settings and system configuration."""

    @staticmethod
    async def get_or_create(db: AsyncSession, user_id: str) -> UserSettings:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        if user_settings is None:
            user_settings = UserSettings(user_id=user_id, preferences={})
            db.add(user_settings)
            await db.flush()
            await db.refresh(user_settings)
        return user_settings

    @staticmethod
    async def update_settings(
        db: AsyncSession, user_id: str, data: UserSettingsUpdate
    ) -> UserSettings:
        user_settings = await SettingsService.get_or_create(db, user_id)
        user_settings.preferences = data.preferences
        await db.flush()
        await db.refresh(user_settings)
        return user_settings

    @staticmethod
    def get_system_config() -> dict:
        return {
            "available_providers": ["openai", "ollama"],
            "default_provider": app_settings.default_provider,
            "default_model": app_settings.default_model,
        }
