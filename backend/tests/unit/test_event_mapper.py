"""Unit tests for the astream_events v2 -> WebSocket event mapper."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessageChunk

from app.api.ws.event_mapper import ThinkTagFilter, map_stream_events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    event_type: str,
    name: str = "",
    data: dict | None = None,
    parent_ids: list[str] | None = None,
) -> dict:
    """Build a minimal astream_events v2 event dict."""
    return {
        "event": event_type,
        "name": name,
        "data": data or {},
        "metadata": {},
        "tags": [],
        "run_id": "test-run",
        "parent_ids": parent_ids or [],
    }


async def _stream_events(*events: dict) -> AsyncGenerator[dict, None]:
    """Yield events one by one (mimics astream_events async iterator)."""
    for e in events:
        yield e


def _mock_graph(*event_batches: list[dict]) -> AsyncMock:
    """Create a mock graph whose astream_events yields the given events."""
    graph = AsyncMock()

    async def _astream_events(input_state, config, *, version):
        for batch in event_batches:
            for event in batch:
                yield event

    graph.astream_events = _astream_events
    return graph


async def _collect(graph, user_input="hello", thread_id="t1") -> list[dict]:
    """Run map_stream_events and collect all yielded events into a list."""
    config = {"configurable": {"thread_id": thread_id}}
    return [e async for e in map_stream_events(graph, user_input, thread_id, config)]


# ---------------------------------------------------------------------------
# on_chat_model_stream -> chunk
# ---------------------------------------------------------------------------


async def test_text_chunk_mapping() -> None:
    graph = _mock_graph([
        make_event(
            "on_chat_model_stream",
            data={"chunk": AIMessageChunk(content="hello")},
        ),
    ])
    events = await _collect(graph)
    assert len(events) == 1
    assert events[0] == {
        "type": "chunk",
        "data": {"content": "hello"},
    }


# ---------------------------------------------------------------------------
# on_chat_model_stream -> tool_call (LLM requests tool)
# ---------------------------------------------------------------------------


async def test_tool_call_from_chat_model_stream() -> None:
    graph = _mock_graph([
        make_event(
            "on_chat_model_stream",
            data={
                "chunk": AIMessageChunk(
                    content="",
                    tool_calls=[
                        {
                            "name": "search",
                            "args": {"q": "test"},
                            "id": "call_123",
                        }
                    ],
                )
            },
        ),
    ])
    events = await _collect(graph)
    assert len(events) == 1
    assert events[0]["type"] == "tool_call"
    assert events[0]["data"]["name"] == "search"
    assert events[0]["data"]["args"] == {"q": "test"}
    assert events[0]["data"]["id"] == "call_123"


# ---------------------------------------------------------------------------
# on_tool_start -> tool_call
# ---------------------------------------------------------------------------


async def test_tool_call_from_on_tool_start() -> None:
    graph = _mock_graph([
        make_event(
            "on_tool_start",
            name="calculator",
            data={"input": {"expression": "2+2"}},
        ),
    ])
    events = await _collect(graph)
    assert len(events) == 1
    assert events[0] == {
        "type": "tool_call",
        "data": {"name": "calculator", "args": {"expression": "2+2"}},
    }


# ---------------------------------------------------------------------------
# on_tool_end -> tool_result
# ---------------------------------------------------------------------------


async def test_tool_result_from_on_tool_end() -> None:
    graph = _mock_graph([
        make_event(
            "on_tool_end",
            name="calculator",
            data={"output": "4"},
        ),
    ])
    events = await _collect(graph)
    assert len(events) == 1
    assert events[0] == {
        "type": "tool_result",
        "data": {"name": "calculator", "result": "4"},
    }


# ---------------------------------------------------------------------------
# on_chain_end -> done (graph-level only)
# ---------------------------------------------------------------------------


async def test_done_on_graph_end() -> None:
    graph = _mock_graph([
        make_event("on_chain_end", parent_ids=[]),
    ])
    events = await _collect(graph)
    assert len(events) == 1
    assert events[0]["type"] == "done"
    assert events[0]["data"]["thread_id"] == "t1"


async def test_ignores_nested_chain_end() -> None:
    """on_chain_end with parent_ids should NOT produce a done event."""
    graph = _mock_graph([
        make_event("on_chain_end", parent_ids=["some-node-run"]),
    ])
    events = await _collect(graph)
    assert len(events) == 0


# ---------------------------------------------------------------------------
# Custom events -> thinking
# ---------------------------------------------------------------------------


async def test_custom_event_thinking() -> None:
    graph = _mock_graph([
        make_event(
            "on_custom_event_thinking",
            data={"content": "Let me analyze the question..."},
        ),
    ])
    events = await _collect(graph)
    assert len(events) == 1
    assert events[0]["type"] == "thinking"
    assert events[0]["data"]["content"] == {"content": "Let me analyze the question..."}


# ---------------------------------------------------------------------------
# Error handling -> done with error
# ---------------------------------------------------------------------------


async def test_error_produces_done_event() -> None:
    graph = AsyncMock()

    async def _failing_stream(input_state, config, *, version):
        yield make_event(
            "on_chat_model_stream",
            data={"chunk": AIMessageChunk(content="partial")},
        )
        raise RuntimeError("LLM provider timeout")

    graph.astream_events = _failing_stream

    events = await _collect(graph)
    # First event is the chunk, second is the error-done
    assert len(events) == 2
    assert events[0]["type"] == "chunk"
    assert events[1]["type"] == "done"
    assert "LLM provider timeout" in events[1]["data"]["error"]


# ---------------------------------------------------------------------------
# Unmapped events are silently skipped
# ---------------------------------------------------------------------------


async def test_unmapped_event_skipped() -> None:
    graph = _mock_graph([
        make_event("on_retriever_start", name="vectorstore"),
    ])
    events = await _collect(graph)
    assert len(events) == 0


# ---------------------------------------------------------------------------
# ThinkTagFilter — <think...</think stripping
# ---------------------------------------------------------------------------


class TestThinkTagFilter:
    """Tests for the ThinkTagFilter state machine."""

    # -- Complete think tag in a single chunk --

    def test_complete_think_tag_stripped(self) -> None:
        f = ThinkTagFilter()
        events = f.process("<think reasoning here</thinkHello!")
        assert len(events) == 2
        assert events[0]["type"] == "thinking"
        assert events[0]["data"]["content"] == "reasoning here"
        assert events[1]["type"] == "chunk"
        assert events[1]["data"]["content"] == "Hello!"

    def test_think_tag_only(self) -> None:
        f = ThinkTagFilter()
        events = f.process("<think let me think</think")
        assert len(events) == 1
        assert events[0]["type"] == "thinking"
        assert events[0]["data"]["content"] == "let me think"

    def test_think_tag_case_insensitive(self) -> None:
        f = ThinkTagFilter()
        events = f.process("<THINK reasoning</THINK>answer")
        assert len(events) == 2
        assert events[0]["type"] == "thinking"
        assert events[1]["type"] == "chunk"
        assert events[1]["data"]["content"] == "answer"

    def test_think_tag_with_whitespace(self) -> None:
        f = ThinkTagFilter()
        events = f.process("<think > spaces </think >answer")
        assert len(events) == 2
        assert events[0]["type"] == "thinking"
        assert events[0]["data"]["content"] == "spaces"
        assert events[1]["type"] == "chunk"

    # -- Think tag split across chunks --

    def test_think_tag_split_open_tag(self) -> None:
        f = ThinkTagFilter()
        events = f.process("before<th")
        # "<th" is a partial match of "<think", held in buffer
        assert events == [{"type": "chunk", "data": {"content": "before"}}]

        events2 = f.process("ink>reasoning</think")
        assert events2[0]["type"] == "thinking"
        assert events2[0]["data"]["content"] == "reasoning"

    def test_think_tag_split_close_tag(self) -> None:
        f = ThinkTagFilter()
        events = f.process("<thinkreasoning")
        assert len(events) == 1
        assert events[0]["type"] == "thinking"
        assert events[0]["data"]["content"] == "reasoning"

        events2 = f.process("</thinkanswer")
        assert len(events2) == 1
        assert events2[0]["type"] == "chunk"
        assert events2[0]["data"]["content"] == "answer"

    # -- Think tag in the middle of content --

    def test_think_in_middle(self) -> None:
        f = ThinkTagFilter()
        events = f.process("Hello <think secret reasoning</think World!")
        assert len(events) == 3
        assert events[0]["type"] == "chunk"
        assert events[0]["data"]["content"] == "Hello "
        assert events[1]["type"] == "thinking"
        assert events[1]["data"]["content"] == "secret reasoning"
        assert events[2]["type"] == "chunk"
        assert events[2]["data"]["content"] == "World!"

    # -- No think tag (passthrough) --

    def test_no_think_tag_passthrough(self) -> None:
        f = ThinkTagFilter()
        events = f.process("Just a normal response.")
        assert len(events) == 1
        assert events[0]["type"] == "chunk"
        assert events[0]["data"]["content"] == "Just a normal response."

    # -- Flush --

    def test_flush_emits_remaining_chunk(self) -> None:
        f = ThinkTagFilter()
        events = f.process("partial")
        assert events[0]["type"] == "chunk"
        assert f.flush() == []

    def test_think_content_emitted_eagerly(self) -> None:
        f = ThinkTagFilter()
        events = f.process("<thinkunclosed thinking")
        # Partial thinking content is eagerly emitted for real-time display
        assert len(events) == 1
        assert events[0]["type"] == "thinking"
        assert events[0]["data"]["content"] == "unclosed thinking"
        # flush has nothing left since content was already emitted
        assert f.flush() == []

    def test_flush_emits_partial_buffer(self) -> None:
        f = ThinkTagFilter()
        # Partial <think at end of buffer — stream ended mid-tag
        f.process("hello<th")
        remaining = f.flush()
        assert len(remaining) == 1
        assert remaining[0]["type"] == "chunk"
        assert remaining[0]["data"]["content"] == "<th"

    # -- Integration: think tag filtered in map_stream_events --

    async def test_think_tag_filtered_in_stream(self) -> None:
        graph = _mock_graph([
            make_event(
                "on_chat_model_stream",
                data={"chunk": AIMessageChunk(content="<think hmm</thinkAnswer")},
            ),
            make_event("on_chain_end", parent_ids=[]),
        ])
        events = await _collect(graph)
        types = [e["type"] for e in events]
        assert "thinking" in types
        assert "chunk" in types
        # The chunk should NOT contain <think tags
        chunk_contents = [
            e["data"]["content"] for e in events if e["type"] == "chunk"
        ]
        assert all("<think" not in c and "</think" not in c for c in chunk_contents)
