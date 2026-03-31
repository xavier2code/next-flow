"""Map LangGraph astream_events v2 output to typed WebSocket events.

Produces five event types consumed by the frontend:
  - thinking: agent reasoning (custom events dispatched during execution)
  - tool_call: a tool is about to be invoked (or an LLM requests one)
  - tool_result: a tool has completed execution
  - chunk: a text fragment of the LLM response
  - done: the graph execution has finished (or errored out)
"""

import re
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.graph.state import CompiledStateGraph

import structlog

logger = structlog.get_logger()


class ThinkTagFilter:
    """Stateful filter that strips <think...</think tags from LLM output.

    Converts think-tag content into ``thinking`` events instead of ``chunk``
    events, so the frontend SidePanel can display reasoning while the message
    bubble stays clean.

    Handles streaming scenarios where ``<think`` / ``</think`` may be split
    across multiple chunks (e.g. ``<`` then ``think>``).
    """

    _OPEN_RE = re.compile(r"<think[\s>]*", re.IGNORECASE)
    _CLOSE_RE = re.compile(r"</think[\s>]*", re.IGNORECASE)

    def __init__(self) -> None:
        self._buffer = ""
        self._in_think = False

    def process(self, text: str) -> list[dict]:
        """Process a text chunk, returning zero or more events."""
        events: list[dict] = []
        self._buffer += text

        while self._buffer:
            if self._in_think:
                close_match = self._CLOSE_RE.search(self._buffer)
                if close_match:
                    thinking_content = self._buffer[:close_match.start()]
                    self._buffer = self._buffer[close_match.end():]
                    self._in_think = False
                    if thinking_content.strip():
                        events.append(
                            {
                                "type": "thinking",
                                "data": {"content": thinking_content.strip()},
                            }
                        )
                else:
                    # Still inside think tag — emit partial thinking for
                    # real-time side-panel display.
                    events.append(
                        {
                            "type": "thinking",
                            "data": {"content": self._buffer},
                        }
                    )
                    self._buffer = ""
                    break
            else:
                open_match = self._OPEN_RE.search(self._buffer)
                if open_match:
                    before = self._buffer[:open_match.start()]
                    if before:
                        events.append(
                            {"type": "chunk", "data": {"content": before}}
                        )
                    self._buffer = self._buffer[open_match.end():]
                    self._in_think = True
                else:
                    # No complete think tag — check for partial ``<think`` at
                    # the end of the buffer (streaming split).
                    partial = self._find_partial_open(self._buffer)
                    if partial is not None:
                        before = self._buffer[:partial]
                        if before:
                            events.append(
                                {"type": "chunk", "data": {"content": before}}
                            )
                        self._buffer = self._buffer[partial:]
                        break  # wait for more data
                    else:
                        events.append(
                            {"type": "chunk", "data": {"content": self._buffer}}
                        )
                        self._buffer = ""

        return events

    # ------------------------------------------------------------------

    def _find_partial_open(self, text: str) -> int | None:
        """Return the start index of a partial ``<think`` prefix at *text*'s tail, or ``None``."""
        lower = text.lower()
        for i in range(1, len("<think") + 1):
            if lower.endswith("<think"[:i]):
                return len(text) - i
        return None

    def flush(self) -> list[dict]:
        """Flush remaining buffered content.  Call when the stream ends."""
        events: list[dict] = []
        if self._buffer:
            if self._in_think:
                events.append(
                    {
                        "type": "thinking",
                        "data": {"content": self._buffer.strip()},
                    }
                )
            else:
                events.append(
                    {"type": "chunk", "data": {"content": self._buffer}}
                )
            self._buffer = ""
        return events


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
    think_filter = ThinkTagFilter()

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
                        for filtered in think_filter.process(chunk.content):
                            yield filtered

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
    finally:
        for remaining in think_filter.flush():
            yield remaining
