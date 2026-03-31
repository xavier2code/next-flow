"""Execute node: sequential tool invocation via Tool Registry.

Per D-03: Sequential tool execution (one at a time).
Per D-05: Graceful degradation -- errors as ToolMessage content, not exceptions.
"""

import structlog
from langchain_core.messages import ToolMessage

from app.services.agent_engine.state import AgentState
from app.services.tool_registry import ToolRegistry, ToolNotFoundError

logger = structlog.get_logger()

# Module-level reference set during lifespan initialization.
_tool_registry: ToolRegistry | None = None


def set_tool_registry(registry: ToolRegistry) -> None:
    """Set the module-level tool_registry reference."""
    global _tool_registry
    _tool_registry = registry


async def execute_node(state: AgentState) -> dict:
    """Execute tool calls from the Plan node's AI message.

    Processes each tool_call sequentially (D-03). Routes through Tool Registry.
    On failure, returns error as ToolMessage content (D-05).

    Args:
        state: Current agent state with messages containing tool calls.
        tool_registry: Tool Registry instance (injected via graph node config).
    """
    last_message = state["messages"][-1]
    tool_messages = []

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.warning("execute_node_no_tool_calls")
        return {"plan": "No tool calls to execute."}

    if _tool_registry is None:
        logger.error("execute_node_no_registry")
        # Return error messages for all pending tool calls
        for tool_call in last_message.tool_calls:
            tool_messages.append(
                ToolMessage(
                    content="Error: Tool Registry not available",
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": tool_messages}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        try:
            logger.info("tool_executing", tool=tool_name)
            result = await _tool_registry.invoke(tool_name, tool_args)
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )
        except ToolNotFoundError:
            logger.warning("tool_not_found", tool=tool_name)
            tool_messages.append(
                ToolMessage(
                    content=f"Error: Tool '{tool_name}' not found",
                    tool_call_id=tool_call["id"],
                )
            )
        except Exception as e:
            logger.warning("tool_execution_failed", tool=tool_name, error=str(e))
            tool_messages.append(
                ToolMessage(
                    content=f"Error executing {tool_name}: {e}",
                    tool_call_id=tool_call["id"],
                )
            )

    return {"messages": tool_messages, "plan": f"Executed {len(tool_messages)} tool(s)."}
