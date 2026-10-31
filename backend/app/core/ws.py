import asyncio
import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger("krisis.websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def send_json(self, websocket: WebSocket, data: Any):
        """Send JSON string to a specific websocket client."""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as e:
            logger.warning(f"Error sending message to client: {e}")

    async def broadcast(self, data: Any):
        """Broadcast payload (string or json-serializable dict) to all connected WebSocket clients."""
        text_data = data if isinstance(data, str) else json.dumps(data)
        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_text(text_data)
            except Exception as e:
                logger.warning(f"Error sending message to websocket: {e}")
                async with self._lock:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    async def broadcast_json(self, data: Any):
        """Alias for broadcast with json serialization."""
        await self.broadcast(data)


manager = ConnectionManager()
