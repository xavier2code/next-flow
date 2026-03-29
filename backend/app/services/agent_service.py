"""Agent CRUD service with cursor-based pagination."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


class AgentService:
    """Business logic for agent CRUD."""

    @staticmethod
    async def create(
        db: AsyncSession, user_id: str, data: AgentCreate
    ) -> Agent:
        agent = Agent(
            user_id=user_id,
            name=data.name,
            system_prompt=data.system_prompt,
            model_config=data.llm_config,
        )
        db.add(agent)
        await db.flush()
        await db.refresh(agent)
        return agent

    @staticmethod
    async def get_for_user(
        db: AsyncSession, user_id: str, agent_id: str
    ) -> Agent | None:
        result = await db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: str,
        cursor_ts=None,
        cursor_id: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Agent], bool]:
        query = (
            select(Agent)
            .where(Agent.user_id == user_id)
            .order_by(Agent.created_at.desc(), Agent.id.desc())
        )

        if cursor_ts is not None and cursor_id is not None:
            query = query.where(
                (Agent.created_at, Agent.id) < (cursor_ts, cursor_id)
            )

        query = query.limit(limit + 1)
        result = await db.execute(query)
        items = list(result.scalars().all())
        has_more = len(items) > limit
        return items[:limit], has_more

    @staticmethod
    async def update(
        db: AsyncSession, agent: Agent, data: AgentUpdate
    ) -> Agent:
        update_data = data.model_dump(exclude_unset=True)
        if "llm_config" in update_data:
            agent.model_config = update_data.pop("llm_config")
        for field, value in update_data.items():
            setattr(agent, field, value)
        await db.flush()
        await db.refresh(agent)
        return agent

    @staticmethod
    async def delete(db: AsyncSession, agent: Agent) -> None:
        await db.delete(agent)
        await db.flush()
