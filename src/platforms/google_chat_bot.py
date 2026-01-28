"""
Google Chat Bot Integration for CursorBot

Uses Google Chat API for Google Workspace integration.
Provides:
- Message receiving and sending
- Space (room) management
- Card message support
- Slash command handling

Setup:
1. Enable Google Chat API in Google Cloud Console
2. Create a service account or OAuth credentials
3. Configure the Chat bot in Google Workspace Admin

Usage:
    from src.platforms.google_chat_bot import GoogleChatBot
    
    bot = GoogleChatBot()
    await bot.start()
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

import httpx

from ..utils.logger import logger

# Try to import Google API client
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    service_account = None
    build = None


# OAuth2 scopes for Google Chat
SCOPES = [
    "https://www.googleapis.com/auth/chat.bot",
    "https://www.googleapis.com/auth/chat.spaces",
    "https://www.googleapis.com/auth/chat.messages",
]


@dataclass
class ChatMessage:
    """Represents a Google Chat message."""
    name: str  # Full resource name
    text: str
    sender_name: str
    sender_email: str = ""
    sender_type: str = "HUMAN"  # HUMAN or BOT
    space_name: str = ""
    space_type: str = ""  # ROOM, DM, etc.
    thread_name: str = ""
    create_time: datetime = None
    annotations: list[dict] = field(default_factory=list)
    attachment: dict = None
    slash_command: dict = None
    
    @property
    def is_dm(self) -> bool:
        return self.space_type == "DM"
    
    @property
    def is_room(self) -> bool:
        return self.space_type == "ROOM"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "text": self.text,
            "sender_name": self.sender_name,
            "sender_email": self.sender_email,
            "sender_type": self.sender_type,
            "space_name": self.space_name,
            "space_type": self.space_type,
            "thread_name": self.thread_name,
            "create_time": self.create_time.isoformat() if self.create_time else None,
        }


@dataclass
class ChatSpace:
    """Represents a Google Chat space (room)."""
    name: str
    display_name: str = ""
    space_type: str = ""
    single_user_bot_dm: bool = False
    threaded: bool = False


@dataclass
class ChatUser:
    """Represents a Google Chat user."""
    name: str
    display_name: str = ""
    email: str = ""
    domain_id: str = ""
    type: str = "HUMAN"


class GoogleChatBot:
    """
    Google Chat bot using Google Chat API.
    
    Supports both service account and OAuth authentication.
    """
    
    def __init__(
        self,
        credentials_file: str = None,
        project_id: str = None,
    ):
        """
        Initialize Google Chat bot.
        
        Args:
            credentials_file: Path to service account JSON or OAuth credentials
            project_id: Google Cloud project ID
        """
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "google"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.credentials_file = credentials_file or os.getenv(
            "GOOGLE_CHAT_CREDENTIALS",
            str(self.data_dir / "chat_service_account.json")
        )
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        
        self._service = None
        self._credentials = None
        self._authenticated = False
        self._running = False
        self._message_handlers: list[Callable] = []
        self._webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """
        Start the Google Chat bot.
        
        Returns:
            True if started successfully
        """
        if self._running:
            return True
        
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API client not installed")
            return False
        
        # Authenticate
        if not await self.authenticate():
            return False
        
        self._running = True
        logger.info("Google Chat bot started")
        return True
    
    async def stop(self) -> None:
        """Stop the Google Chat bot."""
        self._running = False
        logger.info("Google Chat bot stopped")
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Google Chat API.
        
        Returns:
            True if authenticated successfully
        """
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API client not installed")
            return False
        
        try:
            if not os.path.exists(self.credentials_file):
                logger.error(f"Credentials not found: {self.credentials_file}")
                return False
            
            # Load service account credentials
            self._credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=SCOPES,
            )
            
            # Build service
            self._service = build(
                "chat", "v1",
                credentials=self._credentials,
            )
            
            self._authenticated = True
            logger.info("Google Chat authenticated")
            return True
            
        except Exception as e:
            logger.error(f"Google Chat auth failed: {e}")
            return False
    
    @property
    def is_authenticated(self) -> bool:
        return self._authenticated
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    # ============================================
    # Message Handling (Webhook)
    # ============================================
    
    async def handle_webhook(self, event: dict) -> Optional[dict]:
        """
        Handle incoming webhook event from Google Chat.
        
        This should be called from your webhook endpoint.
        
        Args:
            event: The event payload from Google Chat
            
        Returns:
            Response message dict or None
        """
        event_type = event.get("type", "")
        
        if event_type == "MESSAGE":
            return await self._handle_message_event(event)
        elif event_type == "ADDED_TO_SPACE":
            return await self._handle_added_to_space(event)
        elif event_type == "REMOVED_FROM_SPACE":
            return await self._handle_removed_from_space(event)
        elif event_type == "CARD_CLICKED":
            return await self._handle_card_clicked(event)
        
        return None
    
    async def _handle_message_event(self, event: dict) -> Optional[dict]:
        """Handle a MESSAGE event."""
        message_data = event.get("message", {})
        space_data = event.get("space", {})
        user_data = event.get("user", {})
        
        message = ChatMessage(
            name=message_data.get("name", ""),
            text=message_data.get("text", ""),
            sender_name=user_data.get("displayName", ""),
            sender_email=user_data.get("email", ""),
            sender_type=user_data.get("type", "HUMAN"),
            space_name=space_data.get("name", ""),
            space_type=space_data.get("type", ""),
            thread_name=message_data.get("thread", {}).get("name", ""),
            slash_command=message_data.get("slashCommand"),
        )
        
        # Call handlers
        response = None
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(message)
                else:
                    result = handler(message)
                
                if result:
                    response = result
            except Exception as e:
                logger.error(f"Message handler error: {e}")
        
        return response
    
    async def _handle_added_to_space(self, event: dict) -> dict:
        """Handle ADDED_TO_SPACE event."""
        space = event.get("space", {})
        space_type = space.get("type", "")
        
        if space_type == "DM":
            return {
                "text": "Hello! I'm CursorBot. How can I help you today?"
            }
        else:
            return {
                "text": "Thanks for adding me! Use /help to see available commands."
            }
    
    async def _handle_removed_from_space(self, event: dict) -> None:
        """Handle REMOVED_FROM_SPACE event."""
        space = event.get("space", {})
        logger.info(f"Removed from space: {space.get('name')}")
    
    async def _handle_card_clicked(self, event: dict) -> Optional[dict]:
        """Handle CARD_CLICKED event."""
        action = event.get("action", {})
        action_name = action.get("actionMethodName", "")
        parameters = action.get("parameters", [])
        
        logger.debug(f"Card action: {action_name}")
        
        # Return acknowledgment
        return {"text": f"Action '{action_name}' received"}
    
    def on_message(self, handler: Callable) -> None:
        """Register a message handler."""
        self._message_handlers.append(handler)
    
    # ============================================
    # Message Sending
    # ============================================
    
    async def send_message(
        self,
        space_name: str,
        text: str,
        thread_name: str = None,
        cards: list[dict] = None,
    ) -> Optional[dict]:
        """
        Send a message to a space.
        
        Args:
            space_name: Space resource name (e.g., spaces/xxx)
            text: Message text
            thread_name: Thread to reply to (optional)
            cards: Card messages (optional)
            
        Returns:
            Created message or None
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated")
            return None
        
        try:
            body = {}
            
            if text:
                body["text"] = text
            
            if cards:
                body["cards"] = cards
            
            if thread_name:
                body["thread"] = {"name": thread_name}
            
            result = self._service.spaces().messages().create(
                parent=space_name,
                body=body,
            ).execute()
            
            logger.debug(f"Message sent to {space_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    async def send_card(
        self,
        space_name: str,
        card: dict,
        thread_name: str = None,
    ) -> Optional[dict]:
        """
        Send a card message.
        
        Args:
            space_name: Space resource name
            card: Card definition
            thread_name: Thread to reply to
            
        Returns:
            Created message or None
        """
        return await self.send_message(
            space_name=space_name,
            text="",
            thread_name=thread_name,
            cards=[card],
        )
    
    async def send_webhook_message(
        self,
        text: str,
        cards: list[dict] = None,
        thread_key: str = None,
    ) -> bool:
        """
        Send a message via webhook (simpler setup).
        
        Args:
            text: Message text
            cards: Card messages
            thread_key: Thread key for threading
            
        Returns:
            True if sent successfully
        """
        if not self._webhook_url:
            logger.error("Webhook URL not configured")
            return False
        
        try:
            body = {}
            
            if text:
                body["text"] = text
            
            if cards:
                body["cards"] = cards
            
            url = self._webhook_url
            if thread_key:
                url += f"&threadKey={thread_key}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=body)
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False
    
    # ============================================
    # Space Management
    # ============================================
    
    async def list_spaces(self) -> list[ChatSpace]:
        """List all spaces the bot is in."""
        spaces = []
        
        if not self.is_authenticated:
            return spaces
        
        try:
            result = self._service.spaces().list().execute()
            
            for s in result.get("spaces", []):
                spaces.append(ChatSpace(
                    name=s.get("name", ""),
                    display_name=s.get("displayName", ""),
                    space_type=s.get("type", ""),
                    single_user_bot_dm=s.get("singleUserBotDm", False),
                    threaded=s.get("threaded", False),
                ))
            
        except Exception as e:
            logger.error(f"Failed to list spaces: {e}")
        
        return spaces
    
    async def get_space(self, space_name: str) -> Optional[ChatSpace]:
        """Get a specific space."""
        if not self.is_authenticated:
            return None
        
        try:
            result = self._service.spaces().get(name=space_name).execute()
            
            return ChatSpace(
                name=result.get("name", ""),
                display_name=result.get("displayName", ""),
                space_type=result.get("type", ""),
                single_user_bot_dm=result.get("singleUserBotDm", False),
                threaded=result.get("threaded", False),
            )
            
        except Exception as e:
            logger.error(f"Failed to get space: {e}")
            return None
    
    async def list_members(self, space_name: str) -> list[ChatUser]:
        """List members of a space."""
        members = []
        
        if not self.is_authenticated:
            return members
        
        try:
            result = self._service.spaces().members().list(
                parent=space_name
            ).execute()
            
            for m in result.get("memberships", []):
                member = m.get("member", {})
                members.append(ChatUser(
                    name=member.get("name", ""),
                    display_name=member.get("displayName", ""),
                    email=member.get("email", ""),
                    domain_id=member.get("domainId", ""),
                    type=member.get("type", "HUMAN"),
                ))
            
        except Exception as e:
            logger.error(f"Failed to list members: {e}")
        
        return members
    
    # ============================================
    # Card Building Helpers
    # ============================================
    
    @staticmethod
    def build_text_card(
        title: str,
        subtitle: str = "",
        text: str = "",
        buttons: list[dict] = None,
    ) -> dict:
        """
        Build a simple text card.
        
        Args:
            title: Card title
            subtitle: Card subtitle
            text: Card body text
            buttons: List of button definitions
            
        Returns:
            Card definition dict
        """
        sections = []
        
        # Header section
        header = {"title": title}
        if subtitle:
            header["subtitle"] = subtitle
        
        # Text section
        if text:
            sections.append({
                "widgets": [
                    {"textParagraph": {"text": text}}
                ]
            })
        
        # Buttons section
        if buttons:
            button_widgets = []
            for btn in buttons:
                button_widgets.append({
                    "buttons": [{
                        "textButton": {
                            "text": btn.get("text", "Button"),
                            "onClick": btn.get("onClick", {}),
                        }
                    }]
                })
            sections.append({"widgets": button_widgets})
        
        return {
            "header": header,
            "sections": sections,
        }
    
    @staticmethod
    def build_list_card(
        title: str,
        items: list[dict],
    ) -> dict:
        """
        Build a list card.
        
        Args:
            title: Card title
            items: List of items with 'title', 'description', 'icon' keys
            
        Returns:
            Card definition dict
        """
        widgets = []
        
        for item in items:
            widget = {
                "keyValue": {
                    "topLabel": item.get("label", ""),
                    "content": item.get("title", ""),
                    "contentMultiline": True,
                }
            }
            
            if item.get("icon"):
                widget["keyValue"]["icon"] = item["icon"]
            
            if item.get("description"):
                widget["keyValue"]["bottomLabel"] = item["description"]
            
            widgets.append(widget)
        
        return {
            "header": {"title": title},
            "sections": [{"widgets": widgets}],
        }
    
    # ============================================
    # Status
    # ============================================
    
    def get_stats(self) -> dict:
        """Get bot statistics."""
        return {
            "running": self._running,
            "authenticated": self._authenticated,
            "handlers": len(self._message_handlers),
            "webhook_configured": bool(self._webhook_url),
        }


# Global instance
_google_chat_bot: Optional[GoogleChatBot] = None


def get_google_chat_bot() -> GoogleChatBot:
    """Get the global Google Chat bot instance."""
    global _google_chat_bot
    if _google_chat_bot is None:
        _google_chat_bot = GoogleChatBot()
    return _google_chat_bot


__all__ = [
    "GoogleChatBot",
    "ChatMessage",
    "ChatSpace",
    "ChatUser",
    "get_google_chat_bot",
    "GOOGLE_API_AVAILABLE",
]
