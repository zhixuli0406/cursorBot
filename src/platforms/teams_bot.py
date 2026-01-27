"""
Microsoft Teams Integration for CursorBot

Uses Bot Framework SDK for Teams integration.
Supports:
- Direct messages
- Channel messages
- Adaptive cards
- File attachments
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class TeamsStatus(Enum):
    """Teams bot connection status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class TeamsConfig:
    """MS Teams bot configuration."""
    # Azure AD App Registration
    app_id: str = ""
    app_password: str = ""
    
    # Bot settings
    bot_name: str = "CursorBot"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 3978
    
    # Features
    allowed_tenants: list[str] = field(default_factory=list)
    allowed_users: list[str] = field(default_factory=list)


@dataclass
class TeamsUser:
    """Teams user information."""
    id: str
    name: str
    email: str = ""
    tenant_id: str = ""
    aad_object_id: str = ""


@dataclass
class TeamsMessage:
    """Teams message."""
    id: str
    conversation_id: str
    user: TeamsUser
    content: str
    timestamp: datetime
    channel_id: str = ""
    team_id: str = ""
    is_group: bool = False
    mentions: list[str] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)


class TeamsBot:
    """
    Microsoft Teams bot using Bot Framework.
    
    Requires:
    - Azure AD App Registration
    - Bot Framework registration
    - botbuilder-core package
    """
    
    def __init__(self, config: TeamsConfig = None):
        self.config = config or TeamsConfig(
            app_id=os.getenv("TEAMS_APP_ID", ""),
            app_password=os.getenv("TEAMS_APP_PASSWORD", ""),
        )
        self._status = TeamsStatus.STOPPED
        self._message_handlers: list[Callable] = []
        self._adapter = None
        self._bot = None
        self._app = None
        self._server = None
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """Start Teams bot."""
        if not self.config.app_id or not self.config.app_password:
            logger.error("TEAMS_APP_ID and TEAMS_APP_PASSWORD required")
            return False
        
        try:
            self._status = TeamsStatus.STARTING
            
            # Initialize Bot Framework
            await self._init_bot_framework()
            
            # Start HTTP server
            await self._start_server()
            
            self._status = TeamsStatus.RUNNING
            logger.info(f"Teams bot running on port {self.config.port}")
            
            return True
            
        except ImportError:
            logger.error("botbuilder-core not installed. Run: pip install botbuilder-core")
            self._status = TeamsStatus.ERROR
            return False
        except Exception as e:
            logger.error(f"Failed to start Teams bot: {e}")
            self._status = TeamsStatus.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop Teams bot."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        self._status = TeamsStatus.STOPPED
        logger.info("Teams bot stopped")
    
    async def _init_bot_framework(self) -> None:
        """Initialize Bot Framework adapter."""
        from botbuilder.core import (
            BotFrameworkAdapter,
            BotFrameworkAdapterSettings,
            TurnContext,
        )
        from botbuilder.schema import Activity, ActivityTypes
        
        # Create adapter settings
        settings = BotFrameworkAdapterSettings(
            app_id=self.config.app_id,
            app_password=self.config.app_password,
        )
        
        # Create adapter
        self._adapter = BotFrameworkAdapter(settings)
        
        # Error handler
        async def on_error(context: TurnContext, error: Exception):
            logger.error(f"Teams bot error: {error}")
            await context.send_activity("Sorry, an error occurred.")
        
        self._adapter.on_turn_error = on_error
        
        # Create bot logic
        class CursorTeamsBot:
            def __init__(self, parent):
                self.parent = parent
            
            async def on_turn(self, turn_context: TurnContext):
                if turn_context.activity.type == ActivityTypes.message:
                    await self.parent._handle_message(turn_context)
                elif turn_context.activity.type == ActivityTypes.conversation_update:
                    await self._handle_conversation_update(turn_context)
            
            async def _handle_conversation_update(self, turn_context: TurnContext):
                for member in turn_context.activity.members_added or []:
                    if member.id != turn_context.activity.recipient.id:
                        await turn_context.send_activity(
                            f"Hello! I'm {self.parent.config.bot_name}. "
                            "How can I help you today?"
                        )
        
        self._bot = CursorTeamsBot(self)
    
    async def _start_server(self) -> None:
        """Start HTTP server for Bot Framework messages."""
        from aiohttp import web
        
        async def messages(request: web.Request) -> web.Response:
            """Handle incoming messages from Bot Framework."""
            if "application/json" in request.headers.get("Content-Type", ""):
                body = await request.json()
            else:
                return web.Response(status=415)
            
            from botbuilder.schema import Activity
            activity = Activity().deserialize(body)
            auth_header = request.headers.get("Authorization", "")
            
            response = await self._adapter.process_activity(
                activity, auth_header, self._bot.on_turn
            )
            
            if response:
                return web.json_response(data=response.body, status=response.status)
            return web.Response(status=201)
        
        app = web.Application()
        app.router.add_post("/api/messages", messages)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        self._server = await asyncio.start_server(
            lambda r, w: None,  # Placeholder
            self.config.host,
            self.config.port,
        )
        
        # Actually use aiohttp server
        site = web.TCPSite(runner, self.config.host, self.config.port)
        await site.start()
    
    # ============================================
    # Message Handling
    # ============================================
    
    def on_message(self, handler: Callable) -> None:
        """Register message handler."""
        self._message_handlers.append(handler)
    
    async def _handle_message(self, turn_context) -> None:
        """Handle incoming message."""
        from botbuilder.core import TurnContext
        
        activity = turn_context.activity
        
        # Check permissions
        if not self._check_permissions(activity):
            await turn_context.send_activity(
                "Sorry, you don't have permission to use this bot."
            )
            return
        
        # Create message object
        message = TeamsMessage(
            id=activity.id,
            conversation_id=activity.conversation.id,
            user=TeamsUser(
                id=activity.from_property.id,
                name=activity.from_property.name,
                aad_object_id=activity.from_property.aad_object_id or "",
            ),
            content=activity.text or "",
            timestamp=datetime.now(),
            channel_id=activity.channel_id or "",
            team_id=getattr(activity.channel_data, "team", {}).get("id", "") if activity.channel_data else "",
            is_group=activity.conversation.is_group or False,
            mentions=[m.mentioned.id for m in (activity.entities or []) if hasattr(m, "mentioned")],
        )
        
        # Dispatch to handlers
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    response = await handler(message, turn_context)
                else:
                    response = handler(message, turn_context)
                
                if response:
                    await turn_context.send_activity(response)
                    
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    def _check_permissions(self, activity) -> bool:
        """Check if user/tenant has permission."""
        # Check tenant
        if self.config.allowed_tenants:
            tenant_id = getattr(activity.channel_data, "tenant", {}).get("id", "") if activity.channel_data else ""
            if tenant_id and tenant_id not in self.config.allowed_tenants:
                return False
        
        # Check user
        if self.config.allowed_users:
            user_id = activity.from_property.aad_object_id or activity.from_property.id
            if user_id not in self.config.allowed_users:
                return False
        
        return True
    
    # ============================================
    # Sending Messages
    # ============================================
    
    async def send_message(
        self,
        conversation_id: str,
        content: str,
        service_url: str = None,
    ) -> bool:
        """
        Send proactive message.
        
        Args:
            conversation_id: Target conversation
            content: Message content
            service_url: Teams service URL
        
        Returns:
            True if sent successfully
        """
        try:
            from botbuilder.schema import (
                Activity,
                ActivityTypes,
                ConversationReference,
            )
            
            # Create conversation reference
            reference = ConversationReference(
                conversation={"id": conversation_id},
                service_url=service_url or "https://smba.trafficmanager.net/teams/",
            )
            
            async def send_callback(turn_context):
                await turn_context.send_activity(content)
            
            await self._adapter.continue_conversation(
                reference,
                send_callback,
                self.config.app_id,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return False
    
    async def send_adaptive_card(
        self,
        conversation_id: str,
        card: dict,
        service_url: str = None,
    ) -> bool:
        """
        Send adaptive card.
        
        Args:
            conversation_id: Target conversation
            card: Adaptive card JSON
            service_url: Teams service URL
        
        Returns:
            True if sent successfully
        """
        try:
            from botbuilder.schema import (
                Activity,
                ActivityTypes,
                Attachment,
                ConversationReference,
            )
            
            attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=card,
            )
            
            reference = ConversationReference(
                conversation={"id": conversation_id},
                service_url=service_url or "https://smba.trafficmanager.net/teams/",
            )
            
            async def send_callback(turn_context):
                activity = Activity(
                    type=ActivityTypes.message,
                    attachments=[attachment],
                )
                await turn_context.send_activity(activity)
            
            await self._adapter.continue_conversation(
                reference,
                send_callback,
                self.config.app_id,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Send card error: {e}")
            return False
    
    # ============================================
    # Adaptive Card Builder
    # ============================================
    
    @staticmethod
    def build_text_card(title: str, body: str) -> dict:
        """Build simple text adaptive card."""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "bolder",
                    "size": "medium",
                },
                {
                    "type": "TextBlock",
                    "text": body,
                    "wrap": True,
                },
            ],
        }
    
    @staticmethod
    def build_action_card(
        title: str,
        body: str,
        actions: list[dict],
    ) -> dict:
        """Build adaptive card with actions."""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "bolder",
                    "size": "medium",
                },
                {
                    "type": "TextBlock",
                    "text": body,
                    "wrap": True,
                },
            ],
            "actions": actions,
        }
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def status(self) -> TeamsStatus:
        return self._status
    
    @property
    def is_running(self) -> bool:
        return self._status == TeamsStatus.RUNNING
    
    def get_stats(self) -> dict:
        return {
            "status": self._status.value,
            "app_id": self.config.app_id[:8] + "..." if self.config.app_id else "",
            "port": self.config.port,
            "handlers": len(self._message_handlers),
        }


# ============================================
# Factory
# ============================================

def create_teams_bot(
    app_id: str = None,
    app_password: str = None,
    port: int = 3978,
) -> TeamsBot:
    """
    Create Teams bot instance.
    
    Args:
        app_id: Azure AD App ID
        app_password: Azure AD App Password
        port: HTTP server port
    
    Returns:
        TeamsBot instance
    """
    config = TeamsConfig(
        app_id=app_id or os.getenv("TEAMS_APP_ID", ""),
        app_password=app_password or os.getenv("TEAMS_APP_PASSWORD", ""),
        port=port,
    )
    return TeamsBot(config)


__all__ = [
    "TeamsStatus",
    "TeamsConfig",
    "TeamsUser",
    "TeamsMessage",
    "TeamsBot",
    "create_teams_bot",
]
