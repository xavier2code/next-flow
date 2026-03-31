"""Message endpoint: POST to save user messages, GET to list messages."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.envelope import EnvelopeResponse
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["messages"])


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[list[MessageResponse]]:
    conversation = await ConversationService.get_for_user(
        db, str(current_user.id), conversation_id
    )
    if conversation is None:
        raise NotFoundException(message="Conversation not found")

    messages = await ConversationService.list_messages(db, conversation_id)
    return EnvelopeResponse(
        data=[MessageResponse.model_validate(m) for m in messages]
    )


@router.post("/conversations/{conversation_id}/messages", status_code=202)
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    conversation = await ConversationService.get_for_user(
        db, str(current_user.id), conversation_id
    )
    if conversation is None:
        raise NotFoundException(message="Conversation not found")

    await ConversationService.add_message(
        db, conversation_id, role="user", content=data.content
    )
    await db.commit()

    return Response(status_code=202)
