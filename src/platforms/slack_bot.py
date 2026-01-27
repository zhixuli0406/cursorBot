"""
Slack Bot Integration for CursorBot

Provides:
- Slack workspace integration
- Message handling
- Slash commands
- Event subscriptions
"""

import asyncio
import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from ..utils.logger import logger


@dataclass
class SlackUser:
    """Slack user representation."""
    user_id: str
    username: str = ""
    display_name: str = ""
    is_bot: bool = False
    team_id: str = ""


@dataclass
class SlackMessage:
    """Slack message representation."""
    ts: str  # Timestamp (message ID)
    channel: str
    user: SlackUser
    text: str
    thread_ts: Optional[str] = None  # For threaded messages
    team: str = ""
    event_type: str = "message"
    raw: dict = field(default_factory=dict)


@dataclass
class SlackConfig:
    """Slack bot configuration."""
    bot_token: str
    signing_secret: str
    app_token: str = ""  # For Socket Mode
    allowed_channels: list[str] = field(default_factory=list)
    allowed_users: list[str] = field(default_factory=list)
    bot_user_id: str = ""


class SlackBot:
    """
    Slack Bot client for CursorBot.
    """
    
    def __init__(self, config: SlackConfig):
        self.config = config
        self._client = None
        self._socket_client = None
        self._message_handlers: list[Callable] = []
        self._command_handlers: dict[str, Callable] = {}
        self._running = False
    
    # ============================================
    # Initialization
    # ============================================
    
    async def start(self) -> None:
        """Start the Slack bot."""
        try:
            from slack_sdk.web.async_client import AsyncWebClient
            from slack_sdk.socket_mode.aiohttp import SocketModeClient
            from slack_sdk.socket_mode.response import SocketModeResponse
            from slack_sdk.socket_mode.request import SocketModeRequest
            
            self._client = AsyncWebClient(token=self.config.bot_token)
            
            # Get bot info
            auth = await self._client.auth_test()
            self.config.bot_user_id = auth["user_id"]
            logger.info(f"Slack bot started as {auth['user']}")
            
            # Socket Mode for events
            if self.config.app_token:
                self._socket_client = SocketModeClient(
                    app_token=self.config.app_token,
                    web_client=self._client,
                )
                
                @self._socket_client.socket_mode_request_listeners.append
                async def handle_socket_request(client: SocketModeClient, req: SocketModeRequest):
                    await self._handle_event(req)
                    await client.send_socket_mode_response(
                        SocketModeResponse(envelope_id=req.envelope_id)
                    )
                
                await self._socket_client.connect()
                self._running = True
                logger.info("Slack Socket Mode connected")
            
        except ImportError:
            logger.error("slack_sdk not installed. Run: pip install slack_sdk")
            raise
        except Exception as e:
            logger.error(f"Slack bot start error: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the Slack bot."""
        self._running = False
        if self._socket_client:
            await self._socket_client.close()
        logger.info("Slack bot stopped")
    
    # ============================================
    # Event Handling
    # ============================================
    
    async def _handle_event(self, request) -> None:
        """Handle incoming Slack event."""
        try:
            if request.type == "events_api":
                event = request.payload.get("event", {})
                event_type = event.get("type")
                
                if event_type == "message":
                    await self._handle_message(event)
                elif event_type == "app_mention":
                    await self._handle_mention(event)
                    
            elif request.type == "slash_commands":
                await self._handle_command(request.payload)
                
        except Exception as e:
            logger.error(f"Event handling error: {e}")
    
    async def _handle_message(self, event: dict) -> None:
        """Handle message event."""
        # Ignore bot messages
        if event.get("bot_id"):
            return
        
        user_id = event.get("user", "")
        channel = event.get("channel", "")
        text = event.get("text", "")
        
        # Check permissions
        if not self._is_allowed(user_id, channel):
            return
        
        # Create message object
        message = SlackMessage(
            ts=event.get("ts", ""),
            channel=channel,
            user=SlackUser(user_id=user_id),
            text=text,
            thread_ts=event.get("thread_ts"),
            team=event.get("team", ""),
            raw=event,
        )
        
        # Call handlers
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
    
    async def _handle_mention(self, event: dict) -> None:
        """Handle @mention event."""
        # Remove bot mention from text
        text = event.get("text", "")
        text = text.replace(f"<@{self.config.bot_user_id}>", "").strip()
        
        event["text"] = text
        await self._handle_message(event)
    
    async def _handle_command(self, payload: dict) -> None:
        """Handle slash command."""
        command = payload.get("command", "").lstrip("/")
        text = payload.get("text", "")
        user_id = payload.get("user_id", "")
        channel = payload.get("channel_id", "")
        
        if command in self._command_handlers:
            handler = self._command_handlers[command]
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Command handler error: {e}")
    
    # ============================================
    # Messaging
    # ============================================
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: str = None,
        blocks: list = None,
    ) -> dict:
        """
        Send a message to a channel.
        
        Args:
            channel: Channel ID or name
            text: Message text
            thread_ts: Thread timestamp (for replies)
            blocks: Slack Block Kit blocks
        
        Returns:
            API response
        """
        try:
            kwargs = {
                "channel": channel,
                "text": text,
            }
            
            if thread_ts:
                kwargs["thread_ts"] = thread_ts
            
            if blocks:
                kwargs["blocks"] = blocks
            
            response = await self._client.chat_postMessage(**kwargs)
            return response.data
            
        except Exception as e:
            logger.error(f"Send message error: {e}")
            raise
    
    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: list = None,
    ) -> dict:
        """Update an existing message."""
        try:
            kwargs = {
                "channel": channel,
                "ts": ts,
                "text": text,
            }
            
            if blocks:
                kwargs["blocks"] = blocks
            
            response = await self._client.chat_update(**kwargs)
            return response.data
            
        except Exception as e:
            logger.error(f"Update message error: {e}")
            raise
    
    async def add_reaction(self, channel: str, ts: str, emoji: str) -> bool:
        """Add a reaction to a message."""
        try:
            await self._client.reactions_add(
                channel=channel,
                timestamp=ts,
                name=emoji,
            )
            return True
        except Exception as e:
            logger.warning(f"Add reaction error: {e}")
            return False
    
    async def upload_file(
        self,
        channels: list[str],
        content: str = None,
        file: str = None,
        filename: str = "file.txt",
        title: str = None,
    ) -> dict:
        """Upload a file."""
        try:
            kwargs = {
                "channels": channels,
                "filename": filename,
            }
            
            if content:
                kwargs["content"] = content
            elif file:
                kwargs["file"] = file
            
            if title:
                kwargs["title"] = title
            
            response = await self._client.files_upload_v2(**kwargs)
            return response.data
            
        except Exception as e:
            logger.error(f"Upload file error: {e}")
            raise
    
    # ============================================
    # User & Channel Info
    # ============================================
    
    async def get_user_info(self, user_id: str) -> Optional[SlackUser]:
        """Get user information."""
        try:
            response = await self._client.users_info(user=user_id)
            user_data = response.data.get("user", {})
            
            return SlackUser(
                user_id=user_id,
                username=user_data.get("name", ""),
                display_name=user_data.get("profile", {}).get("display_name", ""),
                is_bot=user_data.get("is_bot", False),
                team_id=user_data.get("team_id", ""),
            )
        except Exception as e:
            logger.error(f"Get user info error: {e}")
            return None
    
    async def get_channel_info(self, channel_id: str) -> dict:
        """Get channel information."""
        try:
            response = await self._client.conversations_info(channel=channel_id)
            return response.data.get("channel", {})
        except Exception as e:
            logger.error(f"Get channel info error: {e}")
            return {}
    
    # ============================================
    # Handlers
    # ============================================
    
    def on_message(self, handler: Callable) -> None:
        """Register a message handler."""
        self._message_handlers.append(handler)
    
    def on_command(self, command: str, handler: Callable) -> None:
        """Register a slash command handler."""
        self._command_handlers[command] = handler
    
    # ============================================
    # Permissions
    # ============================================
    
    def _is_allowed(self, user_id: str, channel: str) -> bool:
        """Check if user/channel is allowed."""
        if self.config.allowed_users:
            if user_id not in self.config.allowed_users:
                return False
        
        if self.config.allowed_channels:
            if channel not in self.config.allowed_channels:
                return False
        
        return True
    
    # ============================================
    # Request Verification
    # ============================================
    
    def verify_request(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Verify Slack request signature."""
        if abs(time.time() - float(timestamp)) > 60 * 5:
            return False
        
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        my_signature = 'v0=' + hmac.new(
            self.config.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(my_signature, signature)


# ============================================
# Factory
# ============================================

def create_slack_bot(
    bot_token: str = None,
    signing_secret: str = None,
    app_token: str = None,
) -> Optional[SlackBot]:
    """
    Create a Slack bot instance from environment variables.
    
    Args:
        bot_token: Bot OAuth token (or SLACK_BOT_TOKEN env)
        signing_secret: Signing secret (or SLACK_SIGNING_SECRET env)
        app_token: App-level token for Socket Mode (or SLACK_APP_TOKEN env)
    
    Returns:
        SlackBot instance or None if not configured
    """
    import os
    
    bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
    signing_secret = signing_secret or os.getenv("SLACK_SIGNING_SECRET")
    app_token = app_token or os.getenv("SLACK_APP_TOKEN")
    
    if not bot_token or not signing_secret:
        return None
    
    config = SlackConfig(
        bot_token=bot_token,
        signing_secret=signing_secret,
        app_token=app_token,
        allowed_channels=os.getenv("SLACK_ALLOWED_CHANNELS", "").split(","),
        allowed_users=os.getenv("SLACK_ALLOWED_USERS", "").split(","),
    )
    
    return SlackBot(config)


__all__ = [
    "SlackBot",
    "SlackConfig",
    "SlackUser",
    "SlackMessage",
    "create_slack_bot",
]
