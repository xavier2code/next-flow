"""Respond node: generate final answer.

Per D-02: Single responsibility -- generate the final response to the user.
"""

import structlog
from langchain_core.messages import AIMessage

from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()


async def respond_node(state: AgentState) -> dict:
    """Generate final response to the user.

    Currently returns a simple AI message. Will be enhanced with
    LLM-based response generation (Plan 02).
    """
    logger.info("respond_node_entered")
    # Find the last AI message content to echo, or generate default
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            return {
                "messages": [AIMessage(content=msg.content)],
                "plan": "Response generated.",
            }
    return {
        "messages": [AIMessage(content="I received your message.")],
        "plan": "Response generated.",
    }
