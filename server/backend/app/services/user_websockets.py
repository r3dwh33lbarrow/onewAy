import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket

from app.logger import get_logger

log = get_logger()


class UserWebSocketManager:
    """
    Manages WebSocket connections and broadcasting messages to connected clients.
    """

    def __init__(self):
        # Store active connections by user UUID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_uuid: str):
        """
        Accept a new WebSocket connection and associate it with a user.

        Args:
            websocket: The WebSocket connection
            user_uuid: The UUID of the authenticated user
        """
        await websocket.accept()

        async with self._lock:
            if user_uuid not in self.active_connections:
                self.active_connections[user_uuid] = set()
            self.active_connections[user_uuid].add(websocket)

        log.info(f"WebSocket connected for user {user_uuid}")

    async def disconnect(self, websocket: WebSocket, user_uuid: str):
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            user_uuid: The UUID of the user
        """
        async with self._lock:
            if user_uuid in self.active_connections:
                self.active_connections[user_uuid].discard(websocket)
                if not self.active_connections[user_uuid]:
                    del self.active_connections[user_uuid]

        log.info(f"WebSocket disconnected for user {user_uuid}")

    async def send_to_user(self, user_uuid: str, message: dict):
        """
        Send a message to all WebSocket connections for a specific user.

        Args:
            user_uuid: The UUID of the user to send the message to
            message: The message dictionary to send
        """
        if user_uuid not in self.active_connections:
            return

        connections_to_remove = set()
        message_json = json.dumps(message)

        for websocket in self.active_connections[user_uuid].copy():
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                log.warning(f"Failed to send message to WebSocket: {e}")
                connections_to_remove.add(websocket)

        # Clean up failed connections
        if connections_to_remove:
            async with self._lock:
                self.active_connections[user_uuid].difference_update(
                    connections_to_remove
                )
                if not self.active_connections[user_uuid]:
                    del self.active_connections[user_uuid]

    async def broadcast_to_all(self, message: dict):
        """
        Broadcast a message to all connected users.

        Args:
            message: The message dictionary to broadcast
        """
        for user_uuid in list(self.active_connections.keys()):
            await self.send_to_user(user_uuid, message)

    async def send_client_alive_update(self, alive_dict: dict):
        """
        Send client status update to all connected users.

        Args:
            alive_dict: Dictionary containing client information
        """
        message = {"type": "alive_update", "data": alive_dict}
        await self.broadcast_to_all(message)


user_websocket_manager = UserWebSocketManager()
