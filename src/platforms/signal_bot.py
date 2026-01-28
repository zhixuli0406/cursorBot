"""
Signal Bot Integration for CursorBot

Uses signal-cli for Signal messenger integration.
Provides:
- Message receiving and sending
- Group chat support
- Attachment handling
- Privacy-focused communication

Setup:
1. Install signal-cli: https://github.com/AsamK/signal-cli
2. Link or register a phone number
3. Configure SIGNAL_* environment variables

Usage:
    from src.platforms.signal_bot import SignalBot
    
    bot = SignalBot()
    await bot.start()
"""

import os
import json
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from ..utils.logger import logger


@dataclass
class SignalMessage:
    """Represents a Signal message."""
    id: str
    sender: str
    recipient: str
    text: str
    timestamp: datetime
    group_id: str = ""
    attachments: list[dict] = field(default_factory=list)
    quote: dict = None
    reaction: dict = None
    is_group: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "group_id": self.group_id,
            "attachments": self.attachments,
            "quote": self.quote,
            "reaction": self.reaction,
            "is_group": self.is_group,
        }


@dataclass
class SignalContact:
    """Represents a Signal contact."""
    number: str
    name: str = ""
    profile_name: str = ""
    is_blocked: bool = False


@dataclass
class SignalGroup:
    """Represents a Signal group."""
    id: str
    name: str
    members: list[str] = field(default_factory=list)
    admins: list[str] = field(default_factory=list)


