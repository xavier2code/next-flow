"""Short-term memory backed by Redis Sorted Set with sliding window and summary compression.

Per D-01: Sliding window of last N messages per thread.
Per D-03: Redis key convention nextflow:memory:short:{thread_id}.
Per D-04: TTL refreshed on every write operation (24h default).
Per D-05: Background summary compression via asyncio.create_task (fire-and-forget).
"""

import asyncio
import json
import time

import redis.asyncio as aioredis
import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.agent_engine.llm import get_llm

logger = structlog.get_logger(__name__)


class ShortTermMemory:
    """Short-term conversation memory using Redis Sorted Sets.

    Messages are stored with timestamp scores in a sorted set, enabling
    time-ordered retrieval and efficient window trimming.
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        window_size: int = 20,
        summary_threshold: int = 15,
        ttl: int = 86400,
    ):
        """Initialize short-term memory.

        Args:
            redis: Async Redis client instance.
            window_size: Maximum number of messages to keep per thread (D-01).
            summary_threshold: Message count that triggers background compression (D-05).
            ttl: Time-to-live in seconds for each thread's key (D-04, default 24h).
        """
        self._redis = redis
        self._window_size = window_size
        self._summary_threshold = summary_threshold
        self._ttl = ttl

    async def add_message(self, thread_id: str, role: str, content: str) -> None:
        """Add a message to the thread's short-term memory.

        Uses a Redis pipeline to atomically:
        1. Add the message with its timestamp as score
        2. Trim to window_size (keep most recent)
        3. Refresh the TTL

        If the message count exceeds summary_threshold, fires a background
        compression task.

        Args:
            thread_id: Conversation thread identifier.
            role: Message role (human, ai, system).
            content: Message content text.
        """
        key = f"nextflow:memory:short:{thread_id}"
        timestamp = time.time()
        msg = json.dumps({"role": role, "content": content, "timestamp": timestamp})

        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.zadd(key, {msg: timestamp})
            pipe.zremrangebyrank(key, 0, -(self._window_size + 1))
            pipe.expire(key, self._ttl)
            results = await pipe.execute()

        # Check if compression is needed (D-05)
        card = await self._redis.zcard(key)
        if card > self._summary_threshold:
            asyncio.create_task(self._compress(key))

    async def get_context(self, thread_id: str) -> dict:
        """Retrieve the conversation context for a thread.

        Returns both the summary (if any) and the raw messages.

        Args:
            thread_id: Conversation thread identifier.

        Returns:
            Dict with 'summary' (str or None) and 'messages' (list of dicts).
        """
        key = f"nextflow:memory:short:{thread_id}"
        summary_key = f"{key}:summary"

        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.get(summary_key)
            pipe.zrange(key, 0, -1)
            results = await pipe.execute()

        summary = results[0]
        if isinstance(summary, bytes):
            summary = summary.decode("utf-8")

        raw_messages = results[1]
        messages = []
        for raw in raw_messages:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                messages.append(json.loads(raw))
            except json.JSONDecodeError:
                logger.warning("failed_to_decode_message", raw=raw[:100])

        return {"summary": summary, "messages": messages}

    async def _compress(self, key: str) -> None:
        """Background compression of older messages via LLM summarization.

        Takes the oldest messages (those beyond the recent window), summarizes them,
        stores the summary, and removes the summarized messages from the sorted set.

        This is a fire-and-forget operation (per D-05): errors are logged but never raised.

        Args:
            key: Redis key for the thread's sorted set.
        """
        try:
            # Get all messages
            raw_messages = await self._redis.zrange(key, 0, -1)
            message_count = len(raw_messages)

            if message_count <= self._summary_threshold:
                return  # Nothing to compress

            # Split into old (to compress) and recent (to keep)
            # Keep recent = summary_threshold + 5 messages, compress the rest
            keep_count = self._summary_threshold + 5
            old_count = message_count - keep_count
            if old_count <= 0:
                return

            old_raw = raw_messages[:old_count]
            old_messages = []
            for raw in old_raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                try:
                    old_messages.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue

            if not old_messages:
                return

            # Build text for LLM summarization
            conversation_lines = []
            for msg in old_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                conversation_lines.append(f"{role}: {content}")

            conversation_text = "\n".join(conversation_lines)

            # Use LLM to generate summary
            llm = get_llm()
            system_prompt = (
                "Summarize the following conversation messages into a concise summary "
                "retaining key facts, decisions, and context. Output plain text only."
            )
            messages_for_llm = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=conversation_text),
            ]
            response = await llm.ainvoke(messages_for_llm)
            summary_text = response.content

            # Store summary with same TTL as main key
            summary_key = f"{key}:summary"
            ttl_remaining = await self._redis.ttl(key)
            if ttl_remaining > 0:
                await self._redis.set(summary_key, summary_text, ex=ttl_remaining)
            else:
                await self._redis.set(summary_key, summary_text, ex=self._ttl)

            # Remove old messages from sorted set
            await self._redis.zremrangebyrank(key, 0, old_count - 1)

            logger.info(
                "compressed_short_term_memory",
                key=key,
                old_count=old_count,
                kept_count=keep_count,
            )

        except Exception:
            logger.exception("compression_failed", key=key)
