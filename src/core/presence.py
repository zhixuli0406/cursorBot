"""
Presence System for CursorBot

Provides:
- User online/offline status tracking
- Activity monitoring
- Status broadcasting
- Presence subscriptions
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional, Set

from ..utils.logger import logger


class PresenceStatus(Enum):
    """User presence statuses."""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


@dataclass
class UserPresence:
    """User presence information."""
    user_id: int
    status: PresenceStatus = PresenceStatus.OFFLINE
    status_text: str = ""
    last_seen: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    platform: str = ""
    device: str = ""
    
    # Activity tracking
    typing: bool = False
    typing_in: Optional[str] = None  # chat_id
    
    def is_online(self) -> bool:
        """Check if user is considered online."""
        return self.status in (PresenceStatus.ONLINE, PresenceStatus.AWAY, PresenceStatus.BUSY)
    
    def is_active(self, threshold_minutes: int = 5) -> bool:
        """Check if user was recently active."""
        return (datetime.now() - self.last_activity) < timedelta(minutes=threshold_minutes)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "status": self.status.value,
            "status_text": self.status_text,
            "last_seen": self.last_seen.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "platform": self.platform,
            "typing": self.typing,
        }


class PresenceManager:
    """
    Manages user presence and status.
    """
    
    def __init__(
        self,
        away_timeout_minutes: int = 5,
        offline_timeout_minutes: int = 30,
    ):
        self._presences: dict[int, UserPresence] = {}
        self._subscribers: dict[int, Set[Callable]] = {}  # user_id -> callbacks
        self._global_subscribers: list[Callable] = []
        self._away_timeout = timedelta(minutes=away_timeout_minutes)
        self._offline_timeout = timedelta(minutes=offline_timeout_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    # ============================================
    # Status Management
    # ============================================
    
    def set_status(
        self,
        user_id: int,
        status: PresenceStatus,
        status_text: str = "",
        platform: str = "",
    ) -> UserPresence:
        """
        Set user status.
        
        Args:
            user_id: User ID
            status: New status
            status_text: Optional status message
            platform: Platform the user is on
        
        Returns:
            Updated UserPresence
        """
        presence = self._get_or_create(user_id)
        old_status = presence.status
        
        presence.status = status
        presence.status_text = status_text
        presence.platform = platform
        presence.last_activity = datetime.now()
        
        if status != PresenceStatus.OFFLINE:
            presence.last_seen = datetime.now()
        
        # Notify subscribers if status changed
        if old_status != status:
            self._notify_change(user_id, presence)
        
        return presence
    
    def set_online(self, user_id: int, platform: str = "") -> UserPresence:
        """Set user as online."""
        return self.set_status(user_id, PresenceStatus.ONLINE, platform=platform)
    
    def set_offline(self, user_id: int) -> UserPresence:
        """Set user as offline."""
        return self.set_status(user_id, PresenceStatus.OFFLINE)
    
    def set_away(self, user_id: int) -> UserPresence:
        """Set user as away."""
        return self.set_status(user_id, PresenceStatus.AWAY)
    
    def set_busy(self, user_id: int, status_text: str = "") -> UserPresence:
        """Set user as busy."""
        return self.set_status(user_id, PresenceStatus.BUSY, status_text)
    
    def set_invisible(self, user_id: int) -> UserPresence:
        """Set user as invisible (online but hidden)."""
        return self.set_status(user_id, PresenceStatus.INVISIBLE)
    
    # ============================================
    # Activity Tracking
    # ============================================
    
    def update_activity(self, user_id: int, platform: str = "") -> UserPresence:
        """
        Update user's last activity (heartbeat).
        Automatically sets online if was offline.
        """
        presence = self._get_or_create(user_id)
        presence.last_activity = datetime.now()
        presence.last_seen = datetime.now()
        
        if presence.status == PresenceStatus.OFFLINE:
            presence.status = PresenceStatus.ONLINE
            self._notify_change(user_id, presence)
        elif presence.status == PresenceStatus.AWAY:
            presence.status = PresenceStatus.ONLINE
            self._notify_change(user_id, presence)
        
        if platform:
            presence.platform = platform
        
        return presence
    
    def set_typing(self, user_id: int, chat_id: str, typing: bool = True) -> None:
        """Set user's typing status."""
        presence = self._get_or_create(user_id)
        presence.typing = typing
        presence.typing_in = chat_id if typing else None
        presence.last_activity = datetime.now()
    
    # ============================================
    # Presence Queries
    # ============================================
    
    def get_presence(self, user_id: int) -> Optional[UserPresence]:
        """Get user's presence."""
        return self._presences.get(user_id)
    
    def get_status(self, user_id: int) -> PresenceStatus:
        """Get user's status."""
        presence = self._presences.get(user_id)
        return presence.status if presence else PresenceStatus.OFFLINE
    
    def is_online(self, user_id: int) -> bool:
        """Check if user is online."""
        presence = self._presences.get(user_id)
        return presence.is_online() if presence else False
    
    def get_online_users(self) -> list[int]:
        """Get list of online user IDs."""
        return [
            uid for uid, p in self._presences.items()
            if p.is_online()
        ]
    
    def get_active_users(self, threshold_minutes: int = 5) -> list[int]:
        """Get list of recently active user IDs."""
        return [
            uid for uid, p in self._presences.items()
            if p.is_active(threshold_minutes)
        ]
    
    def get_typing_users(self, chat_id: str) -> list[int]:
        """Get users currently typing in a chat."""
        return [
            uid for uid, p in self._presences.items()
            if p.typing and p.typing_in == chat_id
        ]
    
    # ============================================
    # Subscriptions
    # ============================================
    
    def subscribe(self, user_id: int, callback: Callable) -> None:
        """Subscribe to a user's presence changes."""
        if user_id not in self._subscribers:
            self._subscribers[user_id] = set()
        self._subscribers[user_id].add(callback)
    
    def unsubscribe(self, user_id: int, callback: Callable) -> None:
        """Unsubscribe from a user's presence changes."""
        if user_id in self._subscribers:
            self._subscribers[user_id].discard(callback)
    
    def subscribe_global(self, callback: Callable) -> None:
        """Subscribe to all presence changes."""
        self._global_subscribers.append(callback)
    
    def _notify_change(self, user_id: int, presence: UserPresence) -> None:
        """Notify subscribers of a presence change."""
        # User-specific subscribers
        for callback in self._subscribers.get(user_id, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(user_id, presence))
                else:
                    callback(user_id, presence)
            except Exception as e:
                logger.error(f"Presence callback error: {e}")
        
        # Global subscribers
        for callback in self._global_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(user_id, presence))
                else:
                    callback(user_id, presence)
            except Exception as e:
                logger.error(f"Global presence callback error: {e}")
    
    # ============================================
    # Cleanup
    # ============================================
    
    async def _cleanup_loop(self) -> None:
        """Background task to update away/offline status."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._check_timeouts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Presence cleanup error: {e}")
    
    async def _check_timeouts(self) -> None:
        """Check for away/offline timeouts."""
        now = datetime.now()
        
        for user_id, presence in list(self._presences.items()):
            if presence.status == PresenceStatus.INVISIBLE:
                continue  # Don't auto-change invisible
            
            inactive_time = now - presence.last_activity
            
            if presence.status == PresenceStatus.ONLINE:
                if inactive_time > self._away_timeout:
                    self.set_away(user_id)
            
            elif presence.status == PresenceStatus.AWAY:
                if inactive_time > self._offline_timeout:
                    self.set_offline(user_id)
    
    def start_cleanup(self) -> None:
        """Start the cleanup background task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    def stop_cleanup(self) -> None:
        """Stop the cleanup background task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    # ============================================
    # Helpers
    # ============================================
    
    def _get_or_create(self, user_id: int) -> UserPresence:
        """Get or create presence for a user."""
        if user_id not in self._presences:
            self._presences[user_id] = UserPresence(user_id=user_id)
        return self._presences[user_id]
    
    def get_stats(self) -> dict:
        """Get presence statistics."""
        by_status = {}
        for presence in self._presences.values():
            status = presence.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_tracked": len(self._presences),
            "online": len(self.get_online_users()),
            "active_5min": len(self.get_active_users(5)),
            "by_status": by_status,
        }


# ============================================
# Global Instance
# ============================================

_presence_manager: Optional[PresenceManager] = None


def get_presence_manager() -> PresenceManager:
    """Get the global presence manager instance."""
    global _presence_manager
    if _presence_manager is None:
        _presence_manager = PresenceManager()
    return _presence_manager


__all__ = [
    "PresenceStatus",
    "UserPresence",
    "PresenceManager",
    "get_presence_manager",
]
