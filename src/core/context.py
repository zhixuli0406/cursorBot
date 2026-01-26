"""
Conversation Context Management for CursorBot
Inspired by Clawd Bot's context and session management

Provides:
- Conversation state tracking
- Context window management
- Multi-turn dialogue support
- Follow-up handling
- Compaction (conversation compression)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from ..utils.logger import logger


# ============================================
# Compaction System
# ============================================

async def default_compaction_summarizer(messages: list[dict]) -> str:
    """
    Default summarizer for compaction.
    Uses the configured LLM provider to summarize conversation.
    """
    try:
        from .llm_providers import get_llm_manager
        
        manager = get_llm_manager()
        
        # Build conversation text
        conversation_text = "\n".join([
            f"{m['role'].upper()}: {m['content'][:500]}"
            for m in messages
        ])
        
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a conversation summarizer. Summarize the following conversation "
                    "into a concise summary that captures the key points, decisions, and context. "
                    "The summary should be useful for continuing the conversation later. "
                    "Keep it under 200 words. Write in the same language as the conversation."
                )
            },
            {
                "role": "user",
                "content": f"Please summarize this conversation:\n\n{conversation_text}"
            }
        ]
        
        summary = await manager.generate(prompt, max_tokens=500)
        return summary
        
    except Exception as e:
        logger.error(f"Compaction summarizer error: {e}")
        # Fallback: simple truncation
        return f"[Previous conversation with {len(messages)} messages]"


@dataclass
class CompactionConfig:
    """Configuration for conversation compaction."""
    
    # When to trigger compaction
    trigger_message_count: int = 15  # Compact when messages exceed this
    trigger_token_estimate: int = 3000  # Compact when estimated tokens exceed this
    
    # What to keep
    keep_recent_messages: int = 5  # Always keep N most recent messages
    keep_system_messages: bool = True  # Always keep system messages
    
    # Summary settings
    include_summary: bool = True  # Include a summary of compacted messages
    summary_max_length: int = 500  # Max length of summary
    
    # Auto-compaction
    auto_compact: bool = True  # Automatically compact when triggered


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
    Supports both private chats and group chats with isolation.
    """
    user_id: int
    chat_id: int
    messages: list[Message] = field(default_factory=list)
    current_task_id: Optional[str] = None
    current_repo: Optional[str] = None
    state: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Session identification
    session_key: str = ""
    chat_type: str = "private"  # "private", "group", "supergroup", "channel"
    chat_title: Optional[str] = None
    
    # Agent routing
    assigned_agent: Optional[str] = None  # For multi-agent routing
    agent_config: dict = field(default_factory=dict)

    # Configuration
    max_messages: int = 20
    context_timeout_minutes: int = 30
    
    # Compaction
    compaction_config: CompactionConfig = field(default_factory=CompactionConfig)
    compacted_summary: Optional[str] = None  # Summary of compacted messages
    compaction_count: int = 0  # Number of times compaction has been performed
    total_messages_processed: int = 0  # Total messages including compacted ones

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
            "compacted_summary": self.compacted_summary,
            "compaction_count": self.compaction_count,
            "total_messages_processed": self.total_messages_processed,
        }
    
    # ============================================
    # Compaction Methods
    # ============================================
    
    def estimate_tokens(self) -> int:
        """Estimate total tokens in the conversation."""
        # Rough estimation: ~4 chars per token
        total_chars = sum(len(m.content) for m in self.messages)
        if self.compacted_summary:
            total_chars += len(self.compacted_summary)
        return total_chars // 4
    
    def needs_compaction(self) -> bool:
        """Check if compaction is needed based on config."""
        config = self.compaction_config
        
        # Check message count
        if len(self.messages) > config.trigger_message_count:
            return True
        
        # Check token estimate
        if self.estimate_tokens() > config.trigger_token_estimate:
            return True
        
        return False
    
    async def compact(
        self, 
        summarizer: Optional[Callable] = None,
        force: bool = False
    ) -> bool:
        """
        Compact the conversation by summarizing old messages.
        
        Args:
            summarizer: Optional custom summarizer function
            force: Force compaction even if not needed
        
        Returns:
            True if compaction was performed
        """
        config = self.compaction_config
        
        # Check if compaction is needed
        if not force and not self.needs_compaction():
            return False
        
        # Not enough messages to compact
        if len(self.messages) <= config.keep_recent_messages:
            return False
        
        # Split messages: old (to compact) and recent (to keep)
        split_point = len(self.messages) - config.keep_recent_messages
        old_messages = self.messages[:split_point]
        recent_messages = self.messages[split_point:]
        
        # Filter system messages if configured to keep them
        system_messages = []
        if config.keep_system_messages:
            system_messages = [m for m in old_messages if m.role == "system"]
            old_messages = [m for m in old_messages if m.role != "system"]
        
        # Generate summary if configured
        if config.include_summary and old_messages:
            try:
                # Use provided summarizer or default
                summarize_func = summarizer or default_compaction_summarizer
                
                # Convert messages to dict format for summarizer
                messages_dict = [
                    {"role": m.role, "content": m.content}
                    for m in old_messages
                ]
                
                new_summary = await summarize_func(messages_dict)
                
                # Combine with existing summary if present
                if self.compacted_summary:
                    self.compacted_summary = (
                        f"{self.compacted_summary}\n\n"
                        f"[Compaction {self.compaction_count + 1}]\n{new_summary}"
                    )
                else:
                    self.compacted_summary = new_summary
                
                # Truncate summary if too long
                if len(self.compacted_summary) > config.summary_max_length * 2:
                    self.compacted_summary = self.compacted_summary[-config.summary_max_length:]
                    
            except Exception as e:
                logger.error(f"Error during compaction summarization: {e}")
                # Continue without summary
        
        # Update message list
        self.messages = system_messages + recent_messages
        self.compaction_count += 1
        self.total_messages_processed += len(old_messages)
        
        logger.info(
            f"Compacted conversation {self.session_key}: "
            f"removed {len(old_messages)} messages, "
            f"kept {len(self.messages)} messages"
        )
        
        return True
    
    def get_context_with_summary(self) -> list[dict]:
        """
        Get messages for LLM including compacted summary.
        
        Returns:
            List of message dicts ready for LLM
        """
        result = []
        
        # Add compacted summary as system context
        if self.compacted_summary:
            result.append({
                "role": "system",
                "content": (
                    f"[Previous conversation summary]\n{self.compacted_summary}\n"
                    f"[End of summary - {self.total_messages_processed} messages compacted]"
                )
            })
        
        # Add current messages
        for msg in self.messages:
            result.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        return result
    
    def get_compaction_stats(self) -> dict:
        """Get compaction statistics."""
        return {
            "current_messages": len(self.messages),
            "total_processed": self.total_messages_processed,
            "compaction_count": self.compaction_count,
            "has_summary": bool(self.compacted_summary),
            "summary_length": len(self.compacted_summary) if self.compacted_summary else 0,
            "estimated_tokens": self.estimate_tokens(),
            "needs_compaction": self.needs_compaction(),
        }


