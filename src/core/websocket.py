"""
WebSocket Support for CursorBot

Provides:
- Real-time bidirectional communication
- Event broadcasting
- Client management
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Set

from ..utils.logger import logger


class WSEventType(Enum):
    """WebSocket event types."""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    MESSAGE = "message"
    TASK_UPDATE = "task_update"
    NOTIFICATION = "notification"
    STATUS = "status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class WSClient:
    """Represents a WebSocket client."""
    client_id: str
    user_id: Optional[int] = None
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    subscriptions: Set[str] = field(default_factory=set)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "subscriptions": list(self.subscriptions),
        }


@dataclass
class WSMessage:
    """WebSocket message structure."""
    event: WSEventType
    data: Any
    client_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        return json.dumps({
            "event": self.event.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "WSMessage":
        data = json.loads(json_str)
        return cls(
            event=WSEventType(data.get("event", "message")),
            data=data.get("data"),
        )


class WebSocketManager:
    """
    Manages WebSocket connections and messaging.
    """
    
    def __init__(self):
        self._clients: dict[str, WSClient] = {}
        self._user_clients: dict[int, set[str]] = {}  # user_id -> client_ids
        self._handlers: dict[WSEventType, list[Callable]] = {}
        self._channels: dict[str, set[str]] = {}  # channel -> client_ids
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    # ============================================
    # Client Management
    # ============================================
    
    def register_client(
        self,
        client_id: str,
        user_id: int = None,
        metadata: dict = None,
    ) -> WSClient:
        """Register a new WebSocket client."""
        client = WSClient(
            client_id=client_id,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._clients[client_id] = client
        
        if user_id:
            if user_id not in self._user_clients:
                self._user_clients[user_id] = set()
            self._user_clients[user_id].add(client_id)
        
        logger.info(f"WebSocket client registered: {client_id}")
        self._trigger_event(WSEventType.CONNECT, {"client_id": client_id})
        
        return client
    
    def unregister_client(self, client_id: str) -> bool:
        """Unregister a WebSocket client."""
        if client_id not in self._clients:
            return False
        
        client = self._clients[client_id]
        
        # Remove from user mapping
        if client.user_id and client.user_id in self._user_clients:
            self._user_clients[client.user_id].discard(client_id)
        
        # Remove from channels
        for channel_clients in self._channels.values():
            channel_clients.discard(client_id)
        
        del self._clients[client_id]
        
        logger.info(f"WebSocket client unregistered: {client_id}")
        self._trigger_event(WSEventType.DISCONNECT, {"client_id": client_id})
        
        return True
    
    def get_client(self, client_id: str) -> Optional[WSClient]:
        """Get a client by ID."""
        return self._clients.get(client_id)
    
    def get_user_clients(self, user_id: int) -> list[WSClient]:
        """Get all clients for a user."""
        client_ids = self._user_clients.get(user_id, set())
        return [self._clients[cid] for cid in client_ids if cid in self._clients]
    
    # ============================================
    # Channel Subscriptions
    # ============================================
    
    def subscribe(self, client_id: str, channel: str) -> bool:
        """Subscribe a client to a channel."""
        if client_id not in self._clients:
            return False
        
        if channel not in self._channels:
            self._channels[channel] = set()
        
        self._channels[channel].add(client_id)
        self._clients[client_id].subscriptions.add(channel)
        
        return True
    
    def unsubscribe(self, client_id: str, channel: str) -> bool:
        """Unsubscribe a client from a channel."""
        if client_id not in self._clients:
            return False
        
        if channel in self._channels:
            self._channels[channel].discard(client_id)
        
        self._clients[client_id].subscriptions.discard(channel)
        
        return True
    
    # ============================================
    # Messaging
    # ============================================
    
    async def send_to_client(
        self,
        client_id: str,
        event: WSEventType,
        data: Any,
    ) -> bool:
        """Send message to a specific client."""
        if client_id not in self._clients:
            return False
        
        message = WSMessage(event=event, data=data, client_id=client_id)
        await self._message_queue.put(("client", client_id, message))
        
        return True
    
    async def send_to_user(
        self,
        user_id: int,
        event: WSEventType,
        data: Any,
    ) -> int:
        """Send message to all clients of a user."""
        clients = self.get_user_clients(user_id)
        count = 0
        
        for client in clients:
            await self.send_to_client(client.client_id, event, data)
            count += 1
        
        return count
    
    async def broadcast(
        self,
        event: WSEventType,
        data: Any,
        exclude: set[str] = None,
    ) -> int:
        """Broadcast message to all clients."""
        exclude = exclude or set()
        count = 0
        
        for client_id in self._clients:
            if client_id not in exclude:
                await self.send_to_client(client_id, event, data)
                count += 1
        
        return count
    
    async def broadcast_to_channel(
        self,
        channel: str,
        event: WSEventType,
        data: Any,
        exclude: set[str] = None,
    ) -> int:
        """Broadcast message to a channel."""
        if channel not in self._channels:
            return 0
        
        exclude = exclude or set()
        count = 0
        
        for client_id in self._channels[channel]:
            if client_id not in exclude:
                await self.send_to_client(client_id, event, data)
                count += 1
        
        return count
    
    # ============================================
    # Event Handlers
    # ============================================
    
    def on_event(self, event_type: WSEventType, handler: Callable) -> None:
        """Register an event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def _trigger_event(self, event_type: WSEventType, data: Any) -> None:
        """Trigger event handlers."""
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data))
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    async def handle_message(self, client_id: str, raw_message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            message = WSMessage.from_json(raw_message)
            message.client_id = client_id
            
            # Handle ping
            if message.event == WSEventType.PING:
                await self.send_to_client(client_id, WSEventType.PONG, {})
                if client_id in self._clients:
                    self._clients[client_id].last_ping = datetime.now()
                return
            
            # Trigger handlers
            self._trigger_event(message.event, {
                "client_id": client_id,
                "data": message.data,
            })
            
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await self.send_to_client(client_id, WSEventType.ERROR, {
                "message": str(e),
            })
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_stats(self) -> dict:
        """Get WebSocket statistics."""
        return {
            "total_clients": len(self._clients),
            "unique_users": len(self._user_clients),
            "channels": len(self._channels),
            "subscriptions": sum(len(c.subscriptions) for c in self._clients.values()),
        }
    
    def list_clients(self) -> list[dict]:
        """List all connected clients."""
        return [c.to_dict() for c in self._clients.values()]


# ============================================
# Global Instance
# ============================================

_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


__all__ = [
    "WSEventType",
    "WSClient",
    "WSMessage",
    "WebSocketManager",
    "get_websocket_manager",
]
