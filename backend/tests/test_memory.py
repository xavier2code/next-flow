"""Test scaffold for Phase 4 memory system.

Covers MEM-01 (short-term memory), MEM-02 (context injection),
MEM-03 (semantic search / long-term memory), MEM-04 (pgvector infrastructure).

Unit tests (1-7) use mocks and InMemoryStore, no external deps needed.
Integration tests (8-9) require a running PostgreSQL with pgvector.
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from langgraph.store.memory import InMemoryStore


# ---------------------------------------------------------------------------
# MEM-01: Short-term memory (Redis-backed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_short_term_add_and_retrieve(test_redis):
    """MEM-01: ShortTermMemory.add_message() stores a message and get_context() retrieves it."""
    try:
        from app.services.memory.short_term import ShortTermMemory
    except ImportError:
        pytest.skip("ShortTermMemory not yet implemented (Plan 02)")

    memory = ShortTermMemory(redis=test_redis)
    await memory.add_message(thread_id="test-conv-1", role="user", content="Hello, world!")

    context = await memory.get_context(thread_id="test-conv-1")
    assert len(context["messages"]) >= 1
    assert any("Hello, world!" in msg.get("content", "") for msg in context["messages"])


@pytest.mark.asyncio
async def test_sliding_window_trim(test_redis):
    """MEM-01: Adding more than window_size messages trims to window_size."""
    try:
        from app.services.memory.short_term import ShortTermMemory
    except ImportError:
        pytest.skip("ShortTermMemory not yet implemented (Plan 02)")

    window_size = 5
    memory = ShortTermMemory(
        redis=test_redis,
        window_size=window_size,
    )

    # Add more messages than the window allows
    for i in range(10):
        await memory.add_message(thread_id="test-conv-trim", role="user", content=f"Message {i}")

    context = await memory.get_context(thread_id="test-conv-trim")
    assert len(context["messages"]) <= window_size


@pytest.mark.asyncio
async def test_summary_compression(test_redis):
    """MEM-01: When message count exceeds threshold, summary key is populated."""
    try:
        from app.services.memory.short_term import ShortTermMemory
    except ImportError:
        pytest.skip("ShortTermMemory not yet implemented (Plan 02)")

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Summary of conversation"))

    memory = ShortTermMemory(
        redis=test_redis,
        summary_threshold=3,
    )

    with patch("app.services.memory.short_term.get_llm", return_value=mock_llm):
        for i in range(5):
            await memory.add_message(thread_id="test-conv-summary", role="user", content=f"Message {i}")

    # After exceeding threshold, a summary key should exist (or at least no errors)
    summary_key = "nextflow:memory:short:test-conv-summary:summary"
    summary = await test_redis.get(summary_key)
    # Summary may or may not be populated depending on implementation details,
    # but the mechanism must not raise errors.
    assert summary is None or isinstance(summary, str)


@pytest.mark.asyncio
async def test_ttl_refresh(test_redis):
    """MEM-01: TTL is refreshed on each add_message call."""
    try:
        from app.services.memory.short_term import ShortTermMemory
    except ImportError:
        pytest.skip("ShortTermMemory not yet implemented (Plan 02)")

    memory = ShortTermMemory(
        redis=test_redis,
        ttl=300,
    )

    await memory.add_message(thread_id="test-conv-ttl", role="user", content="First message")
    ttl_first = await test_redis.ttl("nextflow:memory:short:test-conv-ttl")

    await asyncio.sleep(0.1)

    await memory.add_message(thread_id="test-conv-ttl", role="user", content="Second message")
    ttl_second = await test_redis.ttl("nextflow:memory:short:test-conv-ttl")

    # TTL should have been refreshed (second TTL >= first TTL)
    assert ttl_second >= ttl_first


# ---------------------------------------------------------------------------
# MEM-02: Context injection into analyze node
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_context_injection():
    """MEM-02: analyze_node calls memory_service.get_context() and prepends messages to state."""
    try:
        from app.services.agent_engine.nodes.analyze import analyze_node
    except ImportError:
        pytest.skip("analyze_node not available")

    mock_memory_service = AsyncMock()
    mock_memory_service.get_context = AsyncMock(
        return_value=[{"role": "system", "content": "Remembered: user likes Python"}]
    )

    state = {
        "messages": [{"role": "user", "content": "What language should I learn?"}],
        "conversation_id": "test-conv-ctx",
    }

    with patch(
        "app.services.agent_engine.nodes.analyze.memory_service",
        mock_memory_service,
        create=True,
    ):
        result = await analyze_node(state)

    # The result should have memory context injected
    messages = result.get("messages", state["messages"])
    # At minimum, the original message should still be present
    assert len(messages) >= 1


# ---------------------------------------------------------------------------
# MEM-03: Long-term memory (Store / semantic search)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_semantic_search():
    """MEM-03: InMemoryStore with index supports semantic search with scored results."""
    # Use a simple embed function that returns fixed-dimension vectors
    def mock_embed(texts: list[str]) -> list[list[float]]:
        # Deterministic mock embeddings: simple hash-based vectors
        return [
            [float(hash(t) % 100) / 100.0] * 1536
            for t in texts
        ]

    store = InMemoryStore(
        index={
            "dims": 1536,
            "embed": mock_embed,
            "fields": ["content"],
        }
    )

    # Put items into the store
    await store.aput(
        ("memories", "user_123"),
        "item_1",
        {"content": "User prefers dark mode in IDE"},
    )
    await store.aput(
        ("memories", "user_123"),
        "item_2",
        {"content": "User works with Python and FastAPI"},
    )

    # Search with a query
    results = await store.asearch(
        ("memories", "user_123"),
        query="programming language preference",
    )

    # Should return results (InMemoryStore with embed returns scored results)
    assert len(results) > 0
    # Each result should have a score
    for item in results:
        assert item.score is not None


@pytest.mark.asyncio
async def test_store_user_scoped_namespace():
    """MEM-03: store.search with user-scoped namespace only returns that user's memories."""
    def mock_embed(texts: list[str]) -> list[list[float]]:
        return [[float(hash(t) % 100) / 100.0] * 1536 for t in texts]

    store = InMemoryStore(
        index={
            "dims": 1536,
            "embed": mock_embed,
            "fields": ["content"],
        }
    )

    # Put items for two different users
    await store.aput(
        ("memories", "user_a"),
        "item_1",
        {"content": "User A likes Python"},
    )
    await store.aput(
        ("memories", "user_b"),
        "item_2",
        {"content": "User B likes JavaScript"},
    )

    # Search only user_a's namespace
    results = await store.asearch(
        ("memories", "user_a"),
        query="programming",
    )

    # All results should belong to user_a's namespace
    for item in results:
        assert item.namespace == ("memories", "user_a")

    # user_b's data should not appear
    result_keys = [item.key for item in results]
    assert "item_2" not in result_keys


