from fastapi import APIRouter

from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.mcp_servers import router as mcp_servers_router
from app.api.v1.messages import router as messages_router
from app.api.v1.settings import router as settings_router
from app.api.v1.skills import router as skills_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(conversations_router)
router.include_router(agents_router)
router.include_router(settings_router)
router.include_router(messages_router)
router.include_router(mcp_servers_router)
router.include_router(skills_router)
