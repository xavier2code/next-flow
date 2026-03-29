"""Map LangGraph astream_events v2 output to typed WebSocket events.

Produces five event types consumed by the frontend:
  - thinking: agent reasoning (custom events dispatched during execution)
  - tool_call: a tool is about to be invoked (or an LLM requests one)
  - tool_result: a tool has completed execution
  - chunk: a text fragment of the LLM response
  - done: the graph execution has finished (or errored out)
"""

from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.graph.state import CompiledStateGraph

import structlog

logger = structlog.get_logger()


async def map_stream_events(
    graph: CompiledStateGraph,
    user_input: str,
    thread_id: str,
    config: dict,
) -> AsyncGenerator[dict, None]:
    """Stream LangGraph astream_events v2 events as typed WebSocket payloads.

    Args:
        graph: A compiled LangGraph StateGraph (with .astream_events).
        user_input: The user's message text.
        thread_id: Conversation thread identifier for the done event.
        config: LangGraph runnable config (must contain
                ``configurable.thread_id``).

    Yields:
        Dict with ``type`` (str) and ``data`` (dict) keys.
    """
    input_state = {"messages": [HumanMessage(content=user_input)]}

    try:
        async for event in graph.astream_events(input_state, config, version="v2"):
            event_type = event.get("event", "")

            # --- Text content streaming from the LLM ---
            if event_type == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if isinstance(chunk, AIMessageChunk):
                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            yield {
                                "type": "tool_call",
                                "data": {
                                    "name": tc.get("name", ""),
                                    "args": tc.get("args", {}),
                                    "id": tc.get("id", ""),
                                },
                            }
                    elif chunk.content:
                        yield {
                            "type": "chunk",
                            "data": {"content": chunk.content},
                        }

            # --- Tool invocation start ---
            elif event_type == "on_tool_start":
                yield {
                    "type": "tool_call",
                    "data": {
                        "name": event.get("name", ""),
                        "args": event["data"].get("input", {}),
                    },
                }

            # --- Tool invocation end ---
            elif event_type == "on_tool_end":
                yield {
                    "type": "tool_result",
                    "data": {
                        "name": event.get("name", ""),
                        "result": event["data"].get("output"),
                    },
                }

            # --- Graph-level chain end (no parent_ids = top-level) ---
            elif event_type == "on_chain_end":
                if not event.get("parent_ids"):
                    yield {
                        "type": "done",
                        "data": {"thread_id": thread_id},
                    }

            # --- Custom events (thinking, etc.) ---
            elif event_type.startswith("on_custom_event"):
                yield {
                    "type": "thinking",
                    "data": {"content": event["data"]},
                }

            else:
                logger.debug("unmapped_event", event_type=event_type)

    except Exception as exc:
        logger.error("stream_event_error", error=str(exc))
        yield {
            "type": "done",
            "data": {"error": str(exc)},
        }
