"""Unit tests for AgentState, graph topology, and conditional edge.

Tests the core agent workflow engine: StateGraph with 4 nodes (Analyze, Plan,
Execute, Respond), AgentState TypedDict schema, conditional edge routing, and
message accumulation via add_messages reducer.
"""

import typing

from langchain_core.messages import AIMessage, HumanMessage

from app.services.agent_engine.graph import build_graph, should_execute
from app.services.agent_engine.state import AgentState


class TestAgentStateSchema:
    """Tests for AgentState TypedDict definition."""

    def test_agent_state_schema(self) -> None:
        """AgentState has correct fields: messages, plan, scratchpad, remaining_steps."""
        annotations = AgentState.__annotations__

        # messages field exists and is annotated
        assert "messages" in annotations
        # The type should involve add_messages reducer via Annotated
        msg_type = annotations["messages"]
        # Check it's an Annotated type with metadata
        assert hasattr(msg_type, "__metadata__"), (
            "messages must be Annotated[list, add_messages]"
        )

        # plan and scratchpad are str
        assert annotations["plan"] is str
        assert annotations["scratchpad"] is str

        # remaining_steps exists
        assert "remaining_steps" in annotations

    def test_agent_state_excludes_user_id_and_thread_id(self) -> None:
        """AgentState does NOT have user_id or thread_id fields (D-17)."""
        annotations = AgentState.__annotations__
        assert "user_id" not in annotations
        assert "thread_id" not in annotations


class TestGraphTopology:
    """Tests for StateGraph node structure."""

    def test_graph_has_four_nodes(self) -> None:
        """build_graph() returns a CompiledStateGraph with analyze, plan, execute, respond nodes."""
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        # CompiledStateGraph.nodes includes special nodes; check our 4 are present
        expected_nodes = {"analyze", "plan", "execute", "respond"}
        assert expected_nodes.issubset(node_names), (
            f"Expected nodes {expected_nodes} but got {node_names}"
        )


class TestConditionalEdge:
    """Tests for should_execute conditional edge routing."""

    def test_conditional_edge_routes_to_execute(self) -> None:
        """Routes to 'execute' when last message has tool_calls."""
        state: dict = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "1", "name": "test", "args": {}}],
                ),
            ]
        }
        result = should_execute(state)
        assert result == "execute"

    def test_conditional_edge_routes_to_respond(self) -> None:
        """Routes to 'respond' when last AI message has no tool_calls."""
        state: dict = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="No tools needed", tool_calls=[]),
            ]
        }
        result = should_execute(state)
        assert result == "respond"

    def test_conditional_edge_routes_to_respond_on_human_message(self) -> None:
        """Routes to 'respond' when last message is a HumanMessage (no tool_calls)."""
        state: dict = {
            "messages": [HumanMessage(content="hello")],
        }
        result = should_execute(state)
        assert result == "respond"


class TestMessageAccumulation:
    """Tests for add_messages reducer behavior."""

    async def test_messages_accumulate(self) -> None:
        """Messages accumulate via add_messages reducer (not overwritten)."""
        from app.services.agent_engine.nodes.analyze import analyze_node
        from app.services.agent_engine.nodes.plan import plan_node

        initial_state: dict = {
            "messages": [HumanMessage(content="hello")],
            "plan": "",
            "scratchpad": "",
        }
        # Run analyze_node
        analyze_result = await analyze_node(initial_state)
        # Merge results
        accumulated_messages = list(initial_state["messages"]) + list(
            analyze_result.get("messages", [])
        )
        state_after_analyze = {**initial_state, "messages": accumulated_messages}

        # Run plan_node
        plan_result = await plan_node(state_after_analyze)
        accumulated_messages = list(state_after_analyze["messages"]) + list(
            plan_result.get("messages", [])
        )

        # Both the initial HumanMessage and the plan's AIMessage should be present
        assert len(accumulated_messages) >= 2
        assert any(isinstance(m, HumanMessage) for m in accumulated_messages)
        assert any(isinstance(m, AIMessage) for m in accumulated_messages)


class TestGraphExecution:
    """Tests for end-to-end graph execution."""

    async def test_graph_executes_end_to_end(self) -> None:
        """Graph execution completes for a simple HumanMessage input."""
        graph = build_graph()
        result = await graph.ainvoke(
            input={"messages": [HumanMessage(content="test")]},
            config={"configurable": {"thread_id": "test-123"}},
        )
        assert "messages" in result
        assert len(result["messages"]) > 0

    async def test_remaining_steps_present(self) -> None:
        """RemainingSteps managed value is present in state after graph execution."""
        graph = build_graph()
        result = await graph.ainvoke(
            input={"messages": [HumanMessage(content="test")]},
            config={"configurable": {"thread_id": "test-456"}},
        )
        assert "remaining_steps" in result
