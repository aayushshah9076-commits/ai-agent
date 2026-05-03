"""WebSocket manager for real-time progress updates."""

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]):
        """Send message to all connected clients."""
        text = json.dumps(message)
        logger.info(f"WS broadcast ({len(self.active_connections)} clients): type={message.get('type')} stage={message.get('stage')} progress={message.get('progress')}")
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(text)
            except Exception as e:
                logger.warning(f"WS send failed: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_progress(
        self,
        stage: str,
        step: str,
        progress: float,
        message: str,
        data: dict | None = None,
    ):
        """Send structured progress update."""
        await self.broadcast({
            "type": "progress",
            "stage": stage,
            "step": step,
            "progress": min(max(progress, 0), 100),
            "message": message,
            "data": data or {},
        })

    async def send_error(self, stage: str, message: str):
        await self.broadcast({
            "type": "error",
            "stage": stage,
            "message": message,
        })

    async def send_complete(self, result: dict):
        await self.broadcast({
            "type": "complete",
            "result": result,
        })
