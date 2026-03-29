"""WebSocket connection manager for per-user connection tracking.

Manages active WebSocket connections grouped by user ID, supporting
multiple concurrent connections per user and automatic dead-connection
cleanup during broadcast.
"""

from fastapi import WebSocket

import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """Singleton-capable manager tracking active WebSocket connections per user.

    Internal structure:
        _connections: dict[str, list[WebSocket]]  -- user_id -> list of active sockets

    Thread safety note: This manager runs within a single async event loop
    (FastAPI/Starlette), so no explicit locking is needed. All mutations and
    broadcasts are coroutine-based and interleaved cooperatively.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Register a WebSocket connection for a user.

        Creates the user's connection list if this is their first connection.
        """
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info(
            "ws_connected",
            user_id=user_id,
            total=self.get_connection_count(user_id),
        )

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection for a user.

        Deletes the user entry entirely when the connection list becomes empty.
        """
        if user_id in self._connections:
            try:
                self._connections[user_id].remove(websocket)
            except ValueError:
                pass  # Already removed or never tracked
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(
            "ws_disconnected",
            user_id=user_id,
            remaining=self.get_connection_count(user_id),
        )

    async def broadcast_to_user(self, user_id: str, event: dict) -> None:
        """Send a JSON event to all active connections for a user.

        Connections that raise exceptions during send are treated as dead
        and are automatically disconnected.
        """
        connections = self._connections.get(user_id, [])
        if not connections:
            return

        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(user_id, ws)

    def get_connection_count(self, user_id: str) -> int:
        """Return the number of active connections for a user."""
        return len(self._connections.get(user_id, []))

    def get_active_user_count(self) -> int:
        """Return the number of users with at least one active connection."""
        return len(self._connections)
