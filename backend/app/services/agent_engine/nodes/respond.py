"""Respond node: generate final answer via LLM.

Per D-02: Single responsibility -- generate the final response.
Per D-05: Graceful degradation on errors.
"""

import structlog
from langchain_core.messages import AIMessage

from app.services.agent_engine.llm import get_llm
from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()


async def respond_node(state: AgentState) -> dict:
    """Generate final response to the user using LLM.

    Invokes the LLM with the full message history (including tool results)
    to produce a coherent final answer.
    """
    try:
        llm = get_llm()
        response = await llm.ainvoke(state["messages"])
        return {
            "messages": [response],
            "plan": "Response generated.",
        }
    except Exception as e:
        logger.error("respond_node_error", error=str(e))
        # D-05: Graceful degradation
        return {
            "messages": [AIMessage(content="I apologize, but I encountered an error generating a response. Please try again.")],
            "plan": "Error in response generation.",
        }
