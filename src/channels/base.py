"""
Base Channel Abstraction Layer
Provides unified interface for Telegram, Discord, and other platforms
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Union


class ChannelType(Enum):
    """Supported channel types."""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEBCHAT = "webchat"
    CLI = "cli"


@dataclass
class User:
    """Represents a user across platforms."""
    id: str  # Platform-specific user ID
    username: Optional[str] = None
    display_name: Optional[str] = None
    platform: ChannelType = ChannelType.TELEGRAM
    is_bot: bool = False
    avatar_url: Optional[str] = None
    raw_data: dict = field(default_factory=dict)

    @property
    def mention(self) -> str:
        """Get mention string for user."""
        if self.platform == ChannelType.TELEGRAM:
            return f"@{self.username}" if self.username else self.display_name
        elif self.platform == ChannelType.DISCORD:
            return f"<@{self.id}>"
        return self.display_name or self.username or str(self.id)


@dataclass
class Button:
    """Represents an interactive button."""
    label: str
    callback_data: Optional[str] = None
    url: Optional[str] = None
    style: str = "primary"  # primary, secondary, success, danger, link

    def to_telegram(self):
        """Convert to Telegram InlineKeyboardButton."""
        from telegram import InlineKeyboardButton
        if self.url:
            return InlineKeyboardButton(self.label, url=self.url)
        return InlineKeyboardButton(self.label, callback_data=self.callback_data)

    def to_discord(self):
        """Convert to Discord Button."""
        import discord
        if self.url:
            return discord.ui.Button(label=self.label, url=self.url, style=discord.ButtonStyle.link)
        
        style_map = {
            "primary": discord.ButtonStyle.primary,
            "secondary": discord.ButtonStyle.secondary,
            "success": discord.ButtonStyle.success,
            "danger": discord.ButtonStyle.danger,
        }
        return discord.ui.Button(
            label=self.label,
            custom_id=self.callback_data,
            style=style_map.get(self.style, discord.ButtonStyle.primary)
        )


@dataclass
class ButtonRow:
    """A row of buttons."""
    buttons: list[Button] = field(default_factory=list)

    def add(self, label: str, callback_data: str = None, url: str = None, style: str = "primary"):
        self.buttons.append(Button(label, callback_data, url, style))
        return self


@dataclass
class Attachment:
    """Represents a file attachment."""
    filename: str
    data: bytes
    content_type: str = "application/octet-stream"
    url: Optional[str] = None


@dataclass
class Message:
    """Represents a message across platforms."""
    id: str
    content: str
    author: User
    channel_id: str
    platform: ChannelType
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional fields
    reply_to_id: Optional[str] = None
    attachments: list[Attachment] = field(default_factory=list)
    embeds: list[dict] = field(default_factory=list)
    buttons: list[ButtonRow] = field(default_factory=list)
    
    # Platform-specific raw data
    raw_data: Any = None

    @property
    def has_attachments(self) -> bool:
        return len(self.attachments) > 0

    @property
    def is_command(self) -> bool:
        return self.content.startswith("/") or self.content.startswith("!")


@dataclass
class MessageContext:
    """Context for handling a message."""
    message: Message
    channel: "Channel"
    user: User
    
    # State
    args: list[str] = field(default_factory=list)
    command: Optional[str] = None
    
    # Response tracking
    response_sent: bool = False

    async def reply(
        self,
        content: str,
        buttons: list[ButtonRow] = None,
        embed: dict = None,
        parse_mode: str = "HTML",
    ) -> Message:
        """Reply to the message."""
        return await self.channel.send_message(
            channel_id=self.message.channel_id,
            content=content,
            buttons=buttons,
            embed=embed,
            reply_to=self.message.id,
            parse_mode=parse_mode,
        )

    async def edit_reply(
        self,
        message_id: str,
        content: str,
        buttons: list[ButtonRow] = None,
    ) -> bool:
        """Edit a previous reply."""
        return await self.channel.edit_message(
            channel_id=self.message.channel_id,
            message_id=message_id,
            content=content,
            buttons=buttons,
        )


class Channel(ABC):
    """
    Abstract base class for all channel implementations.
    
    Subclass this to implement Telegram, Discord, etc.
    """

    def __init__(self, channel_type: ChannelType):
        self.channel_type = channel_type
        self._handlers: dict[str, list[Callable]] = {
            "message": [],
            "command": [],
            "button": [],
            "voice": [],
            "image": [],
        }

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if channel is connected."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the channel."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel."""
        pass

    @abstractmethod
    async def send_message(
        self,
        channel_id: str,
        content: str,
        buttons: list[ButtonRow] = None,
        embed: dict = None,
        reply_to: str = None,
        parse_mode: str = "HTML",
    ) -> Message:
        """Send a message."""
        pass

    @abstractmethod
    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        buttons: list[ButtonRow] = None,
    ) -> bool:
        """Edit a message."""
        pass

    @abstractmethod
    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> bool:
        """Delete a message."""
        pass

    def on_message(self, handler: Callable) -> Callable:
        """Register a message handler."""
        self._handlers["message"].append(handler)
        return handler

    def on_command(self, command: str) -> Callable:
        """Register a command handler."""
        def decorator(handler: Callable) -> Callable:
            self._handlers["command"].append((command, handler))
            return handler
        return decorator

    def on_button(self, handler: Callable) -> Callable:
        """Register a button click handler."""
        self._handlers["button"].append(handler)
        return handler

    async def _dispatch_message(self, ctx: MessageContext) -> None:
        """Dispatch message to handlers."""
        # Check for commands first
        if ctx.message.is_command:
            parts = ctx.message.content.split()
            command = parts[0][1:]  # Remove / or !
            ctx.command = command
            ctx.args = parts[1:] if len(parts) > 1 else []

            for cmd, handler in self._handlers["command"]:
                if cmd == command or cmd == "*":
                    await handler(ctx)
                    return

        # Then regular message handlers
        for handler in self._handlers["message"]:
            await handler(ctx)

    async def _dispatch_button(self, callback_data: str, ctx: MessageContext) -> None:
        """Dispatch button click to handlers."""
        for handler in self._handlers["button"]:
            await handler(callback_data, ctx)


__all__ = [
    "Channel",
    "ChannelType",
    "Message",
    "User",
    "MessageContext",
    "Button",
    "ButtonRow",
    "Attachment",
]
