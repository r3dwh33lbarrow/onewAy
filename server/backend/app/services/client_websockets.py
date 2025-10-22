import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket

from app.logger import get_logger
from app.services.user_websockets import user_websocket_manager

log = get_logger()


class ClientWebSocketManager:
    """
    Manages WebSocket connections for client applications.

    Maintains active client connections and handles message broadcasting.
    Thread-safe operations using asyncio locks.
    """

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_uuid: str):
        """
        Accept and register a WebSocket connection for a client.

        Args:
            websocket: WebSocket connection to register
            client_uuid: Client identifier
        """
        await websocket.accept()

        async with self._lock:
            if client_uuid not in self.active_connections:
                self.active_connections[client_uuid] = set()
            self.active_connections[client_uuid].add(websocket)

        log.info(f"WebSocket connected for client {client_uuid}")

    async def disconnect(self, websocket: WebSocket, client_uuid: str):
        """
        Remove a WebSocket connection for a client.

        Args:
            websocket: WebSocket connection to remove
            client_uuid: Client identifier
        """
        async with self._lock:
            if client_uuid in self.active_connections:
                self.active_connections[client_uuid].discard(websocket)
                if not self.active_connections[client_uuid]:
                    del self.active_connections[client_uuid]

        log.info(f"WebSocket disconnected for client {client_uuid}")

    async def send_to_client(self, client_uuid: str, message: dict):
        """
        Send a message to all connections for a specific client.

        Args:
            client_uuid: Target client identifier
            message: Message data to send
        """
        if client_uuid not in self.active_connections:
            return

        connections_to_remove = set()
        message_json = json.dumps(message)

        for websocket in self.active_connections[client_uuid].copy():
            try:
                await websocket.send_text(message_json)
                log.info(f"Message sent to client {client_uuid}")
            except Exception as e:
                log.warning(f"Failed to send message to WebSocket: {e}")
                connections_to_remove.add(websocket)

        if connections_to_remove:
            async with self._lock:
                self.active_connections[client_uuid].difference_update(
                    connections_to_remove
                )
                if not self.active_connections[client_uuid]:
                    del self.active_connections[client_uuid]

    async def disconnect_all(self, client_uuid: str, code: int = 1011, reason: str = "Client revoked"):
        """Close and remove all WebSocket connections for a client."""
        async with self._lock:
            connections = list(self.active_connections.get(client_uuid, set()))

        for websocket in connections:
            try:
                await websocket.close(code=code, reason=reason)
            except Exception as exc:
                log.debug("Failed to close websocket cleanly for %s: %s", client_uuid, exc)
            await self.disconnect(websocket, client_uuid)

    @staticmethod
    async def broadcast_client_alive_status(username: str, alive: bool):
        """
        Broadcast client online/offline status to all users.

        Args:
            username: Client username
            alive: True if online, False if offline
        """
        await user_websocket_manager.send_client_alive_update(
            {"username": username, "alive": alive}
        )


client_websocket_manager = ClientWebSocketManager()
