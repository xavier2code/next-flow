"""Plan node: decide tool calls via LLM.

Per D-02: Single responsibility -- decide whether tool calls are needed.
Per D-05: Graceful degradation -- errors result in error message, not exceptions.
"""

import structlog
from langchain_core.messages import AIMessage, SystemMessage

from app.services.agent_engine.llm import get_llm
from app.services.agent_engine.state import AgentState
from app.services.tool_registry import ToolRegistry

logger = structlog.get_logger()

# Module-level reference set during lifespan initialization.
_tool_registry: ToolRegistry | None = None


def set_tool_registry(registry: ToolRegistry) -> None:
    """Set the module-level tool_registry reference."""
    global _tool_registry
    _tool_registry = registry


def _sanitize_messages_for_llm(messages: list) -> list:
    """Reorder messages so SystemMessages appear at the beginning.

    Some OpenAI-compatible providers (e.g., MiniMax) require system messages
    to be at the start of the messages list and reject them mid-conversation.
    This collects all SystemMessages, merges their content, and prepends them.
    """
    system_msgs = []
    non_system_msgs = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_msgs.append(msg)
        else:
            non_system_msgs.append(msg)
    if not system_msgs:
        return messages
    # Merge all system message contents into a single SystemMessage at the front
    merged_content = "\n".join(m.content for m in system_msgs)
    return [SystemMessage(content=merged_content)] + non_system_msgs


async def plan_node(state: AgentState, *, config: dict | None = None) -> dict:
    """Decide next action using LLM.

    Uses the LLM to analyze the conversation and decide whether to:
    1. Make tool calls (routes to Execute node via conditional edge)
    2. Respond directly (routes to Respond node via conditional edge)

    The LLM is created via get_llm() factory using agent config from graph config.
    """
    try:
        # Extract llm_config from agent config (if present)
        llm_config = None
        if config:
            agent_config = config.get("configurable", {}).get("agent_config")
            if agent_config:
                llm_config = agent_config.get("llm_config")

        llm = get_llm(llm_config)
        tools_bound = False

        # Bind tools if registry is available
        if _tool_registry:
            tool_schemas = _tool_registry.list_tools()
            if tool_schemas:
                try:
                    llm = llm.bind_tools(tool_schemas)
                    tools_bound = True
                except Exception as bind_err:
                    logger.warning("bind_tools_failed", error=str(bind_err))

        try:
            response = await llm.ainvoke(_sanitize_messages_for_llm(state["messages"]))
        except Exception as invoke_err:
            # If invocation failed with tools bound, retry without tools
            if tools_bound:
                logger.warning("invoke_with_tools_failed, retrying without tools", error=str(invoke_err))
                llm = get_llm(llm_config)
                response = await llm.ainvoke(_sanitize_messages_for_llm(state["messages"]))
            else:
                raise

        return {
            "messages": [response],
            "plan": "LLM planning complete.",
        }
    except Exception as e:
        logger.error("plan_node_error", error=str(e))
        # D-05: Graceful degradation
        return {
            "messages": [AIMessage(content=f"I encountered an error while planning: {e}")],
            "plan": "Error in planning.",
        }
