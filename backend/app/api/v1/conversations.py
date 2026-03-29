"""Conversation REST endpoints: CRUD + archive with envelope responses."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.schemas.envelope import EnvelopeResponse, PaginatedResponse, PaginationMeta, encode_cursor, decode_cursor
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", status_code=201)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[ConversationResponse]:
    conversation = await ConversationService.create(db, str(current_user.id), data)
    await db.commit()
    return EnvelopeResponse(data=ConversationResponse.model_validate(conversation))


@router.get("")
async def list_conversations(
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[ConversationResponse]:
    cursor_ts = None
    cursor_id = None
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)

    items, has_more = await ConversationService.list_for_user(
        db, str(current_user.id), cursor_ts, cursor_id, limit
    )

    next_cursor = None
    if has_more and items:
        next_cursor = encode_cursor(items[-1].created_at, str(items[-1].id))

    return PaginatedResponse(
        data=[ConversationResponse.model_validate(c) for c in items],
        meta=PaginationMeta(cursor=next_cursor, has_more=has_more),
    )


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[ConversationResponse]:
    conversation = await ConversationService.get_for_user(
        db, str(current_user.id), conversation_id
    )
    if conversation is None:
        raise NotFoundException(message="Conversation not found")
    return EnvelopeResponse(data=ConversationResponse.model_validate(conversation))


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[ConversationResponse]:
    conversation = await ConversationService.get_for_user(
        db, str(current_user.id), conversation_id
    )
    if conversation is None:
        raise NotFoundException(message="Conversation not found")
    conversation = await ConversationService.update(db, conversation, data)
    await db.commit()
    return EnvelopeResponse(data=ConversationResponse.model_validate(conversation))


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    conversation = await ConversationService.get_for_user(
        db, str(current_user.id), conversation_id
    )
    if conversation is None:
        raise NotFoundException(message="Conversation not found")
    await ConversationService.delete(db, conversation)
    await db.commit()
    return Response(status_code=204)


@router.patch("/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[ConversationResponse]:
    conversation = await ConversationService.get_for_user(
        db, str(current_user.id), conversation_id
    )
    if conversation is None:
        raise NotFoundException(message="Conversation not found")
    conversation = await ConversationService.archive(db, conversation)
    await db.commit()
    return EnvelopeResponse(data=ConversationResponse.model_validate(conversation))
