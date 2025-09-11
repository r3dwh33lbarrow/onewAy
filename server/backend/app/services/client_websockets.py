import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket


class ClientWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_uuid: str):
        await websocket.accept()

        async with self._lock:
            if client_uuid not in self.active_connections:
                self.active_connections[client_uuid] = set()
            self.active_connections[client_uuid].add(websocket)

    async def disconnect(self, websocket: WebSocket, client_uuid: str):
        async with self._lock:
            if client_uuid in self.active_connections:
                self.active_connections[client_uuid].discard(websocket)
                if not self.active_connections[client_uuid]:
                    del self.active_connections[client_uuid]

    async def send_to_client(self, client_uuid: str, message: dict):
        if client_uuid not in self.active_connections:
            return

        connections_to_remove = set()
        message_json = json.dumps(message)

        for websocket in self.active_connections[client_uuid].copy():
            try:
                await websocket.send_text(message_json)
            except Exception:
                connections_to_remove.add(websocket)

        if connections_to_remove:
            async with self._lock:
                self.active_connections[client_uuid].difference_update(connections_to_remove)
                if not self.active_connections[client_uuid]:
                    del self.active_connections[client_uuid]


client_websocket_manager = ClientWebSocketManager()