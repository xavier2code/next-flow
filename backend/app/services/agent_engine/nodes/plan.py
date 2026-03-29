"""Plan node: decide tool calls via LLM.

Per D-02: Single responsibility -- decide whether tool calls are needed.
Per D-05: Graceful degradation -- errors result in error message, not exceptions.
"""

import structlog
from langchain_core.messages import AIMessage

from app.services.agent_engine.llm import get_llm
from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()


async def plan_node(state: AgentState) -> dict:
    """Decide next action using LLM.

    Uses the LLM to analyze the conversation and decide whether to:
    1. Make tool calls (routes to Execute node via conditional edge)
    2. Respond directly (routes to Respond node via conditional edge)

    The LLM is created via get_llm() factory using agent config from graph config.
    """
    try:
        # TODO: Get agent-specific config from graph config (future enhancement)
        # For now, use default LLM config from Settings
        llm = get_llm()

        # Simple invocation: pass message history to LLM
        # Tool binding will be added when Tool Registry is injected
        response = await llm.ainvoke(state["messages"])

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
