"""
Unified Gateway for CursorBot

Provides:
- Central message hub for multiple platforms
- Unified API for all communication channels
- Message routing and transformation
- Platform abstraction layer
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class Platform(Enum):
    """Supported communication platforms."""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBCHAT = "webchat"
    API = "api"
    WEBHOOK = "webhook"


class MessageType(Enum):
    """Message types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    STICKER = "sticker"
    COMMAND = "command"
    CALLBACK = "callback"


@dataclass
class UnifiedUser:
    """Unified user representation across platforms."""
    platform: Platform
    platform_id: str  # Original ID on the platform
    username: str = ""
    display_name: str = ""
    is_bot: bool = False
    metadata: dict = field(default_factory=dict)
    
    @property
    def unified_id(self) -> str:
        """Get unified user ID."""
        return f"{self.platform.value}:{self.platform_id}"


@dataclass
class UnifiedMessage:
    """Unified message representation across platforms."""
    id: str
    platform: Platform
    message_type: MessageType
    content: str
    sender: UnifiedUser
    chat_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional fields
    reply_to: Optional[str] = None
    attachments: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    # Platform-specific raw data
    raw: Any = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "type": self.message_type.value,
            "content": self.content,
            "sender": {
                "id": self.sender.unified_id,
                "username": self.sender.username,
                "display_name": self.sender.display_name,
            },
            "chat_id": self.chat_id,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "attachments": self.attachments,
        }


@dataclass
class OutgoingMessage:
    """Message to be sent through the gateway."""
    chat_id: str
    content: str
    platform: Optional[Platform] = None  # None = all platforms
    message_type: MessageType = MessageType.TEXT
    reply_to: Optional[str] = None
    attachments: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class PlatformAdapter(ABC):
    """Base class for platform adapters."""
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Get platform type."""
        pass
    
    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message through this platform."""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[UnifiedUser]:
        """Get user information."""
        pass
    
    async def start(self) -> None:
        """Start the adapter (optional)."""
        pass
    
    async def stop(self) -> None:
        """Stop the adapter (optional)."""
        pass


class Gateway:
    """
    Unified gateway for managing multiple communication platforms.
    """
    
    def __init__(self):
        self._adapters: dict[Platform, PlatformAdapter] = {}
        self._message_handlers: list[Callable] = []
        self._middleware: list[Callable] = []
        self._running: bool = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
        }
    
    # ============================================
    # Adapter Management
    # ============================================
    
    def register_adapter(self, adapter: PlatformAdapter) -> None:
        """Register a platform adapter."""
        self._adapters[adapter.platform] = adapter
        logger.info(f"Gateway: Registered adapter for {adapter.platform.value}")
    
    def unregister_adapter(self, platform: Platform) -> None:
        """Unregister a platform adapter."""
        if platform in self._adapters:
            del self._adapters[platform]
            logger.info(f"Gateway: Unregistered adapter for {platform.value}")
    
    def get_adapter(self, platform: Platform) -> Optional[PlatformAdapter]:
        """Get adapter for a platform."""
        return self._adapters.get(platform)
    
    def list_adapters(self) -> list[Platform]:
        """List registered adapters."""
        return list(self._adapters.keys())
    
    # ============================================
    # Message Handling
    # ============================================
    
    def on_message(self, handler: Callable) -> None:
        """Register a message handler."""
        self._message_handlers.append(handler)
    
    def use_middleware(self, middleware: Callable) -> None:
        """Add middleware for message processing."""
        self._middleware.append(middleware)
    
    async def receive_message(self, message: UnifiedMessage) -> None:
        """Process an incoming message."""
        self._stats["messages_received"] += 1
        
        # Apply middleware
        for mw in self._middleware:
            try:
                message = await mw(message)
                if message is None:
                    return  # Message filtered out
            except Exception as e:
                logger.error(f"Middleware error: {e}")
        
        # Call handlers
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                self._stats["errors"] += 1
    
    async def send_message(self, message: OutgoingMessage) -> dict:
        """
        Send a message through the gateway.
        
        Args:
            message: Message to send
        
        Returns:
            Results dict with success/failure per platform
        """
        results = {"success": [], "failed": []}
        
        # Determine target platforms
        if message.platform:
            platforms = [message.platform]
        else:
            platforms = list(self._adapters.keys())
        
        # Send to each platform
        for platform in platforms:
            adapter = self._adapters.get(platform)
            if not adapter:
                results["failed"].append((platform.value, "No adapter"))
                continue
            
            try:
                success = await adapter.send_message(message)
                if success:
                    results["success"].append(platform.value)
                    self._stats["messages_sent"] += 1
                else:
                    results["failed"].append((platform.value, "Send failed"))
            except Exception as e:
                results["failed"].append((platform.value, str(e)))
                self._stats["errors"] += 1
        
        return results
    
    async def broadcast(self, content: str, **kwargs) -> dict:
        """Broadcast a message to all platforms."""
        message = OutgoingMessage(
            chat_id=kwargs.get("chat_id", "broadcast"),
            content=content,
            platform=None,
            **kwargs,
        )
        return await self.send_message(message)
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> None:
        """Start the gateway and all adapters."""
        logger.info("Gateway starting...")
        
        for platform, adapter in self._adapters.items():
            try:
                await adapter.start()
                logger.info(f"Gateway: Started {platform.value} adapter")
            except Exception as e:
                logger.error(f"Failed to start {platform.value} adapter: {e}")
        
        self._running = True
        logger.info("Gateway started")
    
    async def stop(self) -> None:
        """Stop the gateway and all adapters."""
        logger.info("Gateway stopping...")
        self._running = False
        
        for platform, adapter in self._adapters.items():
            try:
                await adapter.stop()
            except Exception as e:
                logger.error(f"Error stopping {platform.value} adapter: {e}")
        
        logger.info("Gateway stopped")
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_stats(self) -> dict:
        """Get gateway statistics."""
        return {
            **self._stats,
            "adapters": [p.value for p in self._adapters.keys()],
            "handlers": len(self._message_handlers),
            "middleware": len(self._middleware),
            "running": self._running,
        }


# ============================================
# Global Instance
# ============================================

_gateway: Optional[Gateway] = None


def get_gateway() -> Gateway:
    """Get the global gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = Gateway()
    return _gateway


__all__ = [
    "Platform",
    "MessageType",
    "UnifiedUser",
    "UnifiedMessage",
    "OutgoingMessage",
    "PlatformAdapter",
    "Gateway",
    "get_gateway",
]