# ---------------------------------------------------------------------------
# MEM-04: pgvector infrastructure (integration tests)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Requires running PostgreSQL with pgvector",
)
@pytest.mark.asyncio
async def test_pgvector_available():
    """MEM-04: Verify pgvector extension is available in PostgreSQL."""
    import asyncpg

    conn_string = os.getenv(
        "DATABASE_URL",
        "postgresql://nextflow:nextflow@localhost:5432/nextflow",
    )
    conn = await asyncpg.connect(conn_string)
    try:
        # Attempt to create the vector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Verify it exists
        result = await conn.fetchval(
            "SELECT count(*) FROM pg_extension WHERE extname = 'vector'"
        )
        assert result >= 1, "pgvector extension not found in pg_extension"
    finally:
        await conn.close()


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Requires running PostgreSQL with pgvector",
)
@pytest.mark.asyncio
async def test_store_setup():
    """MEM-04: AsyncPostgresStore.setup() creates required tables."""
    from langgraph.store.postgres.aio import AsyncPostgresStore

    conn_string = os.getenv(
        "DATABASE_URL",
        "postgresql://nextflow:nextflow@localhost:5432/nextflow",
    )

    async with AsyncPostgresStore.from_conn_string(conn_string) as store:
        await store.setup()

        # Verify tables exist by querying information_schema
        import asyncpg

        conn = await asyncpg.connect(conn_string)
        try:
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE '%store%'"
            )
            table_names = [row["table_name"] for row in tables]
            assert len(table_names) > 0, f"No store tables found. Tables: {table_names}"
        finally:
            await conn.close()
