import base64
from datetime import datetime

from pydantic import BaseModel, Field
from typing import TypeVar, Generic

T = TypeVar("T")


class PaginationMeta(BaseModel):
    cursor: str | None = None
    has_more: bool = False


class EnvelopeResponse(BaseModel, Generic[T]):
    data: T
    meta: dict | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta


def encode_cursor(created_at: datetime, item_id: str) -> str:
    raw = f"{created_at.isoformat()}|{item_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, item_id = decoded.split("|", 1)
    return datetime.fromisoformat(ts_str), item_id
