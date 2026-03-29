"""LangGraph StateGraph construction for the agent workflow.

Topology: START -> Analyze -> Plan -> [conditional] -> Execute -> Respond -> END
If Plan decides no tools are needed, conditional edge skips Execute and goes to Respond.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.services.agent_engine.nodes.analyze import analyze_node
from app.services.agent_engine.nodes.execute import execute_node
from app.services.agent_engine.nodes.plan import plan_node
from app.services.agent_engine.nodes.respond import respond_node
from app.services.agent_engine.state import AgentState


def should_execute(state: AgentState) -> str:
    """Conditional edge: Plan -> Execute if tools needed, Plan -> Respond if not.

    Checks if the last AI message has tool_calls. If yes, route to execute node.
    If no (or last message is not an AIMessage), route directly to respond.
    """
    last_message = state["messages"][-1]
    # Only AIMessage can have tool_calls (LangChain normalized property)
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute"
    return "respond"


def build_graph() -> CompiledStateGraph:
    """Build and compile the agent workflow StateGraph.

    Returns:
        CompiledStateGraph ready for invocation with input and config.
    """
    builder = StateGraph(AgentState)

    # Add nodes (per D-01: 4-node linear pipeline)
    builder.add_node("analyze", analyze_node)
    builder.add_node("plan", plan_node)
    builder.add_node("execute", execute_node)
    builder.add_node("respond", respond_node)

    # Add edges
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "plan")
    # Per D-04: conditional edge from Plan node
    builder.add_conditional_edges(
        "plan",
        should_execute,
        {"execute": "execute", "respond": "respond"},
    )
    builder.add_edge("execute", "respond")
    builder.add_edge("respond", END)

    return builder.compile()
