from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.v1.router import router as v1_router
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

    app.state.checkpointer = await create_checkpointer(settings.database_url)
    logger.info("checkpointer_initialized")

    yield

    logger.info("shutting_down_application")
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
