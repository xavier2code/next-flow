"""Message endpoint: POST to accept user messages and trigger agent execution."""

import asyncio
import json

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.ws.event_mapper import map_stream_events
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.envelope import EnvelopeResponse
from app.services.conversation_service import ConversationService

logger = get_logger(__name__)

router = APIRouter(tags=["messages"])


async def _trigger_agent_execution(
    graph,
    redis_client,
    conversation_id: str,
    user_id: str,
    message: str,
    pubsub_prefix: str,
) -> None:
    """Run the LangGraph agent pipeline and stream events via Redis pub/sub.

    Flow:
    1. Stream events from map_stream_events()
    2. Publish each event to Redis channel nextflow:ws:events:{user_id}
    3. Collect assistant response text
    4. Save assistant message to DB
    """
    channel = f"{pubsub_prefix}:{user_id}"
    config = {
        "configurable": {
            "thread_id": conversation_id,
        },
    }

    assistant_content_parts: list[str] = []

    try:
        async for event in map_stream_events(
            graph=graph,
            user_input=message,
            thread_id=conversation_id,
            config=config,
        ):
            # Publish event to Redis for WebSocket delivery
            await redis_client.publish(channel, json.dumps(event, ensure_ascii=False))

            # Collect text chunks for DB persistence
            if event.get("type") == "chunk":
                content = event.get("data", {}).get("content", "")
                if content:
                    assistant_content_parts.append(content)

        # Save assistant response to database
        full_response = "".join(assistant_content_parts)
        if full_response:
            async with async_session_factory() as db:
                try:
                    await ConversationService.add_message(
                        db, conversation_id, role="assistant", content=full_response
                    )
                    await db.commit()
                    logger.info("assistant_message_saved", conversation_id=conversation_id)
                except Exception as db_err:
                    logger.error("assistant_message_save_failed", error=str(db_err))
                    await db.rollback()

    except Exception as e:
        logger.error("agent_execution_failed", error=str(e), conversation_id=conversation_id)
        # Send error event to client
        error_event = json.dumps(
            {"type": "done", "data": {"error": str(e)}},
            ensure_ascii=False,
        )
        await redis_client.publish(channel, error_event)


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
    request: Request,
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
        _trigger_agent_execution(
            graph=request.app.state.graph,
            redis_client=request.app.state.redis,
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            message=data.content,
            pubsub_prefix=settings.redis_pubsub_prefix,
        )
    )

    return Response(status_code=202)
