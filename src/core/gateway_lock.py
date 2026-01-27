"""
Gateway Lock System for CursorBot

Provides:
- Bot access locking/unlocking
- Emergency lockdown
- IP-based restrictions
- Time-based access control
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Set

from ..utils.logger import logger


class LockReason(Enum):
    """Reasons for gateway lock."""
    MANUAL = "manual"
    RATE_LIMIT = "rate_limit"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"


@dataclass
class LockInfo:
    """Information about a lock."""
    locked: bool = False
    reason: LockReason = LockReason.MANUAL
    message: str = ""
    locked_at: Optional[datetime] = None
    locked_by: Optional[int] = None
    unlock_at: Optional[datetime] = None
    
    def is_active(self) -> bool:
        """Check if lock is currently active."""
        if not self.locked:
            return False
        
        if self.unlock_at and datetime.now() > self.unlock_at:
            return False
        
        return True
    
    def time_remaining(self) -> Optional[timedelta]:
        """Get remaining lock time."""
        if not self.is_active() or not self.unlock_at:
            return None
        return self.unlock_at - datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "locked": self.locked,
            "reason": self.reason.value,
            "message": self.message,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "locked_by": self.locked_by,
            "unlock_at": self.unlock_at.isoformat() if self.unlock_at else None,
        }


class GatewayLock:
    """
    Controls access to the bot through locking mechanisms.
    """
    
    def __init__(self):
        self._global_lock = LockInfo()
        self._user_locks: dict[int, LockInfo] = {}
        self._group_locks: dict[int, LockInfo] = {}
        self._ip_blacklist: Set[str] = set()
        self._ip_whitelist: Set[str] = set()
        self._allowed_during_lock: Set[int] = set()  # Users who can access during lock
        self._lock_history: list[dict] = []
    
    # ============================================
    # Global Lock
    # ============================================
    
    def lock(
        self,
        reason: LockReason = LockReason.MANUAL,
        message: str = "",
        duration_minutes: int = None,
        locked_by: int = None,
    ) -> LockInfo:
        """
        Lock the gateway globally.
        
        Args:
            reason: Reason for locking
            message: Message to show to users
            duration_minutes: Auto-unlock after this duration
            locked_by: User ID who initiated the lock
        
        Returns:
            LockInfo
        """
        unlock_at = None
        if duration_minutes:
            unlock_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        self._global_lock = LockInfo(
            locked=True,
            reason=reason,
            message=message,
            locked_at=datetime.now(),
            locked_by=locked_by,
            unlock_at=unlock_at,
        )
        
        self._log_lock_event("lock", "global", reason, locked_by)
        logger.warning(f"Gateway LOCKED: {reason.value} - {message}")
        
        return self._global_lock
    
    def unlock(self, unlocked_by: int = None) -> bool:
        """Unlock the gateway."""
        if not self._global_lock.locked:
            return False
        
        self._global_lock.locked = False
        self._log_lock_event("unlock", "global", None, unlocked_by)
        logger.info("Gateway UNLOCKED")
        
        return True
    
    def is_locked(self) -> bool:
        """Check if gateway is locked."""
        return self._global_lock.is_active()
    
    def get_lock_info(self) -> LockInfo:
        """Get current lock information."""
        return self._global_lock
    
    def emergency_lockdown(self, locked_by: int = None) -> LockInfo:
        """Initiate emergency lockdown."""
        return self.lock(
            reason=LockReason.EMERGENCY,
            message="Emergency lockdown activated. Bot is temporarily unavailable.",
            locked_by=locked_by,
        )
    
    def maintenance_mode(
        self,
        duration_minutes: int = 30,
        message: str = "Bot is under maintenance. Please try again later.",
        locked_by: int = None,
    ) -> LockInfo:
        """Enter maintenance mode with auto-unlock."""
        return self.lock(
            reason=LockReason.MAINTENANCE,
            message=message,
            duration_minutes=duration_minutes,
            locked_by=locked_by,
        )
    
    # ============================================
    # User & Group Locks
    # ============================================
    
    def lock_user(
        self,
        user_id: int,
        reason: LockReason = LockReason.MANUAL,
        message: str = "",
        duration_minutes: int = None,
    ) -> LockInfo:
        """Lock a specific user."""
        unlock_at = None
        if duration_minutes:
            unlock_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        lock_info = LockInfo(
            locked=True,
            reason=reason,
            message=message,
            locked_at=datetime.now(),
            unlock_at=unlock_at,
        )
        
        self._user_locks[user_id] = lock_info
        self._log_lock_event("lock", f"user:{user_id}", reason, None)
        logger.info(f"User {user_id} locked: {reason.value}")
        
        return lock_info
    
    def unlock_user(self, user_id: int) -> bool:
        """Unlock a specific user."""
        if user_id in self._user_locks:
            del self._user_locks[user_id]
            self._log_lock_event("unlock", f"user:{user_id}", None, None)
            return True
        return False
    
    def is_user_locked(self, user_id: int) -> bool:
        """Check if a user is locked."""
        if user_id in self._user_locks:
            lock = self._user_locks[user_id]
            if lock.is_active():
                return True
            else:
                del self._user_locks[user_id]
        return False
    
    def lock_group(
        self,
        group_id: int,
        reason: LockReason = LockReason.MANUAL,
        message: str = "",
        duration_minutes: int = None,
    ) -> LockInfo:
        """Lock a specific group."""
        unlock_at = None
        if duration_minutes:
            unlock_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        lock_info = LockInfo(
            locked=True,
            reason=reason,
            message=message,
            locked_at=datetime.now(),
            unlock_at=unlock_at,
        )
        
        self._group_locks[group_id] = lock_info
        self._log_lock_event("lock", f"group:{group_id}", reason, None)
        
        return lock_info
    
    def unlock_group(self, group_id: int) -> bool:
        """Unlock a specific group."""
        if group_id in self._group_locks:
            del self._group_locks[group_id]
            return True
        return False
    
    def is_group_locked(self, group_id: int) -> bool:
        """Check if a group is locked."""
        if group_id in self._group_locks:
            lock = self._group_locks[group_id]
            if lock.is_active():
                return True
            else:
                del self._group_locks[group_id]
        return False
    
    # ============================================
    # Access Control
    # ============================================
    
    def can_access(
        self,
        user_id: int,
        group_id: int = None,
        ip_address: str = None,
    ) -> tuple[bool, str]:
        """
        Check if a user can access the bot.
        
        Args:
            user_id: User ID
            group_id: Optional group ID
            ip_address: Optional IP address
        
        Returns:
            (can_access, reason)
        """
        # Check IP blacklist
        if ip_address and ip_address in self._ip_blacklist:
            return False, "IP address is blacklisted"
        
        # Check IP whitelist (if whitelist is active, only whitelisted IPs allowed)
        if self._ip_whitelist and ip_address:
            if ip_address not in self._ip_whitelist:
                return False, "IP address not in whitelist"
        
        # Check user lock
        if self.is_user_locked(user_id):
            lock = self._user_locks[user_id]
            return False, lock.message or "Your access has been restricted"
        
        # Check group lock
        if group_id and self.is_group_locked(group_id):
            lock = self._group_locks[group_id]
            return False, lock.message or "This group has been restricted"
        
        # Check global lock
        if self.is_locked():
            if user_id in self._allowed_during_lock:
                return True, ""
            return False, self._global_lock.message or "Bot is currently locked"
        
        return True, ""
    
    def allow_during_lock(self, user_id: int) -> None:
        """Allow a user to access bot during lock."""
        self._allowed_during_lock.add(user_id)
    
    def disallow_during_lock(self, user_id: int) -> None:
        """Remove user from lock bypass list."""
        self._allowed_during_lock.discard(user_id)
    
    # ============================================
    # IP Management
    # ============================================
    
    def blacklist_ip(self, ip: str) -> None:
        """Add IP to blacklist."""
        self._ip_blacklist.add(ip)
        self._ip_whitelist.discard(ip)
        logger.info(f"IP blacklisted: {ip}")
    
    def unblacklist_ip(self, ip: str) -> None:
        """Remove IP from blacklist."""
        self._ip_blacklist.discard(ip)
    
    def whitelist_ip(self, ip: str) -> None:
        """Add IP to whitelist."""
        self._ip_whitelist.add(ip)
        self._ip_blacklist.discard(ip)
    
    def unwhitelist_ip(self, ip: str) -> None:
        """Remove IP from whitelist."""
        self._ip_whitelist.discard(ip)
    
    # ============================================
    # History & Stats
    # ============================================
    
    def _log_lock_event(
        self,
        action: str,
        target: str,
        reason: LockReason = None,
        by_user: int = None,
    ) -> None:
        """Log a lock event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "reason": reason.value if reason else None,
            "by_user": by_user,
        }
        self._lock_history.append(event)
        
        # Keep only last 100 events
        if len(self._lock_history) > 100:
            self._lock_history = self._lock_history[-100:]
    
    def get_history(self, limit: int = 20) -> list[dict]:
        """Get lock history."""
        return self._lock_history[-limit:]
    
    def get_stats(self) -> dict:
        """Get lock statistics."""
        return {
            "global_locked": self._global_lock.is_active(),
            "locked_users": len([u for u, l in self._user_locks.items() if l.is_active()]),
            "locked_groups": len([g for g, l in self._group_locks.items() if l.is_active()]),
            "blacklisted_ips": len(self._ip_blacklist),
            "whitelisted_ips": len(self._ip_whitelist),
            "lock_bypass_users": len(self._allowed_during_lock),
        }


# ============================================
# Global Instance
# ============================================

_gateway_lock: Optional[GatewayLock] = None


def get_gateway_lock() -> GatewayLock:
    """Get the global gateway lock instance."""
    global _gateway_lock
    if _gateway_lock is None:
        _gateway_lock = GatewayLock()
    return _gateway_lock


__all__ = [
    "LockReason",
    "LockInfo",
    "GatewayLock",
    "get_gateway_lock",
]
