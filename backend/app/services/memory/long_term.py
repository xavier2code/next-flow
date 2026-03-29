"""Long-term memory backed by LangGraph Store with user-scoped namespaces.

Per D-09: Namespace pattern ("users", user_id, "memories") isolates user data.
Per D-15: LLM-based deduplication for fact storage decisions.
Per D-16, D-17: Semantic search via Store's built-in vector indexing.
Per D-21: Resilient — errors are logged but never raised to callers.
"""

import json
import uuid
from datetime import datetime, timezone

import structlog
from langgraph.store.base import BaseStore

from app.services.agent_engine.llm import get_llm

logger = structlog.get_logger(__name__)


class LongTermMemory:
    """Long-term memory using LangGraph Store for persistent fact storage.

    Facts are stored with user-scoped namespaces and automatically indexed
    by the Store for semantic search retrieval.
    """

    def __init__(self, store: BaseStore):
        """Initialize long-term memory.

        Args:
            store: LangGraph BaseStore instance (typically AsyncPostgresStore).
        """
        self._store = store

    async def store_fact(
        self,
        user_id: str,
        content: str,
        fact_type: str,
        source_thread: str,
    ) -> None:
        """Store a fact in the user's long-term memory.

        Args:
            user_id: User identifier for namespace scoping (D-09).
            content: The fact content text.
            fact_type: Type of fact (preference, fact, instruction, context).
            source_thread: Thread ID where this fact was extracted from.
        """
        try:
            namespace = ("users", user_id, "memories")
            key = f"fact_{uuid.uuid4().hex[:8]}"
            value = {
                "content": content,
                "type": fact_type,
                "source_thread": source_thread,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._store.aput(namespace, key, value)
            logger.debug(
                "stored_fact",
                user_id=user_id,
                key=key,
                fact_type=fact_type,
            )
        except Exception:
            logger.exception(
                "store_fact_failed",
                user_id=user_id,
                content_preview=content[:100],
            )

    async def search(
        self, user_id: str, query: str, limit: int = 5
    ) -> list[dict]:
        """Search the user's long-term memory for relevant facts.

        Args:
            user_id: User identifier for namespace scoping.
            query: Natural language search query (D-16).
            limit: Maximum number of results to return (D-17).

        Returns:
            List of dicts with 'key', 'content', and 'score' fields.
        """
        try:
            namespace = ("users", user_id, "memories")
            results = await self._store.asearch(
                namespace, query=query, limit=limit
            )
            return [
                {
                    "key": r.key,
                    "content": r.value.get("content", ""),
                    "score": r.score,
                }
                for r in results
            ]
        except Exception:
            logger.exception(
                "search_failed",
                user_id=user_id,
                query_preview=query[:100],
            )
            return []

    async def should_store(
        self, new_fact: str, existing_facts: list[str]
    ) -> bool:
        """Determine if a new fact should be stored using LLM deduplication.

        Per D-15: Uses LLM to classify the fact as novel, an update, or a duplicate.

        Args:
            new_fact: The candidate fact to potentially store.
            existing_facts: List of existing fact contents for comparison.

        Returns:
            True if the fact should be stored (novel or update), False if duplicate.
            On error, defaults to True (store by default, per resilience principle).
        """
        try:
            llm = get_llm()
            existing_text = "\n".join(
                f"- {fact}" for fact in existing_facts
            ) if existing_facts else "(no existing facts)"

            prompt = (
                f"Given these existing facts:\n{existing_text}\n\n"
                f"Is this new fact '{new_fact}' novel, an update, or a duplicate? "
                'Reply with JSON: {"decision": "store"|"update"|"skip", "reason": "..."}'
            )
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(
                    content="You are a fact deduplication assistant. "
                    "Analyze whether a new fact is novel, updates an existing fact, "
                    "or is a duplicate. Always respond with valid JSON."
                ),
                HumanMessage(content=prompt),
            ]
            response = await llm.ainvoke(messages)
            result = json.loads(response.content)
            decision = result.get("decision", "store")
            logger.debug(
                "dedup_decision",
                decision=decision,
                reason=result.get("reason", ""),
                fact_preview=new_fact[:80],
            )
            return decision in ("store", "update")
        except Exception:
            logger.exception(
                "dedup_failed",
                fact_preview=new_fact[:80],
            )
            return True  # Store by default on error
