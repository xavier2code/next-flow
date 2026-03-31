"""Message endpoint: POST to accept user messages and trigger agent execution."""

import asyncio

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService

logger = get_logger(__name__)

router = APIRouter(tags=["messages"])


async def _trigger_agent_execution(
    conversation_id: str, user_id: str, message: str
) -> None:
    """Placeholder for agent execution pipeline (wired in Plan 02).

    Will invoke graph.astream_events and publish events to Redis pub/sub.
    """
    logger.info(
        "trigger_agent_execution",
        extra={"conversation_id": conversation_id, "user_id": user_id},
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

    asyncio.create_task(
        _trigger_agent_execution(conversation_id, str(current_user.id), data.content)
    )

    return Response(status_code=202)
