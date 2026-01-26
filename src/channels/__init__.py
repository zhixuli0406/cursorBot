"""
Multi-Channel Support for CursorBot
Supports Telegram, Discord, and other platforms

Inspired by ClawdBot's channel architecture
"""

from .base import (
    Channel,
    ChannelType,
    Message,
    User,
    MessageContext,
    Button,
    ButtonRow,
)
from .manager import ChannelManager, get_channel_manager

__all__ = [
    "Channel",
    "ChannelType",
    "Message",
    "User",
    "MessageContext",
    "Button",
    "ButtonRow",
    "ChannelManager",
    "get_channel_manager",
]
