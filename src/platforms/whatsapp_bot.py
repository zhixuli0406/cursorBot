"""
WhatsApp Integration for CursorBot

Uses whatsapp-web.js via subprocess bridge or direct API.
Supports:
- Text messages
- Image/audio messages
- Group chats
- Status updates
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from ..utils.logger import logger


class WhatsAppStatus(Enum):
    """WhatsApp connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    QR_READY = "qr_ready"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    ERROR = "error"


@dataclass
class WhatsAppConfig:
    """WhatsApp bot configuration."""
    # Session
    session_path: str = ".whatsapp_session"
    headless: bool = True
    
    # Rate limits
    message_delay: float = 1.0  # Seconds between messages
    max_messages_per_minute: int = 20
    
    # Features
    auto_read_messages: bool = True
    ignore_groups: bool = False
    allowed_numbers: list[str] = field(default_factory=list)
    
    # Bridge settings (for Node.js bridge)
    bridge_port: int = 3000
    bridge_host: str = "localhost"


@dataclass
class WhatsAppMessage:
    """Represents a WhatsApp message."""
    id: str
    chat_id: str
    sender: str
    sender_name: str
    content: str
    timestamp: datetime
    is_group: bool = False
    group_name: str = ""
    media_type: str = ""  # image, video, audio, document
    media_url: str = ""
    quoted_message: Optional["WhatsAppMessage"] = None


@dataclass
class WhatsAppChat:
    """Represents a WhatsApp chat."""
    id: str
    name: str
    is_group: bool
    participants: list[str] = field(default_factory=list)
    last_message: Optional[WhatsAppMessage] = None


