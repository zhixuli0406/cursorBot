"""
Session Management for CursorBot
Inspired by ClawdBot's session management system

Features:
- Session persistence (JSON store)
- Reset policies (daily, idle, per-type)
- DM scope control (main, per-peer, per-channel-peer)
- Identity links (cross-platform identity mapping)
- Session lifecycle management
- Token tracking

Reference: https://docs.clawd.bot/concepts/session
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..utils.logger import logger

# Default data directory
DATA_DIR = Path(os.getenv("CURSORBOT_DATA_DIR", "data"))
SESSIONS_DIR = DATA_DIR / "sessions"


class ResetMode(Enum):
    """Session reset modes."""
    DAILY = "daily"      # Reset at specific hour each day
    IDLE = "idle"        # Reset after idle period
    MANUAL = "manual"    # Only reset manually
    NEVER = "never"      # Never auto-reset


class DMScope(Enum):
    """DM session scope modes."""
    MAIN = "main"                    # All DMs share main session
    PER_PEER = "per-peer"            # Isolate by sender id
    PER_CHANNEL_PEER = "per-channel-peer"  # Isolate by channel + sender


class ChatType(Enum):
    """Chat types for session management."""
    DM = "dm"
    GROUP = "group"
    THREAD = "thread"
    CHANNEL = "channel"


@dataclass
class ResetPolicy:
    """Session reset policy configuration."""
    mode: ResetMode = ResetMode.DAILY
    at_hour: int = 4          # Hour of day for daily reset (0-23)
    idle_minutes: int = 120   # Minutes of idle before reset
    
    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "at_hour": self.at_hour,
            "idle_minutes": self.idle_minutes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ResetPolicy":
        return cls(
            mode=ResetMode(data.get("mode", "daily")),
            at_hour=data.get("at_hour", 4),
            idle_minutes=data.get("idle_minutes", 120),
        )


@dataclass
class SessionOrigin:
    """Session origin metadata."""
    label: str = ""           # Human-readable label
    provider: str = ""        # Channel provider (telegram, line, webchat, etc.)
    from_id: str = ""         # Sender ID
    to_id: str = ""           # Recipient ID
    account_id: str = ""      # Provider account ID
    thread_id: str = ""       # Thread/topic ID if applicable
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionOrigin":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SessionEntry:
    """
    Session entry in the store.
    Tracks session state, tokens, and metadata.
    """
    session_id: str
    session_key: str
    user_id: str
    chat_id: str
    chat_type: ChatType = ChatType.DM
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)
    
    # Token tracking
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    context_tokens: int = 0
    
    # Message counts
    message_count: int = 0
    compaction_count: int = 0
    
    # Origin metadata
    origin: SessionOrigin = field(default_factory=SessionOrigin)
    
    # Display info
    display_name: str = ""
    channel: str = ""
    subject: str = ""
    
    # CLI chat ID (for Cursor CLI context)
    cli_chat_id: str = ""
    
    # Custom data
    metadata: dict = field(default_factory=dict)
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.updated_at = datetime.now()
        self.last_message_at = datetime.now()
    
    def add_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Add token usage."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens
    
    def is_stale(self, policy: ResetPolicy) -> bool:
        """Check if session is stale based on reset policy."""
        now = datetime.now()
        
        if policy.mode == ResetMode.NEVER:
            return False
        
        if policy.mode == ResetMode.MANUAL:
            return False
        
        if policy.mode == ResetMode.DAILY:
            # Check if last update is before today's reset time
            reset_today = now.replace(
                hour=policy.at_hour, minute=0, second=0, microsecond=0
            )
            if now.hour < policy.at_hour:
                reset_today -= timedelta(days=1)
            return self.updated_at < reset_today
        
        if policy.mode == ResetMode.IDLE:
            # Check idle timeout
            idle_threshold = now - timedelta(minutes=policy.idle_minutes)
            return self.updated_at < idle_threshold
        
        return False
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "session_key": self.session_key,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "chat_type": self.chat_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat(),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "context_tokens": self.context_tokens,
            "message_count": self.message_count,
            "compaction_count": self.compaction_count,
            "origin": self.origin.to_dict(),
            "display_name": self.display_name,
            "channel": self.channel,
            "subject": self.subject,
            "cli_chat_id": self.cli_chat_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionEntry":
        return cls(
            session_id=data["session_id"],
            session_key=data["session_key"],
            user_id=data["user_id"],
            chat_id=data["chat_id"],
            chat_type=ChatType(data.get("chat_type", "dm")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_message_at=datetime.fromisoformat(data.get("last_message_at", data["updated_at"])),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            context_tokens=data.get("context_tokens", 0),
            message_count=data.get("message_count", 0),
            compaction_count=data.get("compaction_count", 0),
            origin=SessionOrigin.from_dict(data.get("origin", {})),
            display_name=data.get("display_name", ""),
            channel=data.get("channel", ""),
            subject=data.get("subject", ""),
            cli_chat_id=data.get("cli_chat_id", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionConfig:
    """Session management configuration."""
    # DM scope mode
    dm_scope: DMScope = DMScope.MAIN
    
    # Main session key (for dm_scope=main)
    main_key: str = "main"
    
    # Reset policies
    default_reset: ResetPolicy = field(default_factory=ResetPolicy)
    reset_by_type: dict[ChatType, ResetPolicy] = field(default_factory=dict)
    reset_by_channel: dict[str, ResetPolicy] = field(default_factory=dict)
    
    # Reset triggers (commands that start new session)
    reset_triggers: list[str] = field(default_factory=lambda: ["/new", "/reset", "/newchat"])
    
    # Identity links: maps provider-prefixed peer IDs to canonical identity
    # e.g., {"alice": ["telegram:123456", "line:789012"]}
    identity_links: dict[str, list[str]] = field(default_factory=dict)
    
    # Store path
    store_path: str = ""
    
    def get_reset_policy(
        self, 
        chat_type: ChatType = ChatType.DM,
        channel: str = ""
    ) -> ResetPolicy:
        """Get the applicable reset policy."""
        # Channel-specific override first
        if channel and channel in self.reset_by_channel:
            return self.reset_by_channel[channel]
        
        # Type-specific override
        if chat_type in self.reset_by_type:
            return self.reset_by_type[chat_type]
        
        # Default
        return self.default_reset
    
    def resolve_identity(self, provider_peer_id: str) -> str:
        """
        Resolve a provider-prefixed peer ID to canonical identity.
        
        Args:
            provider_peer_id: e.g., "telegram:123456"
        
        Returns:
            Canonical identity if linked, otherwise the original ID
        """
        for canonical, links in self.identity_links.items():
            if provider_peer_id in links:
                return canonical
        return provider_peer_id
    
    def to_dict(self) -> dict:
        return {
            "dm_scope": self.dm_scope.value,
            "main_key": self.main_key,
            "default_reset": self.default_reset.to_dict(),
            "reset_by_type": {k.value: v.to_dict() for k, v in self.reset_by_type.items()},
            "reset_by_channel": {k: v.to_dict() for k, v in self.reset_by_channel.items()},
            "reset_triggers": self.reset_triggers,
            "identity_links": self.identity_links,
            "store_path": self.store_path,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionConfig":
        config = cls()
        if "dm_scope" in data:
            config.dm_scope = DMScope(data["dm_scope"])
        if "main_key" in data:
            config.main_key = data["main_key"]
        if "default_reset" in data:
            config.default_reset = ResetPolicy.from_dict(data["default_reset"])
        if "reset_by_type" in data:
            config.reset_by_type = {
                ChatType(k): ResetPolicy.from_dict(v) 
                for k, v in data["reset_by_type"].items()
            }
        if "reset_by_channel" in data:
            config.reset_by_channel = {
                k: ResetPolicy.from_dict(v) 
                for k, v in data["reset_by_channel"].items()
            }
        if "reset_triggers" in data:
            config.reset_triggers = data["reset_triggers"]
        if "identity_links" in data:
            config.identity_links = data["identity_links"]
        if "store_path" in data:
            config.store_path = data["store_path"]
        return config


class SessionManager:
    """
    Manages sessions for all users across all channels.
    
    Features:
    - Session persistence (JSON store)
    - Reset policies (daily, idle, per-type)
    - DM scope control
    - Identity links for cross-platform users
    - Token tracking
    """
    
    def __init__(self, config: SessionConfig = None, agent_id: str = "default"):
        self.config = config or SessionConfig()
        self.agent_id = agent_id
        
        # Session store: session_key -> SessionEntry
        self._sessions: dict[str, SessionEntry] = {}
        
        # Determine store path
        if self.config.store_path:
            self._store_path = Path(self.config.store_path)
        else:
            self._store_path = SESSIONS_DIR / agent_id / "sessions.json"
        
        # Load existing sessions
        self._load_store()
    
    def _load_store(self) -> None:
        """Load sessions from persistent store."""
        if not self._store_path.exists():
            return
        
        try:
            with open(self._store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for key, entry_data in data.items():
                try:
                    self._sessions[key] = SessionEntry.from_dict(entry_data)
                except Exception as e:
                    logger.warning(f"Failed to load session {key}: {e}")
            
            logger.info(f"Loaded {len(self._sessions)} sessions from {self._store_path}")
        except Exception as e:
            logger.error(f"Failed to load session store: {e}")
    
    def _save_store(self) -> None:
        """Save sessions to persistent store."""
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {key: entry.to_dict() for key, entry in self._sessions.items()}
            
            with open(self._store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save session store: {e}")
    
    def _make_session_key(
        self,
        user_id: str,
        chat_id: str,
        chat_type: ChatType,
        channel: str = "",
        thread_id: str = "",
    ) -> str:
        """
        Create a unique session key based on dm_scope and chat type.
        
        Key formats:
        - DM (main): agent:<agent_id>:<main_key>
        - DM (per-peer): agent:<agent_id>:dm:<peer_id>
        - DM (per-channel-peer): agent:<agent_id>:<channel>:dm:<peer_id>
        - Group: agent:<agent_id>:<channel>:group:<chat_id>
        - Thread: agent:<agent_id>:<channel>:group:<chat_id>:topic:<thread_id>
        - Channel: agent:<agent_id>:<channel>:channel:<chat_id>
        """
        prefix = f"agent:{self.agent_id}"
        
        if chat_type == ChatType.DM:
            # Resolve identity for DM sessions
            provider_peer_id = f"{channel}:{user_id}" if channel else user_id
            resolved_id = self.config.resolve_identity(provider_peer_id)
            
            if self.config.dm_scope == DMScope.MAIN:
                return f"{prefix}:{self.config.main_key}"
            elif self.config.dm_scope == DMScope.PER_PEER:
                return f"{prefix}:dm:{resolved_id}"
            else:  # PER_CHANNEL_PEER
                return f"{prefix}:{channel}:dm:{resolved_id}"
        
        elif chat_type == ChatType.GROUP:
            key = f"{prefix}:{channel}:group:{chat_id}"
            if thread_id:
                key += f":topic:{thread_id}"
            return key
        
        elif chat_type == ChatType.THREAD:
            return f"{prefix}:{channel}:thread:{chat_id}:{thread_id}"
        
        elif chat_type == ChatType.CHANNEL:
            return f"{prefix}:{channel}:channel:{chat_id}"
        
        # Fallback
        return f"{prefix}:{channel}:{chat_type.value}:{user_id}:{chat_id}"
    
    def get_session(
        self,
        user_id: str,
        chat_id: str,
        chat_type: ChatType = ChatType.DM,
        channel: str = "",
        thread_id: str = "",
        display_name: str = "",
        subject: str = "",
        create_if_missing: bool = True,
    ) -> Optional[SessionEntry]:
        """
        Get or create a session.
        
        Automatically handles:
        - Session key generation based on dm_scope
        - Reset policy evaluation
        - Session creation if needed
        
        Args:
            user_id: User identifier
            chat_id: Chat identifier
            chat_type: Type of chat
            channel: Channel/provider name (telegram, line, webchat, etc.)
            thread_id: Thread/topic ID if applicable
            display_name: Display name for the session
            subject: Subject/title for groups
            create_if_missing: Create new session if not found
        
        Returns:
            SessionEntry or None
        """
        session_key = self._make_session_key(
            user_id, chat_id, chat_type, channel, thread_id
        )
        
        # Check existing session
        if session_key in self._sessions:
            session = self._sessions[session_key]
            
            # Check if stale based on reset policy
            policy = self.config.get_reset_policy(chat_type, channel)
            if session.is_stale(policy):
                logger.info(f"Session {session_key} is stale, creating new one")
                return self._create_new_session(
                    session_key, user_id, chat_id, chat_type, 
                    channel, thread_id, display_name, subject
                )
            
            # Touch session (update last activity)
            session.touch()
            self._save_store()
            return session
        
        # Create new session if requested
        if create_if_missing:
            return self._create_new_session(
                session_key, user_id, chat_id, chat_type,
                channel, thread_id, display_name, subject
            )
        
        return None
    
    def _create_new_session(
        self,
        session_key: str,
        user_id: str,
        chat_id: str,
        chat_type: ChatType,
        channel: str,
        thread_id: str,
        display_name: str,
        subject: str,
    ) -> SessionEntry:
        """Create a new session entry."""
        session_id = str(uuid.uuid4())
        
        session = SessionEntry(
            session_id=session_id,
            session_key=session_key,
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            display_name=display_name,
            channel=channel,
            subject=subject,
            origin=SessionOrigin(
                provider=channel,
                from_id=user_id,
                to_id=chat_id,
                thread_id=thread_id,
            ),
        )
        
        self._sessions[session_key] = session
        self._save_store()
        
        logger.info(f"Created new session: {session_key} (id: {session_id[:8]}...)")
        return session
    
    def reset_session(
        self,
        user_id: str,
        chat_id: str,
        chat_type: ChatType = ChatType.DM,
        channel: str = "",
        thread_id: str = "",
    ) -> SessionEntry:
        """
        Reset/create a fresh session (used by /new, /reset commands).
        
        Returns:
            New SessionEntry
        """
        session_key = self._make_session_key(
            user_id, chat_id, chat_type, channel, thread_id
        )
        
        # Get old session info for display name preservation
        old_session = self._sessions.get(session_key)
        display_name = old_session.display_name if old_session else ""
        subject = old_session.subject if old_session else ""
        
        # Create new session
        return self._create_new_session(
            session_key, user_id, chat_id, chat_type,
            channel, thread_id, display_name, subject
        )
    
    def delete_session(self, session_key: str) -> bool:
        """Delete a session by key."""
        if session_key in self._sessions:
            del self._sessions[session_key]
            self._save_store()
            logger.info(f"Deleted session: {session_key}")
            return True
        return False
    
    def get_session_by_key(self, session_key: str) -> Optional[SessionEntry]:
        """Get a session directly by key."""
        return self._sessions.get(session_key)
    
    def get_session_by_id(self, session_id: str) -> Optional[SessionEntry]:
        """Get a session by its unique ID."""
        for session in self._sessions.values():
            if session.session_id == session_id:
                return session
        return None
    
    def list_sessions(
        self,
        user_id: str = None,
        channel: str = None,
        chat_type: ChatType = None,
        active_minutes: int = None,
    ) -> list[SessionEntry]:
        """
        List sessions with optional filters.
        
        Args:
            user_id: Filter by user
            channel: Filter by channel
            chat_type: Filter by chat type
            active_minutes: Only show sessions active within N minutes
        
        Returns:
            List of matching sessions
        """
        sessions = list(self._sessions.values())
        
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        
        if channel:
            sessions = [s for s in sessions if s.channel == channel]
        
        if chat_type:
            sessions = [s for s in sessions if s.chat_type == chat_type]
        
        if active_minutes:
            threshold = datetime.now() - timedelta(minutes=active_minutes)
            sessions = [s for s in sessions if s.updated_at > threshold]
        
        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        return sessions
    
    def list_user_sessions(self, user_id: str) -> list[SessionEntry]:
        """Get all sessions for a user."""
        return self.list_sessions(user_id=user_id)
    
    def update_session_tokens(
        self,
        session_key: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        context_tokens: int = 0,
    ) -> None:
        """Update token usage for a session."""
        if session_key in self._sessions:
            session = self._sessions[session_key]
            session.add_tokens(input_tokens, output_tokens)
            if context_tokens:
                session.context_tokens = context_tokens
            self._save_store()
    
    def increment_message_count(self, session_key: str) -> None:
        """Increment message count for a session."""
        if session_key in self._sessions:
            self._sessions[session_key].message_count += 1
            self._sessions[session_key].touch()
            self._save_store()
    
    def set_cli_chat_id(self, session_key: str, cli_chat_id: str) -> None:
        """Set the Cursor CLI chat ID for a session."""
        if session_key in self._sessions:
            self._sessions[session_key].cli_chat_id = cli_chat_id
            self._save_store()
    
    def get_cli_chat_id(self, session_key: str) -> str:
        """Get the Cursor CLI chat ID for a session."""
        if session_key in self._sessions:
            return self._sessions[session_key].cli_chat_id
        return ""
    
    def cleanup_stale_sessions(self) -> int:
        """
        Remove stale sessions based on their reset policies.
        
        Returns:
            Number of sessions cleaned up
        """
        stale_keys = []
        
        for key, session in self._sessions.items():
            policy = self.config.get_reset_policy(session.chat_type, session.channel)
            if session.is_stale(policy):
                stale_keys.append(key)
        
        for key in stale_keys:
            del self._sessions[key]
        
        if stale_keys:
            self._save_store()
            logger.info(f"Cleaned up {len(stale_keys)} stale sessions")
        
        return len(stale_keys)
    
    def get_stats(self) -> dict:
        """Get session statistics."""
        sessions = list(self._sessions.values())
        
        total_tokens = sum(s.total_tokens for s in sessions)
        total_messages = sum(s.message_count for s in sessions)
        
        by_channel = {}
        for s in sessions:
            channel = s.channel or "unknown"
            if channel not in by_channel:
                by_channel[channel] = 0
            by_channel[channel] += 1
        
        by_type = {}
        for s in sessions:
            chat_type = s.chat_type.value
            if chat_type not in by_type:
                by_type[chat_type] = 0
            by_type[chat_type] += 1
        
        return {
            "total_sessions": len(sessions),
            "total_tokens": total_tokens,
            "total_messages": total_messages,
            "by_channel": by_channel,
            "by_type": by_type,
            "store_path": str(self._store_path),
        }
    
    def get_session_status(self, session_key: str) -> dict:
        """Get detailed status for a session."""
        session = self._sessions.get(session_key)
        if not session:
            return {"exists": False}
        
        policy = self.config.get_reset_policy(session.chat_type, session.channel)
        
        return {
            "exists": True,
            "session_id": session.session_id,
            "session_key": session_key,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "input_tokens": session.input_tokens,
            "output_tokens": session.output_tokens,
            "total_tokens": session.total_tokens,
            "context_tokens": session.context_tokens,
            "message_count": session.message_count,
            "compaction_count": session.compaction_count,
            "is_stale": session.is_stale(policy),
            "reset_policy": policy.to_dict(),
            "channel": session.channel,
            "chat_type": session.chat_type.value,
            "cli_chat_id": session.cli_chat_id,
            "display_name": session.display_name,
        }
    
    def add_identity_link(self, canonical: str, provider_peer_id: str) -> None:
        """Add an identity link."""
        if canonical not in self.config.identity_links:
            self.config.identity_links[canonical] = []
        if provider_peer_id not in self.config.identity_links[canonical]:
            self.config.identity_links[canonical].append(provider_peer_id)
            logger.info(f"Added identity link: {provider_peer_id} -> {canonical}")
    
    def remove_identity_link(self, canonical: str, provider_peer_id: str = None) -> bool:
        """Remove an identity link or all links for a canonical identity."""
        if canonical not in self.config.identity_links:
            return False
        
        if provider_peer_id:
            if provider_peer_id in self.config.identity_links[canonical]:
                self.config.identity_links[canonical].remove(provider_peer_id)
                return True
            return False
        else:
            del self.config.identity_links[canonical]
            return True


# ============================================
# Global Session Manager
# ============================================

_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager."""
    global _session_manager
    if _session_manager is None:
        # Load config from environment or defaults
        config = SessionConfig()
        
        # Override from environment
        dm_scope = os.getenv("SESSION_DM_SCOPE", "main")
        if dm_scope in ("main", "per-peer", "per-channel-peer"):
            config.dm_scope = DMScope(dm_scope)
        
        reset_mode = os.getenv("SESSION_RESET_MODE", "daily")
        if reset_mode in ("daily", "idle", "manual", "never"):
            config.default_reset.mode = ResetMode(reset_mode)
        
        at_hour = os.getenv("SESSION_RESET_HOUR")
        if at_hour:
            config.default_reset.at_hour = int(at_hour)
        
        idle_minutes = os.getenv("SESSION_IDLE_MINUTES")
        if idle_minutes:
            config.default_reset.idle_minutes = int(idle_minutes)
        
        _session_manager = SessionManager(config)
    
    return _session_manager


def reset_session_manager() -> None:
    """Reset the global session manager."""
    global _session_manager
    _session_manager = None


__all__ = [
    "ResetMode",
    "DMScope",
    "ChatType",
    "ResetPolicy",
    "SessionOrigin",
    "SessionEntry",
    "SessionConfig",
    "SessionManager",
    "get_session_manager",
    "reset_session_manager",
]
