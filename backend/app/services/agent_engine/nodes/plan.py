"""Plan node: decide tool calls via LLM.

Per D-02: Single responsibility -- decide whether tool calls are needed
and what those calls should be.
"""

import structlog
from langchain_core.messages import AIMessage

from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()


async def plan_node(state: AgentState) -> dict:
    """Decide next action based on analyzed intent.

    Currently returns a simple AI message without tool calls.
    Will be enhanced with LLM-based planning (Plan 02).
    Per D-05: graceful degradation on errors.
    """
    logger.info("plan_node_entered")
    return {
        "messages": [AIMessage(content="Planning complete.")],
        "plan": "No tools needed. Generating response.",
    }
