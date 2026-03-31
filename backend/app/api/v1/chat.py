"""SSE chat endpoint implementing Vercel AI SDK Data Stream Protocol v2.

Replaces the REST POST + WebSocket push architecture with a single
request-scoped SSE stream.  The frontend ``useChat`` hook consumes this
endpoint directly.

Endpoint: POST /api/v1/conversations/{conversation_id}/chat
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.services.event_mapper import ThinkTagFilter
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])


async def _sse_generator(
    graph,
    conversation_id: str,
    user_id: str,
    user_message: str,
    agent_config: dict | None,
    request: Request,
) -> AsyncGenerator[str, None]:
    """Yield Data Stream Protocol v2 SSE events from LangGraph execution.

    Protocol format: each event is ``data: {JSON}\\n\\n``.
    Stream terminates with ``data: [DONE]\\n\\n``.
    """
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    text_id = f"text_{uuid.uuid4().hex[:12]}"
    reason_id = f"reason_{uuid.uuid4().hex[:12]}"

    config = {
        "configurable": {
            "thread_id": conversation_id,
            "agent_config": agent_config,
        },
    }

    think_filter = ThinkTagFilter()
    assistant_content_parts: list[str] = []
    has_text_start = False
    has_reasoning_start = False

    # -- start event --
    yield _sse_line({"type": "start", "messageId": message_id})
    yield _sse_line({"type": "start-step"})

    try:
        from langchain_core.messages import AIMessageChunk, HumanMessage

        input_state = {"messages": [HumanMessage(content=user_message)]}

        async for event in graph.astream_events(input_state, config, version="v2"):
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("client_disconnected", conversation_id=conversation_id)
                break

            event_type = event.get("event", "")

            # --- Tool calls from LLM ---
            if event_type == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if isinstance(chunk, AIMessageChunk):
                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            yield _sse_line({
                                "type": "tool-input-start",
                                "toolCallId": tc.get("id", ""),
                                "toolName": tc.get("name", ""),
                            })
                    elif chunk.content:
                        # Process through ThinkTagFilter for reasoning vs text split
                        for filtered in think_filter.process(chunk.content):
                            ftype = filtered.get("type")
                            fcontent = filtered.get("data", {}).get("content", "")
                            if not fcontent:
                                continue
                            if ftype == "thinking":
                                if not has_reasoning_start:
                                    has_reasoning_start = True
                                    yield _sse_line({
                                        "type": "reasoning-start",
                                        "id": reason_id,
                                    })
                                yield _sse_line({
                                    "type": "reasoning-delta",
                                    "id": reason_id,
                                    "delta": fcontent,
                                })
                            elif ftype == "chunk":
                                # Close reasoning part before text begins
                                if has_reasoning_start:
                                    has_reasoning_start = False
                                    yield _sse_line({
                                        "type": "reasoning-end",
                                        "id": reason_id,
                                    })
                                if not has_text_start:
                                    has_text_start = True
                                    yield _sse_line({
                                        "type": "text-start",
                                        "id": text_id,
                                    })
                                yield _sse_line({
                                    "type": "text-delta",
                                    "id": text_id,
                                    "delta": fcontent,
                                })
                                assistant_content_parts.append(fcontent)

            # --- Tool invocation start ---
            elif event_type == "on_tool_start":
                yield _sse_line({
                    "type": "tool-input-available",
                    "toolCallId": event.get("name", ""),
                    "toolName": event.get("name", ""),
                    "input": event["data"].get("input", {}),
                })

            # --- Tool invocation end ---
            elif event_type == "on_tool_end":
                output = event["data"].get("output")
                # Serialize output to string if it's not already JSON-serializable
                if output is not None and not isinstance(output, (str, int, float, bool, list, dict)):
                    output = str(output)
                yield _sse_line({
                    "type": "tool-output-available",
                    "toolCallId": event.get("name", ""),
                    "output": output,
                })

            # --- Graph-level chain end (no parent_ids = top-level completion) ---
            elif event_type == "on_chain_end":
                if not event.get("parent_ids"):
                    # Flush remaining ThinkTagFilter buffer
                    for remaining in think_filter.flush():
                        ftype = remaining.get("type")
                        fcontent = remaining.get("data", {}).get("content", "")
                        if not fcontent:
                            continue
                        if ftype == "thinking":
                            if not has_reasoning_start:
                                has_reasoning_start = True
                                yield _sse_line({
                                    "type": "reasoning-start",
                                    "id": reason_id,
                                })
                            yield _sse_line({
                                "type": "reasoning-delta",
                                "id": reason_id,
                                "delta": fcontent,
                            })
                        elif ftype == "chunk":
                            # Close reasoning part before text begins
                            if has_reasoning_start:
                                has_reasoning_start = False
                                yield _sse_line({
                                    "type": "reasoning-end",
                                    "id": reason_id,
                                })
                            if not has_text_start:
                                has_text_start = True
                                yield _sse_line({
                                    "type": "text-start",
                                    "id": text_id,
                                })
                            yield _sse_line({
                                "type": "text-delta",
                                "id": text_id,
                                "delta": fcontent,
                            })
                            assistant_content_parts.append(fcontent)

                    # Close reasoning if still active when stream ends
                    if has_reasoning_start:
                        has_reasoning_start = False
                        yield _sse_line({
                            "type": "reasoning-end",
                            "id": reason_id,
                        })

                    # Finish event
                    yield _sse_line({"type": "finish", "finishReason": "stop"})

            # --- Custom events (thinking, etc.) ---
            elif event_type.startswith("on_custom_event"):
                if not has_reasoning_start:
                    has_reasoning_start = True
                    yield _sse_line({
                        "type": "reasoning-start",
                        "id": reason_id,
                    })
                custom_data = event["data"]
                if isinstance(custom_data, str):
                    yield _sse_line({
                        "type": "reasoning-delta",
                        "id": reason_id,
                        "delta": custom_data,
                    })
                elif isinstance(custom_data, dict):
                    content = custom_data.get("content", str(custom_data))
                    yield _sse_line({
                        "type": "reasoning-delta",
                        "id": reason_id,
                        "delta": content,
                    })

    except asyncio.CancelledError:
        logger.info("stream_cancelled", conversation_id=conversation_id)
        yield _sse_line({"type": "finish", "finishReason": "cancel"})
    except Exception as exc:
        logger.error("sse_stream_error", error=str(exc), conversation_id=conversation_id)
        yield _sse_line({"type": "error", "error": str(exc)})
    finally:
        # Send [DONE] terminator
        yield "data: [DONE]\n\n"

        # Persist assistant message to DB (fire-and-forget)
        full_response = "".join(assistant_content_parts)
        if full_response:
            try:
                async with async_session_factory() as db:
                    await ConversationService.add_message(
                        db, conversation_id, role="assistant", content=full_response
                    )
                    await db.commit()
                    logger.info("assistant_message_saved", conversation_id=conversation_id)
            except Exception as db_err:
                logger.error("assistant_message_save_failed", error=str(db_err))


def _sse_line(obj: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/conversations/{conversation_id}/chat")
async def chat_sse(
    conversation_id: str,
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """SSE chat endpoint implementing Vercel AI SDK Data Stream Protocol v2.

    Accepts a user message, streams the agent's response as SSE events
    following the Data Stream Protocol v2 format, and persists the
    assistant message to the database after completion.
    """
    # Validate conversation ownership
    conversation = await ConversationService.get_for_user(
        db, str(current_user.id), conversation_id
    )
    if conversation is None:
        raise NotFoundException(message="Conversation not found")

    # Save user message to DB
    await ConversationService.add_message(
        db, conversation_id, role="user", content=body.content
    )
    await db.commit()

    # Resolve agent config from conversation's linked agent
    agent_config = None
    if conversation.agent_id:
        agent = await AgentService.get_for_user(
            db, str(current_user.id), str(conversation.agent_id)
        )
        if agent:
            agent_config = {
                "system_prompt": agent.system_prompt,
                "llm_config": agent.model_config,
            }

    return StreamingResponse(
        _sse_generator(
            graph=request.app.state.graph,
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            user_message=body.content,
            agent_config=agent_config,
            request=request,
        ),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
