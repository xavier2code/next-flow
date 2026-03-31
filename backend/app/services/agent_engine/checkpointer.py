"""PostgresSaver checkpointer for conversation state persistence.

Uses AsyncPostgresSaver from langgraph-checkpoint-postgres.
Per Pitfall 6: Must strip '+asyncpg' from SQLAlchemy URL for psycopg3 compatibility.
"""

import structlog
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = structlog.get_logger()


async def create_checkpointer(database_url: str) -> dict:
    """Create and initialize the async PostgreSQL checkpointer.

    Args:
        database_url: SQLAlchemy-style async URL (postgresql+asyncpg://...).
                     The '+asyncpg' suffix is stripped for psycopg3 compatibility.

    Returns:
        Dict with 'checkpointer' (AsyncPostgresSaver) and 'ctx' (the async
        context manager that must stay open for the saver's lifetime).
    """
    # Strip SQLAlchemy async driver suffix for psycopg3 (Pitfall 6)
    conn_string = database_url.replace("+asyncpg", "")
    logger.info("creating_checkpointer", conn_string=conn_string[:30] + "...")

    # langgraph-checkpoint-postgres >= 3.0 returns an async context manager
    ctx = AsyncPostgresSaver.from_conn_string(conn_string)
    checkpointer = await ctx.__aenter__()
    logger.info("checkpointer_ready")
    return {"checkpointer": checkpointer, "ctx": ctx}
