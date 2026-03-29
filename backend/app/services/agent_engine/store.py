"""AsyncPostgresStore factory for LangGraph long-term memory.

Uses AsyncPostgresStore from langgraph-store with pgvector-backed
semantic search. Mirrors the checkpointer.py pattern for consistency.
Per D-22: Embedding provider/model configured via Settings.
Per D-25: OpenAI text-embedding-3-small default, Ollama fallback.
"""

import structlog
from langchain_community.embeddings import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langgraph.store.base import BaseStore
from langgraph.store.postgres.aio import AsyncPostgresStore

from app.core.config import settings

logger = structlog.get_logger()


def _get_embedder() -> OpenAIEmbeddings | OllamaEmbeddings:
    """Create an embedding model instance based on Settings.

    Mirrors the get_llm() factory pattern from llm.py.
    Routes by provider string: openai or ollama.

    Returns:
        An embedding model instance.

    Raises:
        ValueError: If the provider string is not recognized.
    """
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key or None,
        )
    elif settings.embedding_provider == "ollama":
        return OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")


async def create_store(database_url: str) -> dict:
    """Create and initialize the async PostgreSQL store for long-term memory.

    The store provides semantic search via pgvector embeddings.
    Per Pitfall 6: Must strip '+asyncpg' from SQLAlchemy URL for psycopg3 compatibility.

    Args:
        database_url: SQLAlchemy-style async URL (postgresql+asyncpg://...).
                     The '+asyncpg' suffix is stripped for psycopg3 compatibility.

    Returns:
        Dict with "store" (AsyncPostgresStore) and "store_ctx" (async context manager)
        so the lifespan can clean up the context manager on shutdown.
    """
    conn_string = database_url.replace("+asyncpg", "")
    logger.info("creating_store", conn_string=conn_string[:30] + "...")

    embedder = _get_embedder()

    store_ctx = AsyncPostgresStore.from_conn_string(
        conn_string,
        pool_config={"min_size": 1, "max_size": 5},
        index={
            "dims": 1536,
            "embed": embedder,
            "fields": ["content"],
        },
    )

    store = await store_ctx.__aenter__()
    await store.setup()  # Create tables and enable pgvector extension (idempotent)

    logger.info("store_ready")
    return {"store": store, "store_ctx": store_ctx}
