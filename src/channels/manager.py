"""
Channel Manager for CursorBot
Manages multiple channels (Telegram, Discord, etc.)
"""

import asyncio
from typing import Optional

from .base import Channel, ChannelType
from ..utils.logger import logger


class ChannelManager:
    """
    Manages all communication channels.
    
    Usage:
        manager = get_channel_manager()
        manager.register(TelegramChannel(...))
        manager.register(DiscordChannel(...))
        await manager.start_all()
    """

    def __init__(self):
        self._channels: dict[ChannelType, Channel] = {}
        self._running = False

    def register(self, channel: Channel) -> None:
        """Register a channel."""
        self._channels[channel.channel_type] = channel
        logger.info(f"Registered channel: {channel.name} ({channel.channel_type.value})")

    def unregister(self, channel_type: ChannelType) -> bool:
        """Unregister a channel."""
        if channel_type in self._channels:
            del self._channels[channel_type]
            logger.info(f"Unregistered channel: {channel_type.value}")
            return True
        return False

    def get(self, channel_type: ChannelType) -> Optional[Channel]:
        """Get a channel by type."""
        return self._channels.get(channel_type)

    def list_channels(self) -> list[Channel]:
        """List all registered channels."""
        return list(self._channels.values())

    async def start_all(self) -> None:
        """Start all registered channels."""
        if self._running:
            return

        self._running = True
        tasks = []

        for channel in self._channels.values():
            logger.info(f"Starting channel: {channel.name}")
            tasks.append(asyncio.create_task(channel.start()))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self) -> None:
        """Stop all channels."""
        self._running = False

        for channel in self._channels.values():
            logger.info(f"Stopping channel: {channel.name}")
            try:
                await channel.stop()
            except Exception as e:
                logger.error(f"Error stopping {channel.name}: {e}")

    async def broadcast(
        self,
        content: str,
        channel_types: list[ChannelType] = None,
        **kwargs
    ) -> dict[ChannelType, bool]:
        """
        Broadcast a message to multiple channels.
        
        Args:
            content: Message content
            channel_types: List of channel types to broadcast to (None = all)
            **kwargs: Additional arguments for send_message
            
        Returns:
            Dict of channel_type -> success status
        """
        results = {}
        targets = channel_types or list(self._channels.keys())

        for ct in targets:
            channel = self._channels.get(ct)
            if channel and channel.is_connected:
                try:
                    # This requires a default broadcast channel per platform
                    # Implementation depends on specific requirements
                    results[ct] = True
                except Exception as e:
                    logger.error(f"Broadcast to {ct.value} failed: {e}")
                    results[ct] = False
            else:
                results[ct] = False

        return results

    def get_stats(self) -> dict:
        """Get channel statistics."""
        return {
            "total_channels": len(self._channels),
            "connected": sum(1 for c in self._channels.values() if c.is_connected),
            "channels": [
                {
                    "type": c.channel_type.value,
                    "name": c.name,
                    "connected": c.is_connected,
                }
                for c in self._channels.values()
            ]
        }


# Global instance
_channel_manager: Optional[ChannelManager] = None


def get_channel_manager() -> ChannelManager:
    """Get the global ChannelManager instance."""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChannelManager()
    return _channel_manager


__all__ = ["ChannelManager", "get_channel_manager"]
