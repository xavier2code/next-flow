from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import asyncio

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.v1.router import router as v1_router
from app.api.ws.chat import router as ws_router, start_pubsub_listener
from app.api.ws.connection_manager import ConnectionManager
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging, get_logger
from app.db.session import engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize resources on startup, teardown on shutdown."""
    setup_logging()
    logger.info("starting_application", version="0.1.0")

    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    # Tool Registry initialization
    from app.services.tool_registry import get_tool_registry
    from app.services.tool_registry.builtins import register_builtin_tools

    registry = get_tool_registry()
    register_builtin_tools(registry)
    app.state.tool_registry = registry
    logger.info("tool_registry_initialized", tools=registry.list_tools())

    # Checkpointer initialization
    from app.services.agent_engine.checkpointer import create_checkpointer

    cp_result = await create_checkpointer(settings.database_url)
    app.state.checkpointer = cp_result["checkpointer"]
    app.state.checkpointer_ctx = cp_result["ctx"]
    logger.info("checkpointer_initialized")

    # Store initialization (long-term memory with semantic search)
    from app.services.agent_engine.store import create_store

    try:
        store_result = await create_store(settings.database_url)
        app.state.store = store_result["store"]
        app.state.store_ctx = store_result["store_ctx"]
        logger.info("store_initialized")
    except Exception as e:
        logger.warning("store_init_failed", error=str(e))
        app.state.store = None
        app.state.store_ctx = None

    # MemoryService initialization
    from app.services.memory import MemoryService

    memory_service = MemoryService(
        redis=app.state.redis,
        store=app.state.store,
    )
    app.state.memory_service = memory_service

    # Wire memory_service into both analyze and respond nodes
    from app.services.agent_engine.nodes.analyze import set_memory_service as set_analyze_memory
    from app.services.agent_engine.nodes.respond import set_memory_service as set_respond_memory

    set_analyze_memory(memory_service)
    set_respond_memory(memory_service)
    logger.info("memory_service_initialized")

    # ConnectionManager for WebSocket connections
    app.state.connection_manager = ConnectionManager()
    logger.info("connection_manager_initialized")

    # MCPManager initialization (D-01, D-03)
    from app.services.mcp import MCPManager
    from app.db.session import async_session_factory

    mcp_manager = MCPManager(
        tool_registry=registry,
        session_factory=async_session_factory,
        timeout=settings.mcp_tool_timeout,
        health_check_interval=settings.mcp_health_check_interval,
    )
    app.state.mcp_manager = mcp_manager
    await mcp_manager.connect_all()
    await mcp_manager.start_health_check()
    logger.info("mcp_manager_initialized", servers=len(mcp_manager.clients))

    # SkillManager initialization
    from minio import Minio

    from app.services.skill import SkillStorage
    from app.services.skill.manager import SkillManager
    from app.services.skill.sandbox import SkillSandbox

    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    skill_storage = SkillStorage(minio_client, bucket=settings.minio_bucket)
    skill_sandbox = SkillSandbox(settings)

    from app.db.session import async_session_factory

    skill_manager = SkillManager(
        tool_registry=registry,
        session_factory=async_session_factory,
        skill_storage=skill_storage,
        skill_sandbox=skill_sandbox,
        skill_content={},
        timeout=settings.skill_sandbox_timeout,
        health_check_interval=settings.skill_health_check_interval,
    )
    app.state.skill_manager = skill_manager
    await skill_manager.enable_all()
    await skill_manager.start_health_check()

    # Wire skill_manager into builtins and analyze node
    from app.services.tool_registry.builtins import set_skill_manager as set_builtins_skill_manager
    from app.services.agent_engine.nodes.analyze import set_skill_manager as set_analyze_skill_manager

    set_builtins_skill_manager(skill_manager)
    set_analyze_skill_manager(skill_manager)
    logger.info("skill_manager_initialized")

    # Wire tool_registry into plan and execute nodes
    from app.services.agent_engine.nodes.plan import set_tool_registry as set_plan_tool_registry
    from app.services.agent_engine.nodes.execute import set_tool_registry as set_execute_tool_registry

    set_plan_tool_registry(registry)
    set_execute_tool_registry(registry)

    # Build and compile the agent graph
    from app.services.agent_engine import build_graph

    app.state.graph = build_graph(
        checkpointer=app.state.checkpointer,
        store=app.state.store,
    )
    logger.info("agent_graph_initialized")

    # Redis pub/sub listener for cross-worker WebSocket broadcasting
    pubsub_task = asyncio.create_task(
        start_pubsub_listener(
            app.state.redis,
            app.state.connection_manager,
            settings.redis_pubsub_prefix,
        )
    )
    app.state.pubsub_task = pubsub_task
    logger.info("pubsub_listener_started")

    yield

    logger.info("shutting_down_application")

    # Shutdown SkillManager
    if hasattr(app.state, "skill_manager") and app.state.skill_manager:
        await app.state.skill_manager.stop_health_check()
        await app.state.skill_manager.disable_all()

    # Shutdown MCPManager
    if hasattr(app.state, "mcp_manager") and app.state.mcp_manager:
        await app.state.mcp_manager.stop_health_check()
        await app.state.mcp_manager.disconnect_all()

    # Cancel pub/sub listener
    app.state.pubsub_task.cancel()
    try:
        await app.state.pubsub_task
    except asyncio.CancelledError:
        pass

    # Clean up Checkpointer context manager
    if hasattr(app.state, "checkpointer_ctx") and app.state.checkpointer_ctx:
        await app.state.checkpointer_ctx.__aexit__(None, None, None)

    # Clean up Store context manager
    if hasattr(app.state, "store_ctx") and app.state.store_ctx:
        await app.state.store_ctx.__aexit__(None, None, None)

    await app.state.redis.close()
    await engine.dispose()


app = FastAPI(
    title="NextFlow API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors with consistent JSON format."""
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
    )


@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Handle application exceptions with consistent JSON format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.error_code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle all unhandled exceptions with consistent JSON format."""
    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


app.include_router(v1_router)
app.include_router(ws_router)

# NOTE: Uvicorn WebSocket ping/pong is configured at the server level.
# Run with: uvicorn app.main:app --ws-ping-interval 20 --ws-ping-timeout 20
