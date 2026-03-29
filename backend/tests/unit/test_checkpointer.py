"""Tests for PostgresSaver checkpointer and graph compilation."""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.services.agent_engine.checkpointer import create_checkpointer
from app.services.agent_engine.graph import build_graph


class TestCheckpointerSetup:
    """Tests for checkpointer creation and URL handling."""

    async def test_create_checkpointer_strips_asyncpg(self):
        """Verify '+asyncpg' suffix is stripped from database URL (Pitfall 6)."""
        test_url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        with patch(
            "app.services.agent_engine.checkpointer.AsyncPostgresSaver"
        ) as mock_saver_cls:
            mock_saver = AsyncMock()
            mock_saver.setup = AsyncMock()
            mock_saver_cls.from_conn_string.return_value = mock_saver

            result = await create_checkpointer(test_url)

            mock_saver_cls.from_conn_string.assert_called_once_with(
                "postgresql://user:pass@localhost:5432/testdb"
            )
            mock_saver.setup.assert_called_once()
            assert result == mock_saver

    async def test_create_checkpointer_no_op_when_no_asyncpg(self):
        """Verify URL without '+asyncpg' is passed through unchanged."""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        with patch(
            "app.services.agent_engine.checkpointer.AsyncPostgresSaver"
        ) as mock_saver_cls:
            mock_saver = AsyncMock()
            mock_saver.setup = AsyncMock()
            mock_saver_cls.from_conn_string.return_value = mock_saver

            await create_checkpointer(test_url)

            mock_saver_cls.from_conn_string.assert_called_once_with(test_url)

    async def test_create_checkpointer_calls_setup(self):
        """Verify setup() is called to create checkpoint tables."""
        test_url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        with patch(
            "app.services.agent_engine.checkpointer.AsyncPostgresSaver"
        ) as mock_saver_cls:
            mock_saver = AsyncMock()
            mock_saver.setup = AsyncMock()
            mock_saver_cls.from_conn_string.return_value = mock_saver

            await create_checkpointer(test_url)

            mock_saver.setup.assert_awaited_once()


class TestGraphWithCheckpointer:
    """Tests for graph compilation with and without checkpointer."""

    def test_build_graph_without_checkpointer(self):
        """Graph compiles without checkpointer (for testing)."""
        graph = build_graph()
        assert graph is not None
        assert graph.checkpointer is None

    def test_build_graph_with_in_memory_checkpointer(self):
        """Graph compiles with InMemorySaver checkpointer (real but lightweight)."""
        checkpointer = InMemorySaver()
        graph = build_graph(checkpointer=checkpointer)
        assert graph is not None
        assert graph.checkpointer is checkpointer

    async def test_graph_executes_with_mock_llm(self):
        """Graph executes end-to-end without checkpointer (unit test, no real LLM)."""
        with patch("app.services.agent_engine.nodes.plan.get_llm") as mock_plan_llm, \
             patch("app.services.agent_engine.nodes.respond.get_llm") as mock_respond_llm:
            mock_plan_llm.return_value = AsyncMock()
            mock_plan_llm.return_value.ainvoke = AsyncMock(
                return_value=AIMessage(content="No tools needed.")
            )
            mock_respond_llm.return_value = AsyncMock()
            mock_respond_llm.return_value.ainvoke = AsyncMock(
                return_value=AIMessage(content="Final response.")
            )

            graph = build_graph()
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content="Hello")], "plan": "", "scratchpad": ""},
                config={"configurable": {"thread_id": "test-unit"}},
            )
            assert "messages" in result
            assert len(result["messages"]) > 0
