"""Respond node: generate final answer via LLM and trigger memory write-back.

Per D-05: Graceful degradation on errors.
Per D-13: Memory write-back via asyncio.create_task (fire-and-forget).
Per D-20: Synchronized writes to both Redis (short-term) and Store (long-term).
"""

import asyncio

import structlog
from langchain_core.messages import AIMessage, SystemMessage

from app.services.agent_engine.llm import get_llm
from app.services.agent_engine.state import AgentState

logger = structlog.get_logger()

# Module-level reference set during lifespan initialization.
# This avoids passing memory_service through graph config.
_memory_service = None


def set_memory_service(service) -> None:
    """Set the module-level memory_service reference.

    Called from main.py lifespan after MemoryService is created.
    """
    global _memory_service
    _memory_service = service


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
    merged_content = "\n".join(m.content for m in system_msgs)
    return [SystemMessage(content=merged_content)] + non_system_msgs


async def respond_node(state: AgentState, *, config: dict | None = None) -> dict:
    """Generate final response to the user using LLM and trigger memory write-back.

    After generating the response, fires an async task to:
    1. Store the conversation turn in short-term Redis memory
    2. Extract key facts and store in long-term memory via Store

    config: LangGraph config dict, expected to contain:
      config["configurable"]["thread_id"] -- the conversation thread ID
    """
    try:
        # Extract llm_config from agent config (if present)
        llm_config = None
        if config:
            agent_config = config.get("configurable", {}).get("agent_config")
            if agent_config:
                llm_config = agent_config.get("llm_config")

        llm = get_llm(llm_config)
        response = await llm.ainvoke(_sanitize_messages_for_llm(state["messages"]))

        # Trigger async memory write-back (per D-13, D-18)
        if _memory_service:
            try:
                # Extract user_id from state (set by API layer)
                user_id = state.get("user_id")
                # Derive thread_id from LangGraph config configurable dict
                thread_id = None
                if config:
                    configurable = config.get("configurable", {})
                    thread_id = configurable.get("thread_id", None)

                if user_id:
                    # Fire-and-forget: extract facts and store to both backends
                    asyncio.create_task(
                        _memory_service.extract_and_store(
                            messages=state["messages"],
                            user_id=user_id,
                            thread_id=thread_id or "default",
                        )
                    )
                    logger.info("memory_write_back_triggered", user_id=user_id)
            except Exception as mem_err:
                logger.warning("memory_write_back_failed", error=str(mem_err))

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
