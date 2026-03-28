import uuid

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin


class MCPServer(TimestampMixin, TenantMixin, Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    transport_type: Mapped[str] = mapped_column(
        String(20), default="streamable_http", nullable=False
    )
    config: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20), default="disconnected", nullable=False
    )

    def __repr__(self) -> str:
        return f"MCPServer(id={self.id}, name={self.name})"
