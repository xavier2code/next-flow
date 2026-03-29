import uuid

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"UserSettings(id={self.id}, user_id={self.user_id})"
