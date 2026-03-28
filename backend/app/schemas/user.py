import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    avatar_url: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
