"""Respond node: generate final answer via LLM and trigger memory write-back.

Per D-05: Graceful degradation on errors.
Per D-13: Memory write-back via asyncio.create_task (fire-and-forget).
Per D-20: Synchronized writes to both Redis (short-term) and Store (long-term).
"""

import asyncio

import structlog
from langchain_core.messages import AIMessage

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


async def respond_node(state: AgentState, *, config: dict | None = None) -> dict:
    """Generate final response to the user using LLM and trigger memory write-back.

    After generating the response, fires an async task to:
    1. Store the conversation turn in short-term Redis memory
    2. Extract key facts and store in long-term memory via Store

    config: LangGraph config dict, expected to contain:
      config["configurable"]["thread_id"] -- the conversation thread ID
    """
    try:
        llm = get_llm()
        response = await llm.ainvoke(state["messages"])

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
