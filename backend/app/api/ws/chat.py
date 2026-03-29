"""WebSocket chat endpoint with JWT auth, Redis pub/sub listener, and connection lifecycle.

Provides:
  - /ws/chat?token={jwt} -- authenticated WebSocket for streaming agent events
  - start_pubsub_listener() -- background task for cross-worker event broadcasting
"""

import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

import structlog

from app.api.ws.connection_manager import ConnectionManager
from app.core.security import decode_token

logger = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


async def _validate_ws_token(token: str) -> str | None:
    """Validate a JWT token for WebSocket authentication.

    Returns the user_id (sub claim) if valid, or None on any failure.
    Only accepts tokens with type='access'.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------


@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """Authenticated WebSocket endpoint for streaming agent events.

    Flow:
      1. Validate JWT token BEFORE accepting the connection (per D-07).
      2. Accept and register the connection with ConnectionManager.
      3. Keep connection alive with a receive loop (client messages are
         sent via REST per D-08; WS is server-only push).
      4. On disconnect, clean up via ConnectionManager.disconnect in finally.

    Heartbeat is handled at the Uvicorn transport level (ping/pong),
    not in application code (per D-10).
    """
    # Validate token before accept
    user_id = await _validate_ws_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    manager: ConnectionManager = websocket.app.state.connection_manager
    manager.connect(user_id, websocket)

    try:
        # Receive loop: keeps connection alive, detects disconnect.
        # Client sends messages via REST (D-08); WS is server-push only.
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", user_id=user_id)
    finally:
        manager.disconnect(user_id, websocket)


# ---------------------------------------------------------------------------
# Redis pub/sub listener (runs as a background task in the lifespan)
# ---------------------------------------------------------------------------


async def start_pubsub_listener(
    redis: aioredis.Redis,
    manager: ConnectionManager,
    channel_prefix: str,
) -> None:
    """Subscribe to Redis pub/sub channels and broadcast events to users.

    Channel pattern: {channel_prefix}:{user_id}
    Messages are JSON-encoded dicts with ``type`` and ``data`` keys.
    """
    pubsub = redis.pubsub()
    try:
        await pubsub.psubscribe(f"{channel_prefix}:*")
        logger.info("pubsub_listener_started", pattern=f"{channel_prefix}:*")

        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                # Extract user_id from channel (last segment after prefix)
                user_id = channel.split(":")[-1]
                try:
                    event = json.loads(message["data"])
                    await manager.broadcast_to_user(user_id, event)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "pubsub_invalid_message",
                        channel=channel,
                    )
    finally:
        await pubsub.aclose()
        logger.info("pubsub_listener_stopped")
