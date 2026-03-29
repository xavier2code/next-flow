from pydantic import BaseModel


class UserSettingsResponse(BaseModel):
    preferences: dict

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    preferences: dict


class SystemConfigResponse(BaseModel):
    available_providers: list[str]
    default_provider: str
    default_model: str
