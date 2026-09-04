"""Real-time WebSocket telemetry broadcaster and active client connection manager."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger("halocas.core.telemetry")


class ConnectionManager:
    """Manages active WebSocket client connections for real-time safety telemetry broadcasts."""

    def __init__(self) -> None:
        """Initialize thread-safe connection tracking list."""
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept incoming connection and register client.

        Args:
            websocket: Incoming WebSocket client handle.
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket telemetry client connected (total: %d)", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister disconnected client.

        Args:
            websocket: Disconnected WebSocket client handle.
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket telemetry client disconnected (remaining: %d)", len(self.active_connections))

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        """Send JSON telemetry payload to all connected clients.

        Prunes dead or broken connections automatically.

        Args:
            data: Serializable dictionary payload to broadcast.
        """
        async with self._lock:
            disconnected: list[WebSocket] = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(data)
                except Exception:
                    disconnected.append(connection)

            for dead_connection in disconnected:
                if dead_connection in self.active_connections:
                    self.active_connections.remove(dead_connection)


manager = ConnectionManager()
