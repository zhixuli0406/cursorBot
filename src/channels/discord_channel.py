"""
Discord Channel Implementation for CursorBot
Provides Discord bot functionality

Requires: pip install discord.py
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Optional

try:
    import discord
    from discord import app_commands
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None

from .base import (
    Channel,
    ChannelType,
    Message,
    User,
    MessageContext,
    Button,
    ButtonRow,
)
from ..utils.logger import logger


def _escape_html_to_markdown(text: str) -> str:
    """Convert HTML formatting to Discord markdown."""
    # Basic HTML to markdown conversion
    text = text.replace("<b>", "**").replace("</b>", "**")
    text = text.replace("<i>", "*").replace("</i>", "*")
    text = text.replace("<code>", "`").replace("</code>", "`")
    text = text.replace("<pre>", "```").replace("</pre>", "```")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    return text


class DiscordButtonView(discord.ui.View if DISCORD_AVAILABLE else object):
    """Discord button view for interactive buttons."""

    def __init__(self, buttons: list[ButtonRow], callback_handler: Callable, timeout: float = 180):
        if not DISCORD_AVAILABLE:
            return
        super().__init__(timeout=timeout)
        self.callback_handler = callback_handler

        for row_idx, row in enumerate(buttons):
            for btn in row.buttons:
                if btn.url:
                    # Link button
                    button = discord.ui.Button(
                        label=btn.label,
                        url=btn.url,
                        style=discord.ButtonStyle.link,
                        row=row_idx,
                    )
                else:
                    # Interactive button
                    style_map = {
                        "primary": discord.ButtonStyle.primary,
                        "secondary": discord.ButtonStyle.secondary,
                        "success": discord.ButtonStyle.success,
                        "danger": discord.ButtonStyle.danger,
                    }
                    button = discord.ui.Button(
                        label=btn.label,
                        custom_id=btn.callback_data,
                        style=style_map.get(btn.style, discord.ButtonStyle.primary),
                        row=row_idx,
                    )
                    button.callback = self._create_callback(btn.callback_data)

                self.add_item(button)

    def _create_callback(self, callback_data: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            if self.callback_handler:
                await self.callback_handler(callback_data, interaction)
        return callback


class DiscordChannel(Channel):
    """
    Discord channel implementation.
    
    Usage:
        channel = DiscordChannel(
            token="your_bot_token",
            allowed_guilds=[123456789],
            allowed_users=[987654321],
        )
        await channel.start()
    """

    def __init__(
        self,
        token: str,
        allowed_guilds: list[int] = None,
        allowed_users: list[int] = None,
        command_prefix: str = "/",
    ):
        if not DISCORD_AVAILABLE:
            raise ImportError("discord.py is not installed. Run: pip install discord.py")

        super().__init__(ChannelType.DISCORD)
        self.token = token
        self.allowed_guilds = set(allowed_guilds or [])
        self.allowed_users = set(allowed_users or [])
        self.command_prefix = command_prefix

        # Create Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        self.bot = commands.Bot(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None,  # We'll implement our own
        )

        self._connected = False
        self._setup_events()

    @property
    def name(self) -> str:
        return "Discord"

    @property
    def is_connected(self) -> bool:
        return self._connected and self.bot.is_ready()

    def _setup_events(self) -> None:
        """Setup Discord event handlers."""

        @self.bot.event
        async def on_ready():
            self._connected = True
            logger.info(f"Discord bot connected as {self.bot.user}")
            logger.info(f"Connected to {len(self.bot.guilds)} guilds")

            # Sync slash commands
            try:
                synced = await self.bot.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")

        @self.bot.event
        async def on_message(message: discord.Message):
            # Ignore bot messages
            if message.author.bot:
                return

            # Check authorization
            if not self._is_authorized(message.author.id, message.guild):
                return

            # Convert to unified Message
            unified_msg = self._convert_message(message)
            user = self._convert_user(message.author)
            ctx = MessageContext(message=unified_msg, channel=self, user=user)

            # Dispatch to handlers
            await self._dispatch_message(ctx)

        @self.bot.event
        async def on_interaction(interaction: discord.Interaction):
            # Handle button interactions
            if interaction.type == discord.InteractionType.component:
                if not self._is_authorized(interaction.user.id, interaction.guild):
                    await interaction.response.send_message(
                        "You are not authorized to use this bot.",
                        ephemeral=True
                    )
                    return

    def _is_authorized(self, user_id: int, guild: Optional[discord.Guild]) -> bool:
        """Check if user is authorized."""
        # If no restrictions, allow all
        if not self.allowed_users and not self.allowed_guilds:
            return True

        # Check user allowlist
        if self.allowed_users and user_id in self.allowed_users:
            return True

        # Check guild allowlist
        if guild and self.allowed_guilds and guild.id in self.allowed_guilds:
            return True

        return False

    def _convert_user(self, discord_user: discord.User) -> User:
        """Convert Discord user to unified User."""
        return User(
            id=str(discord_user.id),
            username=discord_user.name,
            display_name=discord_user.display_name,
            platform=ChannelType.DISCORD,
            is_bot=discord_user.bot,
            avatar_url=str(discord_user.avatar.url) if discord_user.avatar else None,
            raw_data={"discriminator": discord_user.discriminator},
        )

    def _convert_message(self, discord_msg: discord.Message) -> Message:
        """Convert Discord message to unified Message."""
        return Message(
            id=str(discord_msg.id),
            content=discord_msg.content,
            author=self._convert_user(discord_msg.author),
            channel_id=str(discord_msg.channel.id),
            platform=ChannelType.DISCORD,
            timestamp=discord_msg.created_at,
            raw_data=discord_msg,
        )

    async def start(self) -> None:
        """Start the Discord bot."""
        logger.info("Starting Discord bot...")
        try:
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Discord bot error: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Discord bot."""
        logger.info("Stopping Discord bot...")
        self._connected = False
        await self.bot.close()

    async def send_message(
        self,
        channel_id: str,
        content: str,
        buttons: list[ButtonRow] = None,
        embed: dict = None,
        reply_to: str = None,
        parse_mode: str = "HTML",
    ) -> Message:
        """Send a message to a Discord channel."""
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            raise ValueError(f"Channel not found: {channel_id}")

        # Convert HTML to markdown if needed
        if parse_mode == "HTML":
            content = _escape_html_to_markdown(content)

        # Create view with buttons
        view = None
        if buttons:
            view = DiscordButtonView(buttons, self._button_callback)

        # Create embed if provided
        discord_embed = None
        if embed:
            discord_embed = discord.Embed(
                title=embed.get("title"),
                description=embed.get("description"),
                color=embed.get("color", 0x5865F2),
            )
            if embed.get("fields"):
                for field in embed["fields"]:
                    discord_embed.add_field(
                        name=field["name"],
                        value=field["value"],
                        inline=field.get("inline", False),
                    )

        # Get reference message if replying
        reference = None
        if reply_to:
            try:
                ref_msg = await channel.fetch_message(int(reply_to))
                reference = ref_msg
            except:
                pass

        # Send message
        msg = await channel.send(
            content=content,
            embed=discord_embed,
            view=view,
            reference=reference,
        )

        return self._convert_message(msg)

    async def _button_callback(self, callback_data: str, interaction: discord.Interaction):
        """Handle button callback."""
        user = self._convert_user(interaction.user)
        msg = self._convert_message(interaction.message)
        ctx = MessageContext(message=msg, channel=self, user=user)
        await self._dispatch_button(callback_data, ctx)

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        buttons: list[ButtonRow] = None,
    ) -> bool:
        """Edit a Discord message."""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return False

            message = await channel.fetch_message(int(message_id))
            
            # Convert HTML to markdown
            content = _escape_html_to_markdown(content)

            view = None
            if buttons:
                view = DiscordButtonView(buttons, self._button_callback)

            await message.edit(content=content, view=view)
            return True

        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return False

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> bool:
        """Delete a Discord message."""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return False

            message = await channel.fetch_message(int(message_id))
            await message.delete()
            return True

        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    def add_slash_command(
        self,
        name: str,
        description: str,
        callback: Callable,
    ) -> None:
        """Add a slash command."""
        @self.bot.tree.command(name=name, description=description)
        async def command(interaction: discord.Interaction):
            if not self._is_authorized(interaction.user.id, interaction.guild):
                await interaction.response.send_message(
                    "You are not authorized.",
                    ephemeral=True
                )
                return

            await interaction.response.defer()

            user = self._convert_user(interaction.user)
            # Create a pseudo-message for context
            msg = Message(
                id=str(interaction.id),
                content=f"/{name}",
                author=user,
                channel_id=str(interaction.channel_id),
                platform=ChannelType.DISCORD,
                raw_data=interaction,
            )
            ctx = MessageContext(message=msg, channel=self, user=user)
            ctx.command = name

            await callback(ctx, interaction)


# Factory function
def create_discord_channel(
    token: str,
    allowed_guilds: list[int] = None,
    allowed_users: list[int] = None,
) -> Optional[DiscordChannel]:
    """
    Create a Discord channel if discord.py is available.
    
    Returns None if discord.py is not installed.
    """
    if not DISCORD_AVAILABLE:
        logger.warning("discord.py not installed, Discord channel unavailable")
        return None

    return DiscordChannel(
        token=token,
        allowed_guilds=allowed_guilds,
        allowed_users=allowed_users,
    )


__all__ = ["DiscordChannel", "create_discord_channel", "DISCORD_AVAILABLE"]
