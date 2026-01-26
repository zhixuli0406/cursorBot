"""
WebSocket server for real-time communication
Handles bidirectional communication with clients
"""

import asyncio
import json
from typing import Any, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from ..utils.logger import logger


class ConnectionManager:
    """
    Manages WebSocket connections.
    Handles connection lifecycle and message broadcasting.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._user_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection instance
            user_id: Optional user ID for the connection
        """
        await websocket.accept()
        self.active_connections.add(websocket)

        if user_id:
            self._user_connections[user_id] = websocket

        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
            user_id: Optional user ID for the connection
        """
        self.active_connections.discard(websocket)

        if user_id and user_id in self._user_connections:
            del self._user_connections[user_id]

        logger.info(f"WebSocket disconnected. Remaining: {len(self.active_connections)}")

    async def send_personal(self, message: dict[str, Any], websocket: WebSocket) -> None:
        """
        Send a message to a specific connection.

        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def send_to_user(self, message: dict[str, Any], user_id: int) -> bool:
        """
        Send a message to a specific user.

        Args:
            message: Message to send
            user_id: Target user ID

        Returns:
            True if message sent, False if user not connected
        """
        websocket = self._user_connections.get(user_id)
        if websocket:
            await self.send_personal(message, websocket)
            return True
        return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast
        """
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, user_id: Optional[int] = None):
    """
    Main WebSocket endpoint handler.

    Args:
        websocket: WebSocket connection
        user_id: Optional user ID
    """
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message, user_id)
            except json.JSONDecodeError:
                await manager.send_personal(
                    {"error": "Invalid JSON format"},
                    websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


async def handle_websocket_message(
    websocket: WebSocket,
    message: dict[str, Any],
    user_id: Optional[int] = None,
) -> None:
    """
    Handle incoming WebSocket message.

    Args:
        websocket: Source WebSocket connection
        message: Received message data
        user_id: Optional user ID
    """
    msg_type = message.get("type")

    if msg_type == "ping":
        await manager.send_personal({"type": "pong"}, websocket)

    elif msg_type == "subscribe":
        # Handle subscription to events
        channel = message.get("channel")
        logger.info(f"User {user_id} subscribed to {channel}")
        await manager.send_personal(
            {"type": "subscribed", "channel": channel},
            websocket,
        )

    elif msg_type == "unsubscribe":
        channel = message.get("channel")
        logger.info(f"User {user_id} unsubscribed from {channel}")
        await manager.send_personal(
            {"type": "unsubscribed", "channel": channel},
            websocket,
        )

    else:
        # Echo unknown messages
        await manager.send_personal(
            {"type": "echo", "original": message},
            websocket,
        )


class EventEmitter:
    """
    Event emitter for broadcasting events to WebSocket clients.
    """

    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager

    async def emit(self, event: str, data: Any) -> None:
        """
        Emit an event to all connected clients.

        Args:
            event: Event name
            data: Event data
        """
        message = {
            "type": "event",
            "event": event,
            "data": data,
        }
        await self.manager.broadcast(message)

    async def emit_to_user(self, user_id: int, event: str, data: Any) -> bool:
        """
        Emit an event to a specific user.

        Args:
            user_id: Target user ID
            event: Event name
            data: Event data

        Returns:
            True if event sent
        """
        message = {
            "type": "event",
            "event": event,
            "data": data,
        }
        return await self.manager.send_to_user(message, user_id)


# Global event emitter
event_emitter = EventEmitter(manager)

__all__ = [
    "ConnectionManager",
    "manager",
    "websocket_endpoint",
    "EventEmitter",
    "event_emitter",
]