class ContextManager:
    """
    Manages conversation contexts for all users.
    Supports session isolation for groups and multi-agent routing.
    """

    def __init__(
        self,
        max_contexts: int = 1000,
        default_timeout_minutes: int = 30,
    ):
        self._contexts: dict[str, ConversationContext] = {}  # session_key -> context
        self._agent_routes: dict[str, str] = {}  # pattern -> agent_id
        self.max_contexts = max_contexts
        self.default_timeout_minutes = default_timeout_minutes

    def _make_session_key(
        self, 
        user_id: int, 
        chat_id: int, 
        chat_type: str = "private"
    ) -> str:
        """
        Create a unique session key.
        - Private chats: user_{user_id}
        - Group chats: group_{chat_id}
        """
        if chat_type == "private":
            return f"user_{user_id}"
        else:
            return f"group_{chat_id}"

    def get_context(
        self, 
        user_id: int, 
        chat_id: int,
        chat_type: str = "private",
        chat_title: Optional[str] = None,
    ) -> ConversationContext:
        """
        Get or create a conversation context.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            chat_type: Chat type (private, group, supergroup, channel)
            chat_title: Chat title for groups

        Returns:
            ConversationContext instance
        """
        session_key = self._make_session_key(user_id, chat_id, chat_type)

        if session_key in self._contexts:
            ctx = self._contexts[session_key]
            if ctx.is_expired:
                # Reset expired context but keep session info
                old_agent = ctx.assigned_agent
                old_config = ctx.agent_config
                ctx.clear()
                ctx.assigned_agent = old_agent
                ctx.agent_config = old_config
            # Update last activity
            ctx.last_activity = datetime.now()
            return ctx

        # Create new context
        ctx = ConversationContext(
            user_id=user_id,
            chat_id=chat_id,
            session_key=session_key,
            chat_type=chat_type,
            chat_title=chat_title,
            context_timeout_minutes=self.default_timeout_minutes,
        )
        
        # Auto-assign agent based on routing rules
        ctx.assigned_agent = self._get_agent_for_session(session_key, user_id, chat_id)
        
        self._contexts[session_key] = ctx

        # Cleanup if too many contexts
        self._cleanup_old_contexts()

        return ctx

    def get_context_by_key(self, session_key: str) -> Optional[ConversationContext]:
        """Get context by session key directly."""
        return self._contexts.get(session_key)

    # ============================================
    # Multi-Agent Routing
    # ============================================
    
    def add_agent_route(self, pattern: str, agent_id: str) -> None:
        """
        Add a routing rule for agent assignment.
        
        Args:
            pattern: Pattern to match (e.g., "user_123", "group_*", "*")
            agent_id: Agent identifier to assign
        """
        self._agent_routes[pattern] = agent_id
        logger.info(f"Added agent route: {pattern} -> {agent_id}")
    
    def remove_agent_route(self, pattern: str) -> bool:
        """Remove a routing rule."""
        if pattern in self._agent_routes:
            del self._agent_routes[pattern]
            return True
        return False
    
    def _get_agent_for_session(
        self, 
        session_key: str, 
        user_id: int, 
        chat_id: int
    ) -> Optional[str]:
        """
        Determine which agent should handle this session.
        
        Checks routes in order:
        1. Exact session_key match
        2. user_{user_id} pattern
        3. group_* pattern (for any group)
        4. * (default)
        """
        import fnmatch
        
        # Check exact match first
        if session_key in self._agent_routes:
            return self._agent_routes[session_key]
        
        # Check user-specific pattern
        user_pattern = f"user_{user_id}"
        if user_pattern in self._agent_routes:
            return self._agent_routes[user_pattern]
        
        # Check wildcard patterns
        for pattern, agent_id in self._agent_routes.items():
            if fnmatch.fnmatch(session_key, pattern):
                return agent_id
        
        return None
    
    def get_agent_routes(self) -> dict[str, str]:
        """Get all configured agent routes."""
        return self._agent_routes.copy()
    
    def set_session_agent(
        self, 
        user_id: int, 
        chat_id: int, 
        agent_id: str,
        chat_type: str = "private"
    ) -> None:
        """Manually set the agent for a specific session."""
        ctx = self.get_context(user_id, chat_id, chat_type)
        ctx.assigned_agent = agent_id
        logger.info(f"Set agent for session {ctx.session_key}: {agent_id}")

    # Legacy method for backward compatibility
    def _make_key(self, user_id: int, chat_id: int) -> tuple[int, int]:
        """Create a unique key for user+chat combination (legacy)."""
        return (user_id, chat_id)

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

    def clear_context(
        self, 
        user_id: int, 
        chat_id: int,
        chat_type: str = "private"
    ) -> bool:
        """Clear a specific context."""
        session_key = self._make_session_key(user_id, chat_id, chat_type)
        if session_key in self._contexts:
            self._contexts[session_key].clear()
            return True
        return False

    def delete_context(
        self, 
        user_id: int, 
        chat_id: int,
        chat_type: str = "private"
    ) -> bool:
        """Delete a context entirely."""
        session_key = self._make_session_key(user_id, chat_id, chat_type)
        if session_key in self._contexts:
            del self._contexts[session_key]
            return True
        return False
    
    def list_sessions(self) -> list[dict]:
        """List all active sessions with their info."""
        sessions = []
        for key, ctx in self._contexts.items():
            sessions.append({
                "session_key": key,
                "user_id": ctx.user_id,
                "chat_id": ctx.chat_id,
                "chat_type": ctx.chat_type,
                "chat_title": ctx.chat_title,
                "assigned_agent": ctx.assigned_agent,
                "message_count": len(ctx.messages),
                "last_activity": ctx.last_activity.isoformat(),
                "is_expired": ctx.is_expired,
            })
        return sessions

    def add_user_message(
        self,
        user_id: int,
        chat_id: int,
        content: str,
        metadata: dict = None,
        chat_type: str = "private",
        auto_compact: bool = True,
    ) -> ConversationContext:
        """
        Add a user message and return the context.
        Optionally triggers auto-compaction if enabled.
        """
        ctx = self.get_context(user_id, chat_id, chat_type)
        ctx.add_user_message(content, metadata)
        ctx.total_messages_processed += 1
        
        # Schedule auto-compaction if needed (non-blocking)
        if auto_compact and ctx.compaction_config.auto_compact and ctx.needs_compaction():
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._auto_compact(ctx))
            except RuntimeError:
                pass  # No event loop, skip auto-compaction
        
        return ctx
    
    async def _auto_compact(self, ctx: ConversationContext) -> None:
        """Perform auto-compaction in background."""
        try:
            await ctx.compact()
        except Exception as e:
            logger.warning(f"Auto-compaction failed for {ctx.session_key}: {e}")

    def add_assistant_message(
        self,
        user_id: int,
        chat_id: int,
        content: str,
        metadata: dict = None,
        chat_type: str = "private",
    ) -> ConversationContext:
        """Add an assistant message and return the context."""
        ctx = self.get_context(user_id, chat_id, chat_type)
        ctx.add_assistant_message(content, metadata)
        return ctx

    def get_conversation_prompt(
        self,
        user_id: int,
        chat_id: int,
        current_message: str,
        include_context: bool = True,
        n_messages: int = 5,
        chat_type: str = "private",
    ) -> str:
        """
        Build a prompt with conversation context.

        Args:
            user_id: User ID
            chat_id: Chat ID
            current_message: Current user message
            include_context: Whether to include conversation history
            n_messages: Number of historical messages to include
            chat_type: Chat type

        Returns:
            Full prompt string with context
        """
        ctx = self.get_context(user_id, chat_id, chat_type)

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
        chat_type: str = "private",
    ) -> bool:
        """
        Check if current message is likely a follow-up.

        Args:
            user_id: User ID
            chat_id: Chat ID
            timeout_seconds: Max time since last message
            chat_type: Chat type

        Returns:
            True if this appears to be a follow-up message
        """
        ctx = self.get_context(user_id, chat_id, chat_type)

        if not ctx.messages:
            return False

        last_msg = ctx.messages[-1]
        time_since = datetime.now() - last_msg.timestamp

        return time_since.total_seconds() < timeout_seconds

    def get_current_task(
        self, 
        user_id: int, 
        chat_id: int,
        chat_type: str = "private"
    ) -> Optional[str]:
        """Get the current task ID for this context."""
        ctx = self.get_context(user_id, chat_id, chat_type)
        return ctx.current_task_id

    def set_current_task(
        self, 
        user_id: int, 
        chat_id: int, 
        task_id: str,
        chat_type: str = "private"
    ) -> None:
        """Set the current task ID for this context."""
        ctx = self.get_context(user_id, chat_id, chat_type)
        ctx.current_task_id = task_id

    def get_stats(self) -> dict:
        """Get manager statistics."""
        active = sum(1 for c in self._contexts.values() if not c.is_expired)
        total_messages = sum(len(c.messages) for c in self._contexts.values())
        
        # Group by chat type
        by_type = {}
        for ctx in self._contexts.values():
            chat_type = ctx.chat_type
            if chat_type not in by_type:
                by_type[chat_type] = 0
            by_type[chat_type] += 1
        
        # Count assigned agents
        agents = {}
        for ctx in self._contexts.values():
            agent = ctx.assigned_agent or "default"
            if agent not in agents:
                agents[agent] = 0
            agents[agent] += 1

        return {
            "total_contexts": len(self._contexts),
            "active_contexts": active,
            "total_messages": total_messages,
            "by_chat_type": by_type,
            "by_agent": agents,
            "agent_routes": len(self._agent_routes),
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