class SignalBot:
    """
    Signal messenger bot using signal-cli.
    
    Requires signal-cli to be installed and configured.
    """
    
    def __init__(
        self,
        phone_number: str = None,
        signal_cli_path: str = None,
        config_path: str = None,
    ):
        """
        Initialize Signal bot.
        
        Args:
            phone_number: Signal phone number (e.g., +1234567890)
            signal_cli_path: Path to signal-cli binary
            config_path: Path to signal-cli config directory
        """
        self.phone_number = phone_number or os.getenv("SIGNAL_PHONE_NUMBER")
        self.signal_cli_path = signal_cli_path or os.getenv(
            "SIGNAL_CLI_PATH", "signal-cli"
        )
        self.config_path = config_path or os.getenv(
            "SIGNAL_CONFIG_PATH", 
            str(Path.home() / ".local" / "share" / "signal-cli")
        )
        
        self._running = False
        self._message_handlers: list[Callable] = []
        self._receive_task = None
        self._process = None
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """
        Start the Signal bot.
        
        Returns:
            True if started successfully
        """
        if self._running:
            return True
        
        if not self.phone_number:
            logger.error("Signal phone number not configured")
            return False
        
        # Check signal-cli is available
        if not await self._check_signal_cli():
            return False
        
        # Start receiving messages
        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        logger.info(f"Signal bot started for {self.phone_number}")
        return True
    
    async def stop(self) -> None:
        """Stop the Signal bot."""
        self._running = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._process:
            self._process.terminate()
        
        logger.info("Signal bot stopped")
    
    async def _check_signal_cli(self) -> bool:
        """Check if signal-cli is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.signal_cli_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode == 0:
                version = stdout.decode().strip()
                logger.info(f"signal-cli found: {version}")
                return True
            
        except FileNotFoundError:
            logger.error(f"signal-cli not found at: {self.signal_cli_path}")
            logger.info("Install from: https://github.com/AsamK/signal-cli")
        except Exception as e:
            logger.error(f"signal-cli check failed: {e}")
        
        return False
    
    # ============================================
    # Message Receiving
    # ============================================
    
    async def _receive_loop(self) -> None:
        """Continuously receive messages."""
        while self._running:
            try:
                messages = await self._receive_messages()
                
                for msg in messages:
                    await self._handle_message(msg)
                
                # Small delay to prevent busy loop
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Signal receive error: {e}")
                await asyncio.sleep(5)
    
    async def _receive_messages(self) -> list[SignalMessage]:
        """Receive pending messages."""
        messages = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                self.signal_cli_path,
                "-a", self.phone_number,
                "--config", self.config_path,
                "receive",
                "--json",
                "--timeout", "3",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await proc.communicate()
            
            if stdout:
                # Parse JSON lines
                for line in stdout.decode().strip().split("\n"):
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg = self._parse_message(data)
                        if msg:
                            messages.append(msg)
                    except json.JSONDecodeError:
                        pass
            
        except Exception as e:
            logger.error(f"Failed to receive messages: {e}")
        
        return messages
    
    def _parse_message(self, data: dict) -> Optional[SignalMessage]:
        """Parse a message from signal-cli JSON output."""
        envelope = data.get("envelope", {})
        
        if not envelope:
            return None
        
        # Get message data
        data_msg = envelope.get("dataMessage", {})
        if not data_msg:
            return None
        
        # Extract text
        text = data_msg.get("message", "")
        if not text:
            return None
        
        # Parse timestamp
        timestamp = datetime.fromtimestamp(
            envelope.get("timestamp", 0) / 1000
        )
        
        # Check for group
        group_info = data_msg.get("groupInfo", {})
        group_id = group_info.get("groupId", "")
        is_group = bool(group_id)
        
        # Parse attachments
        attachments = []
        for att in data_msg.get("attachments", []):
            attachments.append({
                "id": att.get("id", ""),
                "filename": att.get("filename", ""),
                "content_type": att.get("contentType", ""),
                "size": att.get("size", 0),
            })
        
        return SignalMessage(
            id=str(envelope.get("timestamp", "")),
            sender=envelope.get("source", ""),
            recipient=self.phone_number,
            text=text,
            timestamp=timestamp,
            group_id=group_id,
            attachments=attachments,
            quote=data_msg.get("quote"),
            reaction=data_msg.get("reaction"),
            is_group=is_group,
        )
    
    async def _handle_message(self, message: SignalMessage) -> None:
        """Handle an incoming message."""
        logger.debug(f"Signal message from {message.sender}: {message.text[:50]}...")
        
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
    
    def on_message(self, handler: Callable) -> None:
        """Register a message handler."""
        self._message_handlers.append(handler)
    
    # ============================================
    # Message Sending
    # ============================================
    
    async def send_message(
        self,
        recipient: str,
        text: str,
        attachments: list[str] = None,
        quote_timestamp: int = None,
    ) -> bool:
        """
        Send a message to a contact.
        
        Args:
            recipient: Phone number or group ID
            text: Message text
            attachments: List of file paths to attach
            quote_timestamp: Timestamp of message to quote
            
        Returns:
            True if sent successfully
        """
        try:
            cmd = [
                self.signal_cli_path,
                "-a", self.phone_number,
                "--config", self.config_path,
                "send",
                "-m", text,
            ]
            
            # Add recipient
            if recipient.startswith("group."):
                cmd.extend(["-g", recipient])
            else:
                cmd.append(recipient)
            
            # Add attachments
            if attachments:
                for att in attachments:
                    cmd.extend(["-a", att])
            
            # Add quote
            if quote_timestamp:
                cmd.extend(["--quote-timestamp", str(quote_timestamp)])
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            _, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.debug(f"Signal message sent to {recipient}")
                return True
            else:
                logger.error(f"Send failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Signal message: {e}")
            return False
    
    async def send_group_message(
        self,
        group_id: str,
        text: str,
        attachments: list[str] = None,
    ) -> bool:
        """
        Send a message to a group.
        
        Args:
            group_id: Group ID
            text: Message text
            attachments: List of file paths to attach
            
        Returns:
            True if sent successfully
        """
        return await self.send_message(
            recipient=group_id,
            text=text,
            attachments=attachments,
        )
    
    async def send_reaction(
        self,
        recipient: str,
        emoji: str,
        target_timestamp: int,
        remove: bool = False,
    ) -> bool:
        """
        Send a reaction to a message.
        
        Args:
            recipient: Phone number or group ID
            emoji: Emoji to react with
            target_timestamp: Timestamp of target message
            remove: Whether to remove the reaction
            
        Returns:
            True if sent successfully
        """
        try:
            cmd = [
                self.signal_cli_path,
                "-a", self.phone_number,
                "--config", self.config_path,
                "sendReaction",
                "-e", emoji,
                "-a", recipient,
                "-t", str(target_timestamp),
            ]
            
            if remove:
                cmd.append("-r")
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            _, stderr = await proc.communicate()
            return proc.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to send reaction: {e}")
            return False
    
    # ============================================
    # Contact & Group Management
    # ============================================
    
    async def get_contacts(self) -> list[SignalContact]:
        """Get list of contacts."""
        contacts = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                self.signal_cli_path,
                "-a", self.phone_number,
                "--config", self.config_path,
                "listContacts",
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, _ = await proc.communicate()
            
            if stdout:
                data = json.loads(stdout.decode())
                for c in data:
                    contacts.append(SignalContact(
                        number=c.get("number", ""),
                        name=c.get("name", ""),
                        profile_name=c.get("profileName", ""),
                        is_blocked=c.get("blocked", False),
                    ))
            
        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
        
        return contacts
    
    async def get_groups(self) -> list[SignalGroup]:
        """Get list of groups."""
        groups = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                self.signal_cli_path,
                "-a", self.phone_number,
                "--config", self.config_path,
                "listGroups",
                "--json",
                "-d",  # Detailed output
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, _ = await proc.communicate()
            
            if stdout:
                data = json.loads(stdout.decode())
                for g in data:
                    groups.append(SignalGroup(
                        id=g.get("id", ""),
                        name=g.get("name", ""),
                        members=g.get("members", []),
                        admins=g.get("admins", []),
                    ))
            
        except Exception as e:
            logger.error(f"Failed to get groups: {e}")
        
        return groups
    
    # ============================================
    # Account Management
    # ============================================
    
    async def link_device(self, device_name: str = "CursorBot") -> Optional[str]:
        """
        Generate a link URI for linking a new device.
        
        Args:
            device_name: Name for the linked device
            
        Returns:
            Link URI or None
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                self.signal_cli_path,
                "--config", self.config_path,
                "link",
                "-n", device_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, _ = await proc.communicate()
            
            if stdout:
                # Extract the link URI
                output = stdout.decode()
                for line in output.split("\n"):
                    if "tsdevice:" in line or "sgnl:" in line:
                        return line.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate link: {e}")
        
        return None
    
    async def verify_account(self, verification_code: str) -> bool:
        """
        Verify account with SMS code.
        
        Args:
            verification_code: SMS verification code
            
        Returns:
            True if verified successfully
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                self.signal_cli_path,
                "-a", self.phone_number,
                "--config", self.config_path,
                "verify",
                verification_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            _, stderr = await proc.communicate()
            return proc.returncode == 0
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def is_running(self) -> bool:
        """Check if bot is running."""
        return self._running
    
    def get_stats(self) -> dict:
        """Get bot statistics."""
        return {
            "running": self._running,
            "phone_number": self.phone_number,
            "handlers": len(self._message_handlers),
        }


# Global instance
_signal_bot: Optional[SignalBot] = None


def get_signal_bot() -> SignalBot:
    """Get the global Signal bot instance."""
    global _signal_bot
    if _signal_bot is None:
        _signal_bot = SignalBot()
    return _signal_bot


__all__ = [
    "SignalBot",
    "SignalMessage",
    "SignalContact",
    "SignalGroup",
    "get_signal_bot",
]
