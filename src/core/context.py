"""
Conversation Context Management for CursorBot
Inspired by Clawd Bot's context and session management

Provides:
- Conversation state tracking
- Context window management
- Multi-turn dialogue support
- Follow-up handling
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from ..utils.logger import logger


@dataclass
class Message:
    """Represents a conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ConversationContext:
    """
    Tracks context for a single conversation.
    """
    user_id: int
    chat_id: int
    messages: list[Message] = field(default_factory=list)
    current_task_id: Optional[str] = None
    current_repo: Optional[str] = None
    state: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    # Configuration
    max_messages: int = 20
    context_timeout_minutes: int = 30

    @property
    def is_expired(self) -> bool:
        """Check if context has expired."""
        timeout = timedelta(minutes=self.context_timeout_minutes)
        return datetime.now() - self.last_activity > timeout

    def add_message(self, role: str, content: str, metadata: dict = None) -> None:
        """Add a message to the context."""
        msg = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        self.last_activity = datetime.now()

        # Trim old messages if exceeding limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def add_user_message(self, content: str, metadata: dict = None) -> None:
        """Add a user message."""
        self.add_message("user", content, metadata)

    def add_assistant_message(self, content: str, metadata: dict = None) -> None:
        """Add an assistant message."""
        self.add_message("assistant", content, metadata)

    def get_recent_messages(self, n: int = 10) -> list[Message]:
        """Get the n most recent messages."""
        return self.messages[-n:]

    def get_context_string(self, n: int = 5) -> str:
        """Get recent messages as a formatted string for context."""
        recent = self.get_recent_messages(n)
        parts = []
        for msg in recent:
            role_label = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{role_label}: {msg.content}")
        return "\n".join(parts)

    def clear(self) -> None:
        """Clear the conversation context."""
        self.messages.clear()
        self.current_task_id = None
        self.state.clear()
        self.last_activity = datetime.now()

    def set_state(self, key: str, value: Any) -> None:
        """Set a state variable."""
        self.state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state variable."""
        return self.state.get(key, default)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "messages": [m.to_dict() for m in self.messages],
            "current_task_id": self.current_task_id,
            "current_repo": self.current_repo,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }


class ContextManager:
    """
    Manages conversation contexts for all users.
    """

    def __init__(
        self,
        max_contexts: int = 1000,
        default_timeout_minutes: int = 30,
    ):
        self._contexts: dict[tuple[int, int], ConversationContext] = {}
        self.max_contexts = max_contexts
        self.default_timeout_minutes = default_timeout_minutes

    def _make_key(self, user_id: int, chat_id: int) -> tuple[int, int]:
        """Create a unique key for user+chat combination."""
        return (user_id, chat_id)

    def get_context(self, user_id: int, chat_id: int) -> ConversationContext:
        """
        Get or create a conversation context.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID

        Returns:
            ConversationContext instance
        """
        key = self._make_key(user_id, chat_id)

        if key in self._contexts:
            ctx = self._contexts[key]
            if ctx.is_expired:
                # Reset expired context
                ctx.clear()
            return ctx

        # Create new context
        ctx = ConversationContext(
            user_id=user_id,
            chat_id=chat_id,
            context_timeout_minutes=self.default_timeout_minutes,
        )
        self._contexts[key] = ctx

        # Cleanup if too many contexts
        self._cleanup_old_contexts()

        return ctx

    def _cleanup_old_contexts(self) -> int:
        """Remove old/expired contexts."""
        if len(self._contexts) <= self.max_contexts:
            return 0

        # Sort by last activity
        sorted_keys = sorted(
            self._contexts.keys(),
            key=lambda k: self._contexts[k].last_activity
        )

        # Remove oldest contexts
        to_remove = len(self._contexts) - self.max_contexts
        removed = 0
        for key in sorted_keys[:to_remove]:
            del self._contexts[key]
            removed += 1

        if removed:
            logger.debug(f"Cleaned up {removed} old contexts")

        return removed

    def clear_context(self, user_id: int, chat_id: int) -> bool:
        """Clear a specific context."""
        key = self._make_key(user_id, chat_id)
        if key in self._contexts:
            self._contexts[key].clear()
            return True
        return False

    def delete_context(self, user_id: int, chat_id: int) -> bool:
        """Delete a context entirely."""
        key = self._make_key(user_id, chat_id)
        if key in self._contexts:
            del self._contexts[key]
            return True
        return False

    def add_user_message(
        self,
        user_id: int,
        chat_id: int,
        content: str,
        metadata: dict = None,
    ) -> ConversationContext:
        """Add a user message and return the context."""
        ctx = self.get_context(user_id, chat_id)
        ctx.add_user_message(content, metadata)
        return ctx

    def add_assistant_message(
        self,
        user_id: int,
        chat_id: int,
        content: str,
        metadata: dict = None,
    ) -> ConversationContext:
        """Add an assistant message and return the context."""
        ctx = self.get_context(user_id, chat_id)
        ctx.add_assistant_message(content, metadata)
        return ctx

    def get_conversation_prompt(
        self,
        user_id: int,
        chat_id: int,
        current_message: str,
        include_context: bool = True,
        n_messages: int = 5,
    ) -> str:
        """
        Build a prompt with conversation context.

        Args:
            user_id: User ID
            chat_id: Chat ID
            current_message: Current user message
            include_context: Whether to include conversation history
            n_messages: Number of historical messages to include

        Returns:
            Full prompt string with context
        """
        ctx = self.get_context(user_id, chat_id)

        parts = []

        # Add conversation context
        if include_context and ctx.messages:
            context_str = ctx.get_context_string(n_messages)
            if context_str:
                parts.append("Previous conversation:")
                parts.append(context_str)
                parts.append("")

        # Add current message
        parts.append(f"Current request: {current_message}")

        return "\n".join(parts)

    def is_follow_up(
        self,
        user_id: int,
        chat_id: int,
        timeout_seconds: int = 300,
    ) -> bool:
        """
        Check if current message is likely a follow-up.

        Args:
            user_id: User ID
            chat_id: Chat ID
            timeout_seconds: Max time since last message

        Returns:
            True if this appears to be a follow-up message
        """
        ctx = self.get_context(user_id, chat_id)

        if not ctx.messages:
            return False

        last_msg = ctx.messages[-1]
        time_since = datetime.now() - last_msg.timestamp

        return time_since.total_seconds() < timeout_seconds

    def get_current_task(self, user_id: int, chat_id: int) -> Optional[str]:
        """Get the current task ID for this context."""
        ctx = self.get_context(user_id, chat_id)
        return ctx.current_task_id

    def set_current_task(self, user_id: int, chat_id: int, task_id: str) -> None:
        """Set the current task ID for this context."""
        ctx = self.get_context(user_id, chat_id)
        ctx.current_task_id = task_id

    def get_stats(self) -> dict:
        """Get manager statistics."""
        active = sum(1 for c in self._contexts.values() if not c.is_expired)
        total_messages = sum(len(c.messages) for c in self._contexts.values())

        return {
            "total_contexts": len(self._contexts),
            "active_contexts": active,
            "total_messages": total_messages,
        }


# Global instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get the global ContextManager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


__all__ = [
    "Message",
    "ConversationContext",
    "ContextManager",
    "get_context_manager",
]
