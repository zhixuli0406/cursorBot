"""
Line Messaging API Integration for CursorBot

Supports:
- Text messages
- Rich menus
- Quick replies
- Flex messages
- Image/audio/video messages

Popular in Japan, Taiwan, Thailand, Indonesia
"""

import asyncio
import hashlib
import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class LineStatus(Enum):
    """Line bot connection status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class LineConfig:
    """Line bot configuration."""
    # Channel credentials
    channel_access_token: str = ""
    channel_secret: str = ""
    
    # Webhook settings
    webhook_path: str = "/webhook/line"
    port: int = 8080
    
    # Features
    auto_reply: bool = True
    
    # Rate limits
    message_delay: float = 0.1


@dataclass
class LineUser:
    """Line user information."""
    user_id: str
    display_name: str = ""
    picture_url: str = ""
    status_message: str = ""


@dataclass
class LineMessage:
    """Line message."""
    id: str
    user_id: str
    reply_token: str
    content: str
    timestamp: datetime
    message_type: str = "text"  # text, image, video, audio, file, location, sticker
    source_type: str = "user"  # user, group, room
    group_id: str = ""
    room_id: str = ""


class LineBot:
    """
    Line Messaging API bot.
    
    Requires:
    - Line Developer account
    - Messaging API channel
    - line-bot-sdk package
    """
    
    API_BASE = "https://api.line.me/v2"
    
    def __init__(self, config: LineConfig = None):
        self.config = config or LineConfig(
            channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
            channel_secret=os.getenv("LINE_CHANNEL_SECRET", ""),
        )
        self._status = LineStatus.STOPPED
        self._message_handlers: list[Callable] = []
        self._http_client = None
        self._app = None
        self._server = None
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """Start Line bot."""
        if not self.config.channel_access_token or not self.config.channel_secret:
            logger.error("LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET required")
            self._status = LineStatus.ERROR
            return False
        
        try:
            self._status = LineStatus.STARTING
            
            # Initialize HTTP client
            import httpx
            self._http_client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.config.channel_access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            
            # Start webhook server
            await self._start_webhook_server()
            
            self._status = LineStatus.RUNNING
            logger.info(f"Line bot running on port {self.config.port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Line bot: {e}")
            self._status = LineStatus.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop Line bot."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        self._status = LineStatus.STOPPED
        logger.info("Line bot stopped")
    
    async def _start_webhook_server(self) -> None:
        """Start webhook server for Line events."""
        from aiohttp import web
        
        async def webhook_handler(request: web.Request) -> web.Response:
            """Handle Line webhook events."""
            # Verify signature
            body = await request.read()
            signature = request.headers.get("X-Line-Signature", "")
            
            if not self._verify_signature(body, signature):
                return web.Response(status=403, text="Invalid signature")
            
            # Parse events
            import json
            data = json.loads(body)
            
            for event in data.get("events", []):
                await self._handle_event(event)
            
            return web.Response(status=200, text="OK")
        
        app = web.Application()
        app.router.add_post(self.config.webhook_path, webhook_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, "0.0.0.0", self.config.port)
        await site.start()
        
        self._app = app
    
    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify Line webhook signature."""
        hash_value = hmac.new(
            self.config.channel_secret.encode(),
            body,
            hashlib.sha256,
        ).digest()
        
        import base64
        expected = base64.b64encode(hash_value).decode()
        
        return hmac.compare_digest(signature, expected)
    
    # ============================================
    # Event Handling
    # ============================================
    
    def on_message(self, handler: Callable) -> None:
        """Register message handler."""
        self._message_handlers.append(handler)
    
    async def _handle_event(self, event: dict) -> None:
        """Handle Line event."""
        event_type = event.get("type")
        
        if event_type == "message":
            await self._handle_message_event(event)
        elif event_type == "follow":
            await self._handle_follow_event(event)
        elif event_type == "unfollow":
            logger.info(f"User unfollowed: {event.get('source', {}).get('userId')}")
        elif event_type == "join":
            logger.info(f"Bot joined group/room")
        elif event_type == "leave":
            logger.info(f"Bot left group/room")
    
    async def _handle_message_event(self, event: dict) -> None:
        """Handle message event."""
        message_data = event.get("message", {})
        source = event.get("source", {})
        
        # Create message object
        message = LineMessage(
            id=message_data.get("id", ""),
            user_id=source.get("userId", ""),
            reply_token=event.get("replyToken", ""),
            content=message_data.get("text", ""),
            timestamp=datetime.fromtimestamp(event.get("timestamp", 0) / 1000),
            message_type=message_data.get("type", "text"),
            source_type=source.get("type", "user"),
            group_id=source.get("groupId", ""),
            room_id=source.get("roomId", ""),
        )
        
        # Dispatch to handlers
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    async def _handle_follow_event(self, event: dict) -> None:
        """Handle follow event (user adds bot as friend)."""
        source = event.get("source", {})
        user_id = source.get("userId", "")
        reply_token = event.get("replyToken", "")
        
        if reply_token and self.config.auto_reply:
            await self.reply_message(
                reply_token,
                "歡迎使用 CursorBot! 發送任何訊息開始對話。"
            )
        
        logger.info(f"New follower: {user_id}")
    
    # ============================================
    # Sending Messages
    # ============================================
    
    async def reply_message(self, reply_token: str, text: str) -> bool:
        """
        Reply to a message using reply token.
        
        Args:
            reply_token: Token from the original message
            text: Reply text
        
        Returns:
            True if sent successfully
        """
        try:
            response = await self._http_client.post(
                f"{self.API_BASE}/bot/message/reply",
                json={
                    "replyToken": reply_token,
                    "messages": [{"type": "text", "text": text}],
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Reply error: {response.text}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Reply error: {e}")
            return False
    
    async def push_message(self, user_id: str, text: str) -> bool:
        """
        Send push message to user.
        
        Args:
            user_id: Target user ID
            text: Message text
        
        Returns:
            True if sent successfully
        """
        try:
            response = await self._http_client.post(
                f"{self.API_BASE}/bot/message/push",
                json={
                    "to": user_id,
                    "messages": [{"type": "text", "text": text}],
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Push error: {response.text}")
                return False
            
            await asyncio.sleep(self.config.message_delay)
            return True
            
        except Exception as e:
            logger.error(f"Push error: {e}")
            return False
    
    async def send_image(self, user_id: str, image_url: str, preview_url: str = None) -> bool:
        """Send image message."""
        try:
            response = await self._http_client.post(
                f"{self.API_BASE}/bot/message/push",
                json={
                    "to": user_id,
                    "messages": [{
                        "type": "image",
                        "originalContentUrl": image_url,
                        "previewImageUrl": preview_url or image_url,
                    }],
                },
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Send image error: {e}")
            return False
    
    async def send_quick_reply(
        self,
        reply_token: str,
        text: str,
        items: list[dict],
    ) -> bool:
        """
        Send message with quick reply buttons.
        
        Args:
            reply_token: Reply token
            text: Message text
            items: List of quick reply items
        
        Returns:
            True if sent successfully
        """
        try:
            response = await self._http_client.post(
                f"{self.API_BASE}/bot/message/reply",
                json={
                    "replyToken": reply_token,
                    "messages": [{
                        "type": "text",
                        "text": text,
                        "quickReply": {"items": items},
                    }],
                },
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Quick reply error: {e}")
            return False
    
    async def send_flex_message(
        self,
        user_id: str,
        alt_text: str,
        contents: dict,
    ) -> bool:
        """
        Send Flex Message (rich message format).
        
        Args:
            user_id: Target user ID
            alt_text: Alternative text for notifications
            contents: Flex Message JSON contents
        
        Returns:
            True if sent successfully
        """
        try:
            response = await self._http_client.post(
                f"{self.API_BASE}/bot/message/push",
                json={
                    "to": user_id,
                    "messages": [{
                        "type": "flex",
                        "altText": alt_text,
                        "contents": contents,
                    }],
                },
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Flex message error: {e}")
            return False
    
    # ============================================
    # User Management
    # ============================================
    
    async def get_profile(self, user_id: str) -> Optional[LineUser]:
        """Get user profile."""
        try:
            response = await self._http_client.get(
                f"{self.API_BASE}/bot/profile/{user_id}"
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            return LineUser(
                user_id=data.get("userId", user_id),
                display_name=data.get("displayName", ""),
                picture_url=data.get("pictureUrl", ""),
                status_message=data.get("statusMessage", ""),
            )
            
        except Exception as e:
            logger.error(f"Get profile error: {e}")
            return None
    
    # ============================================
    # Flex Message Builders
    # ============================================
    
    @staticmethod
    def build_bubble(
        header: str = None,
        body: str = None,
        footer: str = None,
    ) -> dict:
        """Build a simple Flex bubble message."""
        contents = {"type": "bubble"}
        
        if header:
            contents["header"] = {
                "type": "box",
                "layout": "vertical",
                "contents": [{"type": "text", "text": header, "weight": "bold", "size": "xl"}],
            }
        
        if body:
            contents["body"] = {
                "type": "box",
                "layout": "vertical",
                "contents": [{"type": "text", "text": body, "wrap": True}],
            }
        
        if footer:
            contents["footer"] = {
                "type": "box",
                "layout": "vertical",
                "contents": [{"type": "text", "text": footer, "color": "#888888", "size": "sm"}],
            }
        
        return contents
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def status(self) -> LineStatus:
        return self._status
    
    @property
    def is_running(self) -> bool:
        return self._status == LineStatus.RUNNING
    
    def get_stats(self) -> dict:
        return {
            "status": self._status.value,
            "port": self.config.port,
            "webhook_path": self.config.webhook_path,
            "handlers": len(self._message_handlers),
        }


# ============================================
# Factory
# ============================================

def create_line_bot(
    channel_access_token: str = None,
    channel_secret: str = None,
    port: int = 8080,
) -> LineBot:
    """
    Create Line bot instance.
    
    Args:
        channel_access_token: Line channel access token
        channel_secret: Line channel secret
        port: Webhook server port
    
    Returns:
        LineBot instance
    """
    config = LineConfig(
        channel_access_token=channel_access_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
        channel_secret=channel_secret or os.getenv("LINE_CHANNEL_SECRET", ""),
        port=port,
    )
    return LineBot(config)


__all__ = [
    "LineStatus",
    "LineConfig",
    "LineUser",
    "LineMessage",
    "LineBot",
    "create_line_bot",
]
