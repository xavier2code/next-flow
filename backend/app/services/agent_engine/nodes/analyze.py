"""Analyze node: intent analysis and context injection.

Per D-06: Messages list injection -- prepend Redis context as messages in state.
Per D-16: Single query for long-term memory before planning.
Per D-19: Long-term memory injected as SystemMessage with "Relevant past context:" prefix.
Per D-21: Uses memory_service methods exclusively, never Redis/Store directly.
"""

import structlog
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()

# Module-level reference set during lifespan initialization.
# Same pattern as respond.py -- avoids passing memory_service through graph config.
# Set via set_memory_service() called from main.py lifespan.
_memory_service = None
_skill_manager = None


def set_memory_service(service) -> None:
    """Set the module-level memory_service reference.

    Called from main.py lifespan after MemoryService is created.
    """
    global _memory_service
    _memory_service = service


def set_skill_manager(manager) -> None:
    """Set the SkillManager reference for skill context injection."""
    global _skill_manager
    _skill_manager = manager


async def analyze_node(state: AgentState, *, config: dict | None = None) -> dict:
    """Analyze user intent and inject memory context for planning.

    Performs two context injections:
    1. Short-term memory: summary + recent messages from Redis (via memory_service.get_context)
    2. Long-term memory: semantic search results from Store (via memory_service.get_long_term_context)

    Per D-06: Context is prepended as messages in state (no new AgentState fields for memory).
    Per D-21: Uses memory_service methods exclusively -- never Redis/Store directly.

    config: LangGraph config dict, expected to contain:
      config["configurable"]["thread_id"] -- the conversation thread ID
    user_id is read from state (set by API layer on graph invocation).
    """
    logger.info("analyze_node_entered", messages_count=len(state["messages"]))

    context_messages = []
    # Extract last message content, handling both LangChain message objects
    # and plain dicts (for test scaffolding that bypasses graph reducers)
    last_msg = state["messages"][-1] if state["messages"] else None
    last_message = ""
    if last_msg is not None:
        if hasattr(last_msg, "content"):
            last_message = last_msg.content
        elif isinstance(last_msg, dict):
            last_message = last_msg.get("content", "")
    user_id = state.get("user_id", None)

    # Derive thread_id from LangGraph config configurable dict
    # The API layer sets config={"configurable": {"thread_id": "...", "user_id": "..."}}
    # when invoking the graph. LangGraph passes this as the config parameter.
    thread_id = None
    if config:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", None)

    # Inject enabled skill summaries into Agent context (per D-16)
    if _skill_manager:
        try:
            summaries = _skill_manager.get_enabled_skill_summaries()
            if summaries:
                summary_text = "可用技能：" + ", ".join(
                    f"{s['name']}({s['description']})" for s in summaries
                )
                context_messages.append(
                    SystemMessage(content=summary_text)
                )
                logger.info(
                    "skill_summary_injected",
                    skill_count=len(summaries),
                )
        except Exception as e:
            logger.warning("skill_summary_injection_failed", error=str(e))

    if not _memory_service:
        logger.debug("memory_service_not_available")
        return {
            "messages": context_messages,
            "scratchpad": "Intent analyzed. Memory service not available. Ready for planning.",
        }

    # Long-term memory injection via memory_service (per D-16, D-19, D-21)
    # Uses memory_service.get_long_term_context() -- NOT direct Store/LongTermMemory access.
    if user_id and last_message:
        try:
            results = await _memory_service.get_long_term_context(
                user_id=user_id,
                query=str(last_message),
                limit=5,  # Per Claude's discretion: Top-K=5 (D-17)
            )
            if results:
                context_parts = [r["content"] for r in results if r.get("content")]
                if context_parts:
                    context_text = "; ".join(context_parts)
                    context_messages.append(
                        SystemMessage(content=f"Relevant past context: {context_text}")
                    )
                    logger.info(
                        "long_term_memory_injected",
                        user_id=user_id,
                        results_count=len(results),
                    )
        except Exception as e:
            logger.warning("long_term_memory_retrieval_failed", error=str(e))

    # Short-term memory injection (per D-06)
    # Uses memory_service.get_context() -- NOT direct Redis access (per D-21).
    if thread_id:
        try:
            ctx = await _memory_service.get_context(thread_id)
            summary = ctx.get("summary")
            recent_msgs = ctx.get("messages", [])

            if summary:
                context_messages.append(
                    SystemMessage(content=f"Conversation summary: {summary}")
                )

            for msg in recent_msgs[-10:]:  # Limit to last 10 from Redis
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    context_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    context_messages.append(AIMessage(content=content))

            logger.info(
                "short_term_memory_injected",
                thread_id=thread_id,
                summary_present=summary is not None,
                recent_count=len(recent_msgs),
            )
        except Exception as e:
            logger.warning("short_term_memory_retrieval_failed", error=str(e))

    return {
        "messages": context_messages,
        "scratchpad": "Intent analyzed. Memory context injected. Ready for planning.",
    }