class WhatsAppBot:
    """
    WhatsApp bot using whatsapp-web.js bridge.
    
    Architecture:
    - Python: Bot logic, message handling
    - Node.js bridge: WhatsApp Web connection (whatsapp-web.js)
    - Communication via HTTP/WebSocket
    """
    
    def __init__(self, config: WhatsAppConfig = None):
        self.config = config or WhatsAppConfig()
        self._status = WhatsAppStatus.DISCONNECTED
        self._qr_code: str = ""
        self._bridge_process: Optional[subprocess.Popen] = None
        self._message_handlers: list[Callable] = []
        self._http_client = None
        self._ws_client = None
        self._running = False
    
    # ============================================
    # Connection Management
    # ============================================
    
    async def start(self) -> bool:
        """
        Start WhatsApp bot.
        
        Returns:
            True if started successfully
        """
        try:
            self._status = WhatsAppStatus.CONNECTING
            
            # Start Node.js bridge
            if not await self._start_bridge():
                return False
            
            # Wait for connection
            await self._wait_for_ready()
            
            self._running = True
            self._status = WhatsAppStatus.READY
            logger.info("WhatsApp bot started")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WhatsApp bot: {e}")
            self._status = WhatsAppStatus.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop WhatsApp bot."""
        self._running = False
        
        if self._bridge_process:
            self._bridge_process.terminate()
            self._bridge_process = None
        
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        self._status = WhatsAppStatus.DISCONNECTED
        logger.info("WhatsApp bot stopped")
    
    async def _start_bridge(self) -> bool:
        """Start Node.js WhatsApp bridge."""
        bridge_path = Path(__file__).parent / "whatsapp_bridge"
        
        # Check if bridge exists
        if not (bridge_path / "index.js").exists():
            logger.warning("WhatsApp bridge not found, using HTTP API mode")
            return await self._init_http_client()
        
        try:
            self._bridge_process = subprocess.Popen(
                ["node", "index.js"],
                cwd=str(bridge_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={
                    **os.environ,
                    "PORT": str(self.config.bridge_port),
                    "SESSION_PATH": self.config.session_path,
                    "HEADLESS": str(self.config.headless).lower(),
                }
            )
            
            # Wait for bridge to start
            await asyncio.sleep(2)
            
            return await self._init_http_client()
            
        except FileNotFoundError:
            logger.error("Node.js not found. Install Node.js to use WhatsApp bridge.")
            return False
        except Exception as e:
            logger.error(f"Failed to start bridge: {e}")
            return False
    
    async def _init_http_client(self) -> bool:
        """Initialize HTTP client for bridge communication."""
        import httpx
        
        self._http_client = httpx.AsyncClient(
            base_url=f"http://{self.config.bridge_host}:{self.config.bridge_port}",
            timeout=30,
        )
        
        # Test connection
        try:
            response = await self._http_client.get("/status")
            return response.status_code == 200
        except:
            return True  # May not be ready yet
    
    async def _wait_for_ready(self, timeout: int = 120) -> None:
        """Wait for WhatsApp to be ready."""
        start = datetime.now()
        
        while (datetime.now() - start).seconds < timeout:
            try:
                response = await self._http_client.get("/status")
                data = response.json()
                
                status = data.get("status", "")
                
                if status == "ready":
                    self._status = WhatsAppStatus.READY
                    return
                elif status == "qr":
                    self._status = WhatsAppStatus.QR_READY
                    self._qr_code = data.get("qr", "")
                    logger.info("Scan QR code to login to WhatsApp")
                elif status == "authenticated":
                    self._status = WhatsAppStatus.AUTHENTICATED
                
            except Exception:
                pass
            
            await asyncio.sleep(2)
        
        raise TimeoutError("WhatsApp connection timeout")
    
    # ============================================
    # Message Handling
    # ============================================
    
    def on_message(self, handler: Callable) -> None:
        """Register message handler."""
        self._message_handlers.append(handler)
    
    async def _poll_messages(self) -> None:
        """Poll for new messages."""
        while self._running:
            try:
                response = await self._http_client.get("/messages")
                messages = response.json().get("messages", [])
                
                for msg_data in messages:
                    message = self._parse_message(msg_data)
                    
                    if message and self._should_process(message):
                        await self._dispatch_message(message)
                
            except Exception as e:
                logger.error(f"Poll error: {e}")
            
            await asyncio.sleep(1)
    
    def _parse_message(self, data: dict) -> Optional[WhatsAppMessage]:
        """Parse message from bridge response."""
        try:
            return WhatsAppMessage(
                id=data.get("id", ""),
                chat_id=data.get("chatId", ""),
                sender=data.get("sender", ""),
                sender_name=data.get("senderName", ""),
                content=data.get("content", ""),
                timestamp=datetime.fromisoformat(data.get("timestamp", "")),
                is_group=data.get("isGroup", False),
                group_name=data.get("groupName", ""),
                media_type=data.get("mediaType", ""),
                media_url=data.get("mediaUrl", ""),
            )
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    def _should_process(self, message: WhatsAppMessage) -> bool:
        """Check if message should be processed."""
        # Check allowed numbers
        if self.config.allowed_numbers:
            if message.sender not in self.config.allowed_numbers:
                return False
        
        # Check group setting
        if self.config.ignore_groups and message.is_group:
            return False
        
        return True
    
    async def _dispatch_message(self, message: WhatsAppMessage) -> None:
        """Dispatch message to handlers."""
        # Check for commands (starts with /)
        if message.content.startswith("/"):
            handled = await self._handle_command(message)
            if handled:
                return
        
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    async def _handle_command(self, message: WhatsAppMessage) -> bool:
        """Handle command message using unified command handler."""
        from ..core.unified_commands import execute_command, CommandContext
        
        # Parse command and args
        parts = message.content[1:].split()
        if not parts:
            return False
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Create context
        ctx = CommandContext(
            user_id=message.sender,
            user_name=message.sender_name or message.sender,
            platform="whatsapp",
            args=args,
            raw_text=message.content,
        )
        
        # Execute command
        result = await execute_command(command, ctx)
        
        if result:
            await self.send_message(message.chat_id, result.message)
            return True
        
        return False
    
    # ============================================
    # Sending Messages
    # ============================================
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        quote_message_id: str = None,
    ) -> bool:
        """
        Send text message.
        
        Args:
            chat_id: Target chat ID (phone@c.us or group@g.us)
            content: Message content
            quote_message_id: Optional message to quote
        
        Returns:
            True if sent successfully
        """
        try:
            response = await self._http_client.post(
                "/send",
                json={
                    "chatId": chat_id,
                    "content": content,
                    "quoteMessageId": quote_message_id,
                }
            )
            
            if response.status_code == 200:
                await asyncio.sleep(self.config.message_delay)
                return True
            
            logger.error(f"Send failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    async def send_image(
        self,
        chat_id: str,
        image_path: str,
        caption: str = "",
    ) -> bool:
        """Send image message."""
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            import base64
            image_b64 = base64.b64encode(image_data).decode()
            
            response = await self._http_client.post(
                "/send-media",
                json={
                    "chatId": chat_id,
                    "media": image_b64,
                    "mediaType": "image",
                    "caption": caption,
                }
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Send image error: {e}")
            return False
    
    async def send_audio(
        self,
        chat_id: str,
        audio_path: str,
        is_voice_note: bool = True,
    ) -> bool:
        """Send audio message."""
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            import base64
            audio_b64 = base64.b64encode(audio_data).decode()
            
            response = await self._http_client.post(
                "/send-media",
                json={
                    "chatId": chat_id,
                    "media": audio_b64,
                    "mediaType": "audio",
                    "isVoiceNote": is_voice_note,
                }
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            return False
    
    async def send_document(
        self,
        chat_id: str,
        file_path: str,
        filename: str = None,
    ) -> bool:
        """Send document."""
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            import base64
            file_b64 = base64.b64encode(file_data).decode()
            
            response = await self._http_client.post(
                "/send-media",
                json={
                    "chatId": chat_id,
                    "media": file_b64,
                    "mediaType": "document",
                    "filename": filename or os.path.basename(file_path),
                }
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Send document error: {e}")
            return False
    
    # ============================================
    # Chat Management
    # ============================================
    
    async def get_chats(self) -> list[WhatsAppChat]:
        """Get all chats."""
        try:
            response = await self._http_client.get("/chats")
            chats_data = response.json().get("chats", [])
            
            return [
                WhatsAppChat(
                    id=c.get("id", ""),
                    name=c.get("name", ""),
                    is_group=c.get("isGroup", False),
                    participants=c.get("participants", []),
                )
                for c in chats_data
            ]
            
        except Exception as e:
            logger.error(f"Get chats error: {e}")
            return []
    
    async def get_contact_name(self, chat_id: str) -> str:
        """Get contact name by ID."""
        try:
            response = await self._http_client.get(f"/contact/{chat_id}")
            return response.json().get("name", chat_id)
        except:
            return chat_id
    
    # ============================================
    # Status & Info
    # ============================================
    
    @property
    def status(self) -> WhatsAppStatus:
        return self._status
    
    @property
    def qr_code(self) -> str:
        """Get QR code for authentication."""
        return self._qr_code
    
    @property
    def is_ready(self) -> bool:
        return self._status == WhatsAppStatus.READY
    
    def get_stats(self) -> dict:
        return {
            "status": self._status.value,
            "qr_available": bool(self._qr_code),
            "handlers": len(self._message_handlers),
        }


# ============================================
# Helper: Format phone number
# ============================================

def format_phone_number(phone: str) -> str:
    """
    Format phone number for WhatsApp.
    
    Args:
        phone: Phone number (e.g., +1234567890 or 1234567890)
    
    Returns:
        Formatted chat ID (e.g., 1234567890@c.us)
    """
    # Remove non-digits
    digits = "".join(c for c in phone if c.isdigit())
    return f"{digits}@c.us"


def format_group_id(group_id: str) -> str:
    """
    Format group ID for WhatsApp.
    
    Args:
        group_id: Group ID
    
    Returns:
        Formatted group ID (e.g., 123456789@g.us)
    """
    if "@g.us" in group_id:
        return group_id
    return f"{group_id}@g.us"


# ============================================
# Factory
# ============================================

def create_whatsapp_bot(
    session_path: str = ".whatsapp_session",
    allowed_numbers: list[str] = None,
) -> WhatsAppBot:
    """
    Create WhatsApp bot instance.
    
    Args:
        session_path: Path for session data
        allowed_numbers: List of allowed phone numbers
    
    Returns:
        WhatsAppBot instance
    """
    config = WhatsAppConfig(
        session_path=session_path,
        allowed_numbers=allowed_numbers or [],
    )
    return WhatsAppBot(config)


__all__ = [
    "WhatsAppStatus",
    "WhatsAppConfig",
    "WhatsAppMessage",
    "WhatsAppChat",
    "WhatsAppBot",
    "format_phone_number",
    "format_group_id",
    "create_whatsapp_bot",
]
