"""
Channel Routing System for CursorBot

Provides:
- Multi-channel message routing
- Channel-specific configurations
- Agent assignment per channel
- Message filtering and forwarding
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class ChannelType(Enum):
    """Channel types."""
    TELEGRAM_PRIVATE = "telegram_private"
    TELEGRAM_GROUP = "telegram_group"
    TELEGRAM_SUPERGROUP = "telegram_supergroup"
    TELEGRAM_CHANNEL = "telegram_channel"
    DISCORD_DM = "discord_dm"
    DISCORD_SERVER = "discord_server"
    DISCORD_THREAD = "discord_thread"
    API = "api"
    WEBHOOK = "webhook"


@dataclass
class ChannelConfig:
    """Configuration for a specific channel."""
    channel_id: str
    channel_type: ChannelType
    name: str = ""
    enabled: bool = True
    
    # Routing settings
    assigned_agent: Optional[str] = None
    forward_to: list[str] = field(default_factory=list)  # Forward messages to these channels
    
    # Processing settings
    auto_reply: bool = True
    use_ai: bool = True
    use_skills: bool = True
    
    # Filtering
    allowed_commands: set[str] = field(default_factory=set)  # Empty = all
    blocked_commands: set[str] = field(default_factory=set)
    message_filter: Optional[str] = None  # Regex pattern
    
    # Rate limiting
    rate_limit: int = 0  # Messages per minute, 0 = no limit
    cooldown_seconds: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: Optional[datetime] = None
    message_count: int = 0
    
    def should_process(self, message: str, command: str = None) -> bool:
        """Check if message should be processed."""
        if not self.enabled:
            return False
        
        if command:
            if self.blocked_commands and command in self.blocked_commands:
                return False
            if self.allowed_commands and command not in self.allowed_commands:
                return False
        
        if self.message_filter:
            try:
                if not re.search(self.message_filter, message):
                    return False
            except re.error:
                pass
        
        return True
    
    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "channel_type": self.channel_type.value,
            "name": self.name,
            "enabled": self.enabled,
            "assigned_agent": self.assigned_agent,
            "forward_to": self.forward_to,
            "auto_reply": self.auto_reply,
            "message_count": self.message_count,
        }


@dataclass
class RouteRule:
    """Rule for routing messages."""
    name: str
    priority: int = 0
    
    # Matching conditions
    channel_pattern: Optional[str] = None  # Regex for channel_id
    channel_types: list[ChannelType] = field(default_factory=list)
    message_pattern: Optional[str] = None  # Regex for message content
    command_pattern: Optional[str] = None  # Regex for command
    
    # Actions
    target_agent: Optional[str] = None
    forward_channels: list[str] = field(default_factory=list)
    transform: Optional[Callable[[str], str]] = None
    block: bool = False
    
    def matches(
        self,
        channel_id: str,
        channel_type: ChannelType,
        message: str = "",
        command: str = "",
    ) -> bool:
        """Check if rule matches."""
        if self.channel_pattern:
            if not re.match(self.channel_pattern, channel_id):
                return False
        
        if self.channel_types:
            if channel_type not in self.channel_types:
                return False
        
        if self.message_pattern:
            if not re.search(self.message_pattern, message):
                return False
        
        if self.command_pattern:
            if not re.match(self.command_pattern, command):
                return False
        
        return True


class ChannelRouter:
    """
    Routes messages between channels and agents.
    """
    
    def __init__(self):
        self._channels: dict[str, ChannelConfig] = {}
        self._rules: list[RouteRule] = []
        self._handlers: dict[str, Callable] = {}
        self._forwarding_enabled: bool = True
    
    # ============================================
    # Channel Management
    # ============================================
    
    def register_channel(self, config: ChannelConfig) -> None:
        """Register a channel configuration."""
        self._channels[config.channel_id] = config
        logger.info(f"Registered channel: {config.channel_id} ({config.channel_type.value})")
    
    def get_channel(self, channel_id: str) -> Optional[ChannelConfig]:
        """Get channel configuration."""
        return self._channels.get(channel_id)
    
    def update_channel(self, channel_id: str, **kwargs) -> bool:
        """Update channel configuration."""
        if channel_id not in self._channels:
            return False
        
        config = self._channels[channel_id]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return True
    
    def remove_channel(self, channel_id: str) -> bool:
        """Remove a channel."""
        if channel_id in self._channels:
            del self._channels[channel_id]
            return True
        return False
    
    def list_channels(self, channel_type: ChannelType = None) -> list[ChannelConfig]:
        """List all channels, optionally filtered by type."""
        channels = list(self._channels.values())
        if channel_type:
            channels = [c for c in channels if c.channel_type == channel_type]
        return channels
    
    # ============================================
    # Routing Rules
    # ============================================
    
    def add_rule(self, rule: RouteRule) -> None:
        """Add a routing rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added routing rule: {rule.name}")
    
    def remove_rule(self, name: str) -> bool:
        """Remove a routing rule by name."""
        original_len = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) < original_len
    
    def get_matching_rules(
        self,
        channel_id: str,
        channel_type: ChannelType,
        message: str = "",
        command: str = "",
    ) -> list[RouteRule]:
        """Get all rules that match the given criteria."""
        return [
            rule for rule in self._rules
            if rule.matches(channel_id, channel_type, message, command)
        ]
    
    # ============================================
    # Message Routing
    # ============================================
    
    async def route_message(
        self,
        channel_id: str,
        channel_type: ChannelType,
        message: str,
        command: str = "",
        metadata: dict = None,
    ) -> dict:
        """
        Route a message through the routing system.
        
        Args:
            channel_id: Source channel ID
            channel_type: Type of channel
            message: Message content
            command: Command if any
            metadata: Additional metadata
        
        Returns:
            Routing result dict
        """
        result = {
            "processed": False,
            "blocked": False,
            "forwarded_to": [],
            "target_agent": None,
            "transformed_message": message,
        }
        
        # Get or create channel config
        config = self.get_channel(channel_id)
        if not config:
            config = ChannelConfig(
                channel_id=channel_id,
                channel_type=channel_type,
            )
            self.register_channel(config)
        
        # Update activity
        config.last_activity = datetime.now()
        config.message_count += 1
        
        # Check if should process
        if not config.should_process(message, command):
            result["blocked"] = True
            return result
        
        # Apply routing rules
        matching_rules = self.get_matching_rules(channel_id, channel_type, message, command)
        
        for rule in matching_rules:
            if rule.block:
                result["blocked"] = True
                return result
            
            if rule.target_agent:
                result["target_agent"] = rule.target_agent
            
            if rule.forward_channels:
                result["forwarded_to"].extend(rule.forward_channels)
            
            if rule.transform:
                try:
                    result["transformed_message"] = rule.transform(result["transformed_message"])
                except Exception as e:
                    logger.warning(f"Transform error in rule {rule.name}: {e}")
        
        # Apply channel-level settings
        if config.assigned_agent and not result["target_agent"]:
            result["target_agent"] = config.assigned_agent
        
        if config.forward_to and self._forwarding_enabled:
            result["forwarded_to"].extend(config.forward_to)
        
        # Deduplicate forwards
        result["forwarded_to"] = list(set(result["forwarded_to"]))
        
        result["processed"] = True
        return result
    
    async def forward_message(
        self,
        message: str,
        target_channels: list[str],
        source_channel: str = None,
    ) -> dict:
        """
        Forward a message to multiple channels.
        
        Args:
            message: Message to forward
            target_channels: List of target channel IDs
            source_channel: Optional source channel for context
        
        Returns:
            Forwarding result dict
        """
        results = {"success": [], "failed": []}
        
        for channel_id in target_channels:
            handler = self._handlers.get(channel_id)
            if handler:
                try:
                    await handler(message, source_channel)
                    results["success"].append(channel_id)
                except Exception as e:
                    logger.error(f"Forward to {channel_id} failed: {e}")
                    results["failed"].append(channel_id)
            else:
                results["failed"].append(channel_id)
        
        return results
    
    # ============================================
    # Handlers
    # ============================================
    
    def register_handler(self, channel_id: str, handler: Callable) -> None:
        """Register a message handler for a channel."""
        self._handlers[channel_id] = handler
    
    def remove_handler(self, channel_id: str) -> bool:
        """Remove a message handler."""
        if channel_id in self._handlers:
            del self._handlers[channel_id]
            return True
        return False
    
    # ============================================
    # Settings
    # ============================================
    
    def enable_forwarding(self) -> None:
        """Enable message forwarding."""
        self._forwarding_enabled = True
    
    def disable_forwarding(self) -> None:
        """Disable message forwarding."""
        self._forwarding_enabled = False
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_stats(self) -> dict:
        """Get routing statistics."""
        by_type = {}
        total_messages = 0
        
        for config in self._channels.values():
            t = config.channel_type.value
            by_type[t] = by_type.get(t, 0) + 1
            total_messages += config.message_count
        
        return {
            "total_channels": len(self._channels),
            "active_rules": len(self._rules),
            "registered_handlers": len(self._handlers),
            "forwarding_enabled": self._forwarding_enabled,
            "by_type": by_type,
            "total_messages_routed": total_messages,
        }


# ============================================
# Global Instance
# ============================================

_channel_router: Optional[ChannelRouter] = None


def get_channel_router() -> ChannelRouter:
    """Get the global channel router instance."""
    global _channel_router
    if _channel_router is None:
        _channel_router = ChannelRouter()
    return _channel_router


__all__ = [
    "ChannelType",
    "ChannelConfig",
    "RouteRule",
    "ChannelRouter",
    "get_channel_router",
]
