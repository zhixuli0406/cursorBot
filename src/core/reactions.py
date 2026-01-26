"""
Reactions System for CursorBot

Provides:
- Message reactions (emoji feedback)
- Reaction tracking
- Auto-reactions based on content
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class ReactionType(Enum):
    """Standard reaction types."""
    # Positive
    LIKE = "👍"
    LOVE = "❤️"
    CELEBRATE = "🎉"
    FIRE = "🔥"
    STAR = "⭐"
    ROCKET = "🚀"
    
    # Acknowledgment
    EYES = "👀"
    CHECK = "✅"
    THINKING = "🤔"
    WORKING = "⏳"
    
    # Negative
    DISLIKE = "👎"
    SAD = "😢"
    ERROR = "❌"
    WARNING = "⚠️"
    
    # Task status
    PENDING = "⏱️"
    IN_PROGRESS = "🔄"
    COMPLETED = "✅"
    FAILED = "❌"


@dataclass
class Reaction:
    """Represents a reaction on a message."""
    emoji: str
    user_id: int
    message_id: int
    chat_id: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "emoji": self.emoji,
            "user_id": self.user_id,
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "timestamp": self.timestamp.isoformat(),
        }


class ReactionManager:
    """
    Manages message reactions.
    """
    
    # Emoji aliases for easy access
    EMOJI = {
        "like": "👍",
        "love": "❤️",
        "fire": "🔥",
        "star": "⭐",
        "rocket": "🚀",
        "eyes": "👀",
        "check": "✅",
        "thinking": "🤔",
        "working": "⏳",
        "error": "❌",
        "warning": "⚠️",
        "celebrate": "🎉",
        "ok": "👌",
        "clap": "👏",
        "100": "💯",
        "bulb": "💡",
        "sparkle": "✨",
    }
    
    def __init__(self):
        self._reactions: dict[tuple[int, int], list[Reaction]] = {}  # (chat_id, msg_id) -> reactions
        self._auto_rules: list[tuple[Callable, str]] = []
    
    def add_reaction(
        self,
        chat_id: int,
        message_id: int,
        emoji: str,
        user_id: int = 0,
    ) -> Reaction:
        """
        Add a reaction to a message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
            emoji: Emoji or alias
            user_id: User who reacted
        
        Returns:
            Reaction object
        """
        # Resolve alias
        emoji = self.EMOJI.get(emoji.lower(), emoji)
        
        key = (chat_id, message_id)
        reaction = Reaction(
            emoji=emoji,
            user_id=user_id,
            message_id=message_id,
            chat_id=chat_id,
        )
        
        if key not in self._reactions:
            self._reactions[key] = []
        
        self._reactions[key].append(reaction)
        logger.debug(f"Added reaction {emoji} to message {message_id}")
        
        return reaction
    
    def get_reactions(self, chat_id: int, message_id: int) -> list[Reaction]:
        """Get all reactions for a message."""
        return self._reactions.get((chat_id, message_id), [])
    
    def remove_reaction(
        self,
        chat_id: int,
        message_id: int,
        emoji: str,
        user_id: int = None,
    ) -> bool:
        """Remove a reaction from a message."""
        key = (chat_id, message_id)
        if key not in self._reactions:
            return False
        
        emoji = self.EMOJI.get(emoji.lower(), emoji)
        
        original_len = len(self._reactions[key])
        self._reactions[key] = [
            r for r in self._reactions[key]
            if not (r.emoji == emoji and (user_id is None or r.user_id == user_id))
        ]
        
        return len(self._reactions[key]) < original_len
    
    def add_auto_rule(self, condition: Callable, emoji: str) -> None:
        """
        Add an auto-reaction rule.
        
        Args:
            condition: Function(text) -> bool
            emoji: Emoji to add when condition is True
        """
        self._auto_rules.append((condition, emoji))
    
    def get_auto_reactions(self, text: str) -> list[str]:
        """Get auto-reactions for text based on rules."""
        reactions = []
        for condition, emoji in self._auto_rules:
            try:
                if condition(text):
                    reactions.append(emoji)
            except Exception:
                pass
        return reactions
    
    @staticmethod
    def get_status_emoji(status: str) -> str:
        """Get emoji for a status string."""
        status_map = {
            "pending": "⏱️",
            "running": "🔄",
            "in_progress": "🔄",
            "completed": "✅",
            "success": "✅",
            "failed": "❌",
            "error": "❌",
            "cancelled": "🚫",
            "timeout": "⏰",
            "waiting": "⏳",
        }
        return status_map.get(status.lower(), "❓")
    
    @staticmethod
    def format_with_emoji(text: str, emoji: str = None, status: str = None) -> str:
        """Format text with emoji prefix."""
        if status:
            emoji = ReactionManager.get_status_emoji(status)
        if emoji:
            return f"{emoji} {text}"
        return text


async def react_to_message(
    bot,
    chat_id: int,
    message_id: int,
    emoji: str,
) -> bool:
    """
    Add a reaction to a Telegram message.
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID
        message_id: Message ID
        emoji: Emoji to react with
    
    Returns:
        True if successful
    """
    try:
        # Resolve alias
        emoji = ReactionManager.EMOJI.get(emoji.lower(), emoji)
        
        # Telegram setMessageReaction API
        await bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[{"type": "emoji", "emoji": emoji}],
        )
        logger.debug(f"Reacted with {emoji} to message {message_id}")
        return True
        
    except Exception as e:
        # Reactions might not be supported in all chats
        logger.debug(f"Could not add reaction: {e}")
        return False


async def react_status(
    bot,
    chat_id: int,
    message_id: int,
    status: str,
) -> bool:
    """
    React to a message based on task status.
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID
        message_id: Message ID
        status: Status string
    
    Returns:
        True if successful
    """
    emoji = ReactionManager.get_status_emoji(status)
    return await react_to_message(bot, chat_id, message_id, emoji)


# ============================================
# Global Instance
# ============================================

_reaction_manager: Optional[ReactionManager] = None


def get_reaction_manager() -> ReactionManager:
    """Get the global reaction manager instance."""
    global _reaction_manager
    if _reaction_manager is None:
        _reaction_manager = ReactionManager()
    return _reaction_manager


__all__ = [
    "ReactionType",
    "Reaction",
    "ReactionManager",
    "react_to_message",
    "react_status",
    "get_reaction_manager",
]
