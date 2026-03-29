"""Unified MemoryService: single entry point for all memory operations.

Per D-18, D-21: Nodes call MemoryService methods, never Redis or Store directly.
Per D-13, D-14: LLM-based fact extraction from conversation exchanges.
Per D-20: Synchronized write to short-term memory only; long-term is updated
after the Respond node completes.
"""

import json

import redis.asyncio as aioredis
import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.store.base import BaseStore

from app.services.agent_engine.llm import get_llm
from app.services.memory.long_term import LongTermMemory
from app.services.memory.short_term import ShortTermMemory

logger = structlog.get_logger(__name__)


class MemoryService:
    """Unified memory service coordinating short-term and long-term memory.

    This is the single entry point for all memory operations. It composes
    ShortTermMemory (Redis) and LongTermMemory (Store) and provides
    high-level methods for the agent engine nodes.
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        store: BaseStore,
        window_size: int = 20,
        summary_threshold: int = 15,
        ttl: int = 86400,
    ):
        """Initialize the memory service.

        Args:
            redis: Async Redis client for short-term memory.
            store: LangGraph BaseStore for long-term memory.
            window_size: Max messages per thread in short-term memory (D-01).
            summary_threshold: Message count triggering compression (D-05).
            ttl: TTL in seconds for short-term memory keys (D-04).
        """
        self._short_term = ShortTermMemory(
            redis, window_size, summary_threshold, ttl
        )
        self._long_term = LongTermMemory(store)
        self._redis = redis

    async def add_message(
        self, thread_id: str, role: str, content: str
    ) -> None:
        """Add a message to short-term memory.

        Per D-20: Synchronized write to Redis short-term only.
        Long-term memory is updated by extract_and_store after Respond.

        Args:
            thread_id: Conversation thread identifier.
            role: Message role (human, ai, system).
            content: Message content text.
        """
        await self._short_term.add_message(thread_id, role, content)

    async def get_context(self, thread_id: str) -> dict:
        """Retrieve conversation context from short-term memory.

        Args:
            thread_id: Conversation thread identifier.

        Returns:
            Dict with 'summary' and 'messages' from ShortTermMemory.
        """
        return await self._short_term.get_context(thread_id)

    async def extract_and_store(
        self,
        messages: list,
        user_id: str,
        thread_id: str,
    ) -> None:
        """Extract key facts from conversation and store in long-term memory.

        Per D-13, D-14, D-18, D-20: Single entry point called after Respond node.
        Uses LLM to extract facts, then deduplicates before storing.

        This is a fire-and-forget operation (per D-13): errors are logged
        but never raised.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            user_id: User identifier for namespace scoping.
            thread_id: Conversation thread identifier.
        """
        try:
            if not messages or len(messages) < 2:
                return

            # Filter to get only the latest exchange (last user + last AI)
            # Per Pitfall 4: avoid burning tokens on every turn for trivial checks
            last_human = None
            last_ai = None
            for msg in reversed(messages):
                role = msg.get("role", "")
                if role == "ai" and last_ai is None:
                    last_ai = msg.get("content", "")
                elif role == "human" and last_human is None:
                    last_human = msg.get("content", "")
                if last_human is not None and last_ai is not None:
                    break

            if not last_human or not last_ai:
                return

            # Skip extraction for very short messages (Pitfall 4 heuristic)
            if len(last_human.strip()) < 10:
                return

            # Call LLM to extract key facts (D-14)
            llm = get_llm()
            system_prompt = (
                "Extract key facts, preferences, or important information from "
                "this conversation. Output a JSON array of objects, each with "
                "'content' (the fact), and 'type' (one of: preference, fact, "
                "instruction, context). If no significant facts, output empty array."
            )
            user_prompt = f"Human: {last_human}\nAI: {last_ai}"

            extraction_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await llm.ainvoke(extraction_messages)

            # Parse JSON response
            try:
                facts = json.loads(response.content)
            except json.JSONDecodeError:
                logger.warning(
                    "fact_extraction_parse_failed",
                    response_preview=response.content[:200],
                )
                return

            if not isinstance(facts, list):
                return

            # Process each extracted fact
            for fact in facts:
                if not isinstance(fact, dict):
                    continue

                fact_content = fact.get("content", "")
                fact_type = fact.get("type", "fact")
                if not fact_content:
                    continue

                # Fetch existing facts for deduplication (D-15)
                existing = await self._long_term.search(
                    user_id, fact_content, limit=5
                )
                existing_contents = [e["content"] for e in existing]

                # Check dedup
                should = await self._long_term.should_store(
                    fact_content, existing_contents
                )
                if should:
                    await self._long_term.store_fact(
                        user_id, fact_content, fact_type, thread_id
                    )

            logger.debug(
                "extract_and_store_completed",
                user_id=user_id,
                thread_id=thread_id,
                facts_extracted=len(facts),
            )

        except Exception:
            logger.exception(
                "extract_and_store_failed",
                user_id=user_id,
                thread_id=thread_id,
            )

    async def get_long_term_context(
        self, user_id: str, query: str, limit: int = 5
    ) -> list[dict]:
        """Retrieve relevant long-term memory facts for a query.

        Args:
            user_id: User identifier for namespace scoping.
            query: Natural language search query.
            limit: Maximum number of results.

        Returns:
            List of dicts with 'key', 'content', and 'score' fields.
        """
        return await self._long_term.search(user_id, query, limit)
