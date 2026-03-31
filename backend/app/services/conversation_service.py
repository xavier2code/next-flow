"""Conversation CRUD service with cursor-based pagination."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationUpdate


class ConversationService:
    """Business logic for conversation CRUD and message persistence."""

    @staticmethod
    async def create(
        db: AsyncSession, user_id: str, data: ConversationCreate
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, title=data.title)
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get_for_user(
        db: AsyncSession, user_id: str, conversation_id: str
    ) -> Conversation | None:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: str,
        cursor_ts=None,
        cursor_id: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Conversation], bool]:
        query = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.is_archived == False,  # noqa: E712
            )
            .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        )

        if cursor_ts is not None and cursor_id is not None:
            query = query.where(
                (Conversation.created_at, Conversation.id)
                < (cursor_ts, cursor_id)
            )

        query = query.limit(limit + 1)
        result = await db.execute(query)
        items = list(result.scalars().all())
        has_more = len(items) > limit
        return items[:limit], has_more

    @staticmethod
    async def update(
        db: AsyncSession, conversation: Conversation, data: ConversationUpdate
    ) -> Conversation:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(conversation, field, value)
        await db.flush()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete(db: AsyncSession, conversation: Conversation) -> None:
        await db.execute(
            delete(Message).where(Message.conversation_id == conversation.id)
        )
        await db.delete(conversation)
        await db.flush()

    @staticmethod
    async def archive(
        db: AsyncSession, conversation: Conversation
    ) -> Conversation:
        conversation.is_archived = True
        await db.flush()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        conversation_id: str,
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message
