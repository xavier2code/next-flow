"""Plan node: decide tool calls via LLM.

Per D-02: Single responsibility -- decide whether tool calls are needed.
Per D-05: Graceful degradation -- errors result in error message, not exceptions.
"""

import structlog
from langchain_core.messages import AIMessage

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


async def plan_node(state: AgentState) -> dict:
    """Decide next action using LLM.

    Uses the LLM to analyze the conversation and decide whether to:
    1. Make tool calls (routes to Execute node via conditional edge)
    2. Respond directly (routes to Respond node via conditional edge)

    The LLM is created via get_llm() factory using agent config from graph config.
    """
    try:
        llm = get_llm()
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
            response = await llm.ainvoke(state["messages"])
        except Exception as invoke_err:
            # If invocation failed with tools bound, retry without tools
            if tools_bound:
                logger.warning("invoke_with_tools_failed, retrying without tools", error=str(invoke_err))
                llm = get_llm()
                response = await llm.ainvoke(state["messages"])
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
