"""
iMessage Integration for CursorBot (macOS only)

Uses AppleScript and Messages.app database to send/receive iMessages.
Supports:
- Text messages
- Read receipts
- Group chats
- Attachments (images, files)

Note: Requires macOS with Full Disk Access for database reading
"""

import asyncio
import os
import platform
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from ..utils.logger import logger


class IMessageStatus(Enum):
    """iMessage connection status."""
    NOT_MACOS = "not_macos"
    NO_ACCESS = "no_access"
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class IMessageConfig:
    """iMessage bot configuration."""
    # Polling settings
    poll_interval: float = 2.0  # Seconds between checks
    
    # Database path (auto-detected)
    db_path: str = ""
    
    # Features
    allowed_contacts: list[str] = field(default_factory=list)
    ignore_groups: bool = False
    mark_as_read: bool = True
    
    # Rate limits
    message_delay: float = 0.5


@dataclass
class IMessageContact:
    """iMessage contact."""
    id: str  # Phone number or email
    name: str = ""
    is_group: bool = False


@dataclass
class IMessage:
    """iMessage message."""
    id: int
    chat_id: str
    sender: str
    content: str
    timestamp: datetime
    is_from_me: bool = False
    is_group: bool = False
    has_attachment: bool = False
    attachment_path: str = ""


