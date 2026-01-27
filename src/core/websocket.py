"""
WebSocket Support for CursorBot

Provides:
- Real-time bidirectional communication
- Client connection management
- Message broadcasting
- Event subscription system
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Set
from weakref import WeakSet

from ..utils.logger import logger


class WSMessageType(Enum):
    """WebSocket message types."""
    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    MESSAGE = "message"
    PING = "ping"
    AUTH = "auth"
    
    # Server -> Client
    EVENT = "event"
    RESPONSE = "response"
    ERROR = "error"
    PONG = "pong"
    CONNECTED = "connected"


@dataclass
class WSMessage:
    """WebSocket message structure."""
    type: WSMessageType
    data: Any = None
    channel: str = "default"
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = ""
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "channel": self.channel,
            "timestamp": self.timestamp.isoformat(),
            "id": self.id,
        })
    
    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        parsed = json.loads(data)
        return cls(
            type=WSMessageType(parsed.get("type", "message")),
            data=parsed.get("data"),
            channel=parsed.get("channel", "default"),
            id=parsed.get("id", ""),
        )


@dataclass
class WSClient:
    """Represents a WebSocket client."""
    client_id: str
    websocket: Any  # The actual websocket connection
    user_id: Optional[int] = None
    subscriptions: Set[str] = field(default_factory=set)
    authenticated: bool = False
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    async def send(self, message: WSMessage) -> bool:
        """Send a message to this client."""
        try:
            await self.websocket.send_text(message.to_json())
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client {self.client_id}: {e}")
            return False
    
    async def send_json(self, data: dict) -> bool:
        """Send JSON data to this client."""
        try:
            await self.websocket.send_json(data)
            return True
        except Exception:
            return False


class WebSocketManager:
    """
    Manages WebSocket connections and messaging.
    """
    
    def __init__(self):
        self._clients: dict[str, WSClient] = {}
        self._channels: dict[str, Set[str]] = {}  # channel -> client_ids
        self._event_handlers: dict[str, list[Callable]] = {}
        self._auth_handler: Optional[Callable] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running: bool = False
    
    # ============================================
    # Connection Management
    # ============================================
    
    async def connect(
        self,
        websocket: Any,
        client_id: str,
        user_id: int = None,
    ) -> WSClient:
        """
        Handle a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            client_id: Unique client identifier
            user_id: Optional user ID
        
        Returns:
            WSClient instance
        """
        client = WSClient(
            client_id=client_id,
            websocket=websocket,
            user_id=user_id,
        )
        
        self._clients[client_id] = client
        
        # Send connected message
        await client.send(WSMessage(
            type=WSMessageType.CONNECTED,
            data={"client_id": client_id},
        ))
        
        logger.info(f"WebSocket client connected: {client_id}")
        return client
    
    async def disconnect(self, client_id: str) -> None:
        """Handle client disconnection."""
        if client_id in self._clients:
            client = self._clients[client_id]
            
            # Remove from all channels
            for channel in list(client.subscriptions):
                await self.unsubscribe(client_id, channel)
            
            del self._clients[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    def get_client(self, client_id: str) -> Optional[WSClient]:
        """Get a client by ID."""
        return self._clients.get(client_id)
    
    def get_clients_by_user(self, user_id: int) -> list[WSClient]:
        """Get all clients for a user."""
        return [c for c in self._clients.values() if c.user_id == user_id]
    
    # ============================================
    # Channel Subscriptions
    # ============================================
    
    async def subscribe(self, client_id: str, channel: str) -> bool:
        """Subscribe a client to a channel."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        client.subscriptions.add(channel)
        
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(client_id)
        
        logger.debug(f"Client {client_id} subscribed to {channel}")
        return True
    
    async def unsubscribe(self, client_id: str, channel: str) -> bool:
        """Unsubscribe a client from a channel."""
        client = self.get_client(client_id)
        if not client:
            return False
        
        client.subscriptions.discard(channel)
        
        if channel in self._channels:
            self._channels[channel].discard(client_id)
            if not self._channels[channel]:
                del self._channels[channel]
        
        logger.debug(f"Client {client_id} unsubscribed from {channel}")
        return True
    
    def get_channel_clients(self, channel: str) -> list[WSClient]:
        """Get all clients subscribed to a channel."""
        client_ids = self._channels.get(channel, set())
        return [self._clients[cid] for cid in client_ids if cid in self._clients]
    
    # ============================================
    # Messaging
    # ============================================
    
    async def send_to_client(self, client_id: str, message: WSMessage) -> bool:
        """Send a message to a specific client."""
        client = self.get_client(client_id)
        if client:
            return await client.send(message)
        return False
    
    async def send_to_user(self, user_id: int, message: WSMessage) -> int:
        """Send a message to all clients of a user."""
        clients = self.get_clients_by_user(user_id)
        success = 0
        for client in clients:
            if await client.send(message):
                success += 1
        return success
    
    async def broadcast(
        self,
        message: WSMessage,
        channel: str = None,
        exclude: set[str] = None,
    ) -> int:
        """
        Broadcast a message.
        
        Args:
            message: Message to send
            channel: Channel to broadcast to (None = all clients)
            exclude: Client IDs to exclude
        
        Returns:
            Number of successful sends
        """
        exclude = exclude or set()
        
        if channel:
            clients = self.get_channel_clients(channel)
        else:
            clients = list(self._clients.values())
        
        success = 0
        for client in clients:
            if client.client_id not in exclude:
                if await client.send(message):
                    success += 1
        
        return success
    
    async def publish_event(
        self,
        event_name: str,
        data: Any,
        channel: str = "events",
    ) -> int:
        """Publish an event to subscribers."""
        message = WSMessage(
            type=WSMessageType.EVENT,
            data={"event": event_name, "payload": data},
            channel=channel,
        )
        return await self.broadcast(message, channel)
    
    # ============================================
    # Message Handling
    # ============================================
    
    async def handle_message(self, client_id: str, raw_message: str) -> Optional[WSMessage]:
        """
        Handle an incoming message from a client.
        
        Args:
            client_id: Source client ID
            raw_message: Raw message string
        
        Returns:
            Response message if any
        """
        client = self.get_client(client_id)
        if not client:
            return None
        
        client.last_activity = datetime.now()
        
        try:
            message = WSMessage.from_json(raw_message)
        except Exception as e:
            return WSMessage(
                type=WSMessageType.ERROR,
                data={"error": "Invalid message format"},
            )
        
        # Handle by type
        if message.type == WSMessageType.PING:
            return WSMessage(type=WSMessageType.PONG)
        
        elif message.type == WSMessageType.SUBSCRIBE:
            channel = message.data.get("channel") if isinstance(message.data, dict) else message.data
            await self.subscribe(client_id, channel)
            return WSMessage(
                type=WSMessageType.RESPONSE,
                data={"subscribed": channel},
            )
        
        elif message.type == WSMessageType.UNSUBSCRIBE:
            channel = message.data.get("channel") if isinstance(message.data, dict) else message.data
            await self.unsubscribe(client_id, channel)
            return WSMessage(
                type=WSMessageType.RESPONSE,
                data={"unsubscribed": channel},
            )
        
        elif message.type == WSMessageType.AUTH:
            if self._auth_handler:
                try:
                    result = await self._auth_handler(client, message.data)
                    client.authenticated = result
                    return WSMessage(
                        type=WSMessageType.RESPONSE,
                        data={"authenticated": result},
                    )
                except Exception as e:
                    return WSMessage(
                        type=WSMessageType.ERROR,
                        data={"error": str(e)},
                    )
        
        elif message.type == WSMessageType.MESSAGE:
            # Trigger event handlers
            await self._trigger_handlers("message", client, message)
        
        return None
    
    # ============================================
    # Event Handlers
    # ============================================
    
    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable = None) -> None:
        """Remove an event handler."""
        if event in self._event_handlers:
            if handler:
                self._event_handlers[event] = [
                    h for h in self._event_handlers[event] if h != handler
                ]
            else:
                del self._event_handlers[event]
    
    async def _trigger_handlers(self, event: str, *args, **kwargs) -> None:
        """Trigger all handlers for an event."""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"WebSocket handler error for {event}: {e}")
    
    def set_auth_handler(self, handler: Callable) -> None:
        """Set the authentication handler."""
        self._auth_handler = handler
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_stats(self) -> dict:
        """Get WebSocket statistics."""
        return {
            "connected_clients": len(self._clients),
            "active_channels": len(self._channels),
            "authenticated_clients": sum(1 for c in self._clients.values() if c.authenticated),
            "total_subscriptions": sum(len(c.subscriptions) for c in self._clients.values()),
        }
    
    def get_client_list(self) -> list[dict]:
        """Get list of connected clients."""
        return [
            {
                "client_id": c.client_id,
                "user_id": c.user_id,
                "authenticated": c.authenticated,
                "subscriptions": list(c.subscriptions),
                "connected_at": c.connected_at.isoformat(),
            }
            for c in self._clients.values()
        ]


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
    "WSMessageType",
    "WSMessage",
    "WSClient",
    "WebSocketManager",
    "get_websocket_manager",
]
