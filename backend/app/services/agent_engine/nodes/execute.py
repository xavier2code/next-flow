"""Execute node: sequential tool invocation.

Per D-02: Single responsibility -- execute tool calls.
Per D-03: Sequential tool execution (one at a time).
Per D-05: Graceful degradation -- tool failures return ToolMessage with error, not exceptions.
"""

import structlog
from langchain_core.messages import ToolMessage

from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()


async def execute_node(state: AgentState) -> dict:
    """Execute tool calls from the Plan node's AI message.

    Processes each tool_call sequentially (D-03). On failure, returns
    error as ToolMessage content instead of raising (D-05).
    """
    last_message = state["messages"][-1]
    tool_messages = []

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.warning("execute_node_no_tool_calls")
        return {"plan": "No tool calls to execute."}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        try:
            # TODO: Route to Tool Registry (Plan 03)
            logger.info("tool_executing", tool=tool_name, args=tool_args)
            result = f"Tool '{tool_name}' executed (registry not yet connected)"
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )
        except Exception as e:
            logger.warning("tool_execution_failed", tool=tool_name, error=str(e))
            tool_messages.append(
                ToolMessage(
                    content=f"Error executing {tool_name}: {e}",
                    tool_call_id=tool_call["id"],
                )
            )

    return {"messages": tool_messages, "plan": f"Executed {len(tool_messages)} tools."}
