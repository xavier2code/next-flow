import uuid

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin


class Skill(TimestampMixin, TenantMixin, Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    manifest: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20), default="inactive", nullable=False
    )

    def __repr__(self) -> str:
        return f"Skill(id={self.id}, name={self.name})"
