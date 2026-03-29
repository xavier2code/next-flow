"""Agent REST endpoints: CRUD with envelope responses."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.schemas.envelope import EnvelopeResponse, PaginatedResponse, PaginationMeta, encode_cursor, decode_cursor
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", status_code=201)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[AgentResponse]:
    agent = await AgentService.create(db, str(current_user.id), data)
    await db.commit()
    return EnvelopeResponse(data=AgentResponse.model_validate(agent))


@router.get("")
async def list_agents(
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[AgentResponse]:
    cursor_ts = None
    cursor_id = None
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)

    items, has_more = await AgentService.list_for_user(
        db, str(current_user.id), cursor_ts, cursor_id, limit
    )

    next_cursor = None
    if has_more and items:
        next_cursor = encode_cursor(items[-1].created_at, str(items[-1].id))

    return PaginatedResponse(
        data=[AgentResponse.model_validate(a) for a in items],
        meta=PaginationMeta(cursor=next_cursor, has_more=has_more),
    )


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[AgentResponse]:
    agent = await AgentService.get_for_user(db, str(current_user.id), agent_id)
    if agent is None:
        raise NotFoundException(message="Agent not found")
    return EnvelopeResponse(data=AgentResponse.model_validate(agent))


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[AgentResponse]:
    agent = await AgentService.get_for_user(db, str(current_user.id), agent_id)
    if agent is None:
        raise NotFoundException(message="Agent not found")
    agent = await AgentService.update(db, agent, data)
    await db.commit()
    return EnvelopeResponse(data=AgentResponse.model_validate(agent))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    agent = await AgentService.get_for_user(db, str(current_user.id), agent_id)
    if agent is None:
        raise NotFoundException(message="Agent not found")
    await AgentService.delete(db, agent)
    await db.commit()
    return Response(status_code=204)
