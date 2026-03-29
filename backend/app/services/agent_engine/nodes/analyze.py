"""Analyze node: intent analysis and context injection.

Per D-02: Single responsibility -- analyze user intent and inject context.
This is the first node in the pipeline. It prepares the state for the Plan node.
"""

import structlog

from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()


async def analyze_node(state: AgentState) -> dict:
    """Analyze user intent and prepare context for planning.

    Currently a pass-through stub. Will be enhanced with:
    - LLM-based intent classification (future)
    - Short-term memory context injection (Phase 4)
    """
    logger.info("analyze_node_entered", messages_count=len(state["messages"]))
    return {"scratchpad": "Intent analyzed. Ready for planning."}