class IMessageBot:
    """
    iMessage bot using macOS Messages.app integration.
    
    Note: Only works on macOS with proper permissions.
    """
    
    def __init__(self, config: IMessageConfig = None):
        self.config = config or IMessageConfig()
        self._status = IMessageStatus.STOPPED
        self._message_handlers: list[Callable] = []
        self._last_message_id = 0
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        
        # Auto-detect database path
        if not self.config.db_path:
            self.config.db_path = os.path.expanduser(
                "~/Library/Messages/chat.db"
            )
    
    # ============================================
    # Platform Check
    # ============================================
    
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return platform.system() == "Darwin"
    
    def has_db_access(self) -> bool:
        """Check if we have access to Messages database."""
        if not os.path.exists(self.config.db_path):
            return False
        try:
            conn = sqlite3.connect(self.config.db_path)
            conn.execute("SELECT 1 FROM message LIMIT 1")
            conn.close()
            return True
        except:
            return False
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """Start iMessage bot."""
        if not self.is_macos():
            logger.error("iMessage is only available on macOS")
            self._status = IMessageStatus.NOT_MACOS
            return False
        
        if not self.has_db_access():
            logger.error(
                "No access to Messages database. "
                "Grant Full Disk Access in System Preferences > Security & Privacy"
            )
            self._status = IMessageStatus.NO_ACCESS
            return False
        
        try:
            # Get last message ID
            self._last_message_id = self._get_last_message_id()
            
            # Start polling
            self._running = True
            self._poll_task = asyncio.create_task(self._poll_messages())
            
            self._status = IMessageStatus.RUNNING
            logger.info("iMessage bot started")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start iMessage bot: {e}")
            self._status = IMessageStatus.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop iMessage bot."""
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        self._status = IMessageStatus.STOPPED
        logger.info("iMessage bot stopped")
    
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
                messages = self._get_new_messages()
                
                for msg in messages:
                    if self._should_process(msg):
                        await self._dispatch_message(msg)
                    self._last_message_id = max(self._last_message_id, msg.id)
                
            except Exception as e:
                logger.error(f"Poll error: {e}")
            
            await asyncio.sleep(self.config.poll_interval)
    
    def _get_last_message_id(self) -> int:
        """Get the last message ID from database."""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.execute(
                "SELECT MAX(ROWID) FROM message"
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] or 0
        except:
            return 0
    
    def _get_new_messages(self) -> list[IMessage]:
        """Get new messages since last check."""
        messages = []
        
        try:
            conn = sqlite3.connect(self.config.db_path)
            
            query = """
                SELECT 
                    m.ROWID,
                    m.text,
                    m.date,
                    m.is_from_me,
                    m.cache_has_attachments,
                    h.id as sender,
                    c.chat_identifier,
                    c.display_name
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                LEFT JOIN chat c ON cmj.chat_id = c.ROWID
                WHERE m.ROWID > ?
                ORDER BY m.ROWID ASC
                LIMIT 100
            """
            
            cursor = conn.execute(query, (self._last_message_id,))
            
            for row in cursor.fetchall():
                msg_id, text, date, is_from_me, has_attach, sender, chat_id, display_name = row
                
                if not text:  # Skip empty messages
                    continue
                
                # Convert Apple timestamp to datetime
                timestamp = datetime(2001, 1, 1) + timedelta(seconds=date / 1e9) if date else datetime.now()
                
                messages.append(IMessage(
                    id=msg_id,
                    chat_id=chat_id or sender or "",
                    sender=sender or "",
                    content=text,
                    timestamp=timestamp,
                    is_from_me=bool(is_from_me),
                    is_group="chat" in (chat_id or ""),
                    has_attachment=bool(has_attach),
                ))
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Get messages error: {e}")
        
        return messages
    
    def _should_process(self, message: IMessage) -> bool:
        """Check if message should be processed."""
        # Skip our own messages
        if message.is_from_me:
            return False
        
        # Check allowed contacts
        if self.config.allowed_contacts:
            if message.sender not in self.config.allowed_contacts:
                return False
        
        # Check group setting
        if self.config.ignore_groups and message.is_group:
            return False
        
        return True
    
    async def _dispatch_message(self, message: IMessage) -> None:
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
    
    async def _handle_command(self, message: IMessage) -> bool:
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
            platform="imessage",
            args=args,
            raw_text=message.content,
        )
        
        # Execute command
        result = await execute_command(command, ctx)
        
        if result:
            await self.send_message(message.sender, result.message)
            return True
        
        return False
    
    # ============================================
    # Sending Messages
    # ============================================
    
    async def send_message(self, recipient: str, content: str) -> bool:
        """
        Send iMessage using AppleScript.
        
        Args:
            recipient: Phone number or email
            content: Message content
        
        Returns:
            True if sent successfully
        """
        if not self.is_macos():
            return False
        
        try:
            # Escape special characters
            content = content.replace('\\', '\\\\').replace('"', '\\"')
            
            script = f'''
                tell application "Messages"
                    set targetService to 1st service whose service type = iMessage
                    set targetBuddy to buddy "{recipient}" of targetService
                    send "{content}" to targetBuddy
                end tell
            '''
            
            process = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            _, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Send error: {stderr.decode()}")
                return False
            
            await asyncio.sleep(self.config.message_delay)
            return True
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    async def send_file(self, recipient: str, file_path: str) -> bool:
        """
        Send file via iMessage.
        
        Args:
            recipient: Phone number or email
            file_path: Path to file
        
        Returns:
            True if sent successfully
        """
        if not self.is_macos() or not os.path.exists(file_path):
            return False
        
        try:
            abs_path = os.path.abspath(file_path)
            
            script = f'''
                tell application "Messages"
                    set targetService to 1st service whose service type = iMessage
                    set targetBuddy to buddy "{recipient}" of targetService
                    send POSIX file "{abs_path}" to targetBuddy
                end tell
            '''
            
            process = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Send file error: {e}")
            return False
    
    # ============================================
    # Contact Management
    # ============================================
    
    async def get_recent_chats(self, limit: int = 20) -> list[IMessageContact]:
        """Get recent chat contacts."""
        contacts = []
        
        try:
            conn = sqlite3.connect(self.config.db_path)
            
            query = """
                SELECT DISTINCT
                    c.chat_identifier,
                    c.display_name
                FROM chat c
                ORDER BY c.ROWID DESC
                LIMIT ?
            """
            
            cursor = conn.execute(query, (limit,))
            
            for row in cursor.fetchall():
                chat_id, display_name = row
                contacts.append(IMessageContact(
                    id=chat_id,
                    name=display_name or chat_id,
                    is_group="chat" in chat_id,
                ))
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Get chats error: {e}")
        
        return contacts
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def status(self) -> IMessageStatus:
        return self._status
    
    @property
    def is_running(self) -> bool:
        return self._status == IMessageStatus.RUNNING
    
    def get_stats(self) -> dict:
        return {
            "status": self._status.value,
            "is_macos": self.is_macos(),
            "has_db_access": self.has_db_access(),
            "last_message_id": self._last_message_id,
            "handlers": len(self._message_handlers),
        }


# ============================================
# Factory
# ============================================

def create_imessage_bot(
    allowed_contacts: list[str] = None,
    poll_interval: float = 2.0,
) -> IMessageBot:
    """
    Create iMessage bot instance.
    
    Args:
        allowed_contacts: List of allowed phone numbers/emails
        poll_interval: Seconds between message checks
    
    Returns:
        IMessageBot instance
    """
    config = IMessageConfig(
        allowed_contacts=allowed_contacts or [],
        poll_interval=poll_interval,
    )
    return IMessageBot(config)


__all__ = [
    "IMessageStatus",
    "IMessageConfig",
    "IMessageContact",
    "IMessage",
    "IMessageBot",
    "create_imessage_bot",
]
