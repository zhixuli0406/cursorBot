"""
Elevated Mode - v0.4 Feature
Permission elevation for sensitive operations.

Provides a time-limited elevated privilege mode for operations that require
additional confirmation or higher permissions (e.g., deleting files, 
executing dangerous commands, modifying system settings).

Commands:
    /elevated - Show elevation status
    /elevated on [minutes] - Request elevation (default: 15 minutes)
    /elevated off - Revoke elevation
    /elevate - Alias for /elevated on
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Callable, Any
import json
import asyncio

from ..utils.logger import logger


class ElevationReason(Enum):
    """Reasons for requesting elevation."""
    GENERAL = "general"
    FILE_DELETE = "file_delete"
    SYSTEM_COMMAND = "system_command"
    CONFIG_CHANGE = "config_change"
    ADMIN_ACTION = "admin_action"
    SENSITIVE_DATA = "sensitive_data"


@dataclass
class ElevationRequest:
    """A request for elevated privileges."""
    user_id: str
    reason: ElevationReason
    requested_at: datetime
    expires_at: datetime
    granted: bool = False
    granted_by: Optional[str] = None
    operation: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if elevation has expired."""
        return datetime.now() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if elevation is currently active."""
        return self.granted and not self.is_expired
    
    @property
    def remaining_minutes(self) -> int:
        """Get remaining minutes of elevation."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.now()
        return max(0, int(delta.total_seconds() / 60))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "reason": self.reason.value,
            "requested_at": self.requested_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "granted": self.granted,
            "granted_by": self.granted_by,
            "operation": self.operation,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ElevationRequest":
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            reason=ElevationReason(data.get("reason", "general")),
            requested_at=datetime.fromisoformat(data["requested_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            granted=data.get("granted", False),
            granted_by=data.get("granted_by"),
            operation=data.get("operation"),
        )


@dataclass
class ElevatedAction:
    """An action that requires elevated privileges."""
    name: str
    description: str
    reason: ElevationReason
    require_confirmation: bool = True
    auto_grant: bool = False  # If True, auto-grant to admin users


# Pre-defined elevated actions
ELEVATED_ACTIONS = {
    "file_delete": ElevatedAction(
        name="file_delete",
        description="Delete files or directories",
        reason=ElevationReason.FILE_DELETE,
        require_confirmation=True,
    ),
    "system_exec": ElevatedAction(
        name="system_exec",
        description="Execute system commands",
        reason=ElevationReason.SYSTEM_COMMAND,
        require_confirmation=True,
    ),
    "config_write": ElevatedAction(
        name="config_write",
        description="Modify configuration files",
        reason=ElevationReason.CONFIG_CHANGE,
        require_confirmation=True,
    ),
    "rag_clear": ElevatedAction(
        name="rag_clear",
        description="Clear RAG knowledge base",
        reason=ElevationReason.SENSITIVE_DATA,
        require_confirmation=True,
    ),
    "memory_clear": ElevatedAction(
        name="memory_clear",
        description="Clear user memory",
        reason=ElevationReason.SENSITIVE_DATA,
        require_confirmation=True,
    ),
    "broadcast": ElevatedAction(
        name="broadcast",
        description="Broadcast message to all users",
        reason=ElevationReason.ADMIN_ACTION,
        require_confirmation=True,
        auto_grant=True,
    ),
}


class ElevatedManager:
    """
    Manager for elevated privilege mode.
    
    Usage:
        manager = get_elevated_manager()
        
        # Request elevation
        request = await manager.request_elevation(user_id, minutes=15)
        
        # Check if elevated
        if manager.is_elevated(user_id):
            # Perform sensitive operation
            pass
        
        # Check specific action
        if manager.can_perform(user_id, "file_delete"):
            # Delete file
            pass
        
        # Require elevation (decorator)
        @manager.require_elevation("file_delete")
        async def delete_file(path):
            ...
    """
    
    _instance: Optional["ElevatedManager"] = None
    
    def __init__(self):
        self._active_elevations: Dict[str, ElevationRequest] = {}
        self._elevation_history: list = []
        self._data_path = "data/elevated_settings.json"
        self._admin_users: set = set()
        self._default_duration = 15  # minutes
        self._max_duration = 60  # minutes
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from disk."""
        try:
            import os
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, elev_data in data.get("active", {}).items():
                        elev = ElevationRequest.from_dict(elev_data)
                        if elev.is_active:
                            self._active_elevations[user_id] = elev
                    self._admin_users = set(data.get("admin_users", []))
                logger.debug(f"Loaded elevated settings, {len(self._active_elevations)} active")
        except Exception as e:
            logger.warning(f"Failed to load elevated settings: {e}")
    
    def _save_settings(self):
        """Save settings to disk."""
        try:
            import os
            os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
            data = {
                "active": {
                    user_id: elev.to_dict()
                    for user_id, elev in self._active_elevations.items()
                    if elev.is_active
                },
                "admin_users": list(self._admin_users),
            }
            with open(self._data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save elevated settings: {e}")
    
    def is_admin(self, user_id: str) -> bool:
        """Check if user is an admin."""
        return user_id in self._admin_users
    
    def add_admin(self, user_id: str):
        """Add user as admin."""
        self._admin_users.add(user_id)
        self._save_settings()
    
    def remove_admin(self, user_id: str):
        """Remove user from admin."""
        self._admin_users.discard(user_id)
        self._save_settings()
    
    def is_elevated(self, user_id: str) -> bool:
        """Check if user currently has elevated privileges."""
        if user_id in self._active_elevations:
            elev = self._active_elevations[user_id]
            if elev.is_active:
                return True
            else:
                # Cleanup expired
                del self._active_elevations[user_id]
                self._save_settings()
        return False
    
    def get_elevation(self, user_id: str) -> Optional[ElevationRequest]:
        """Get current elevation for user."""
        if self.is_elevated(user_id):
            return self._active_elevations.get(user_id)
        return None
    
    async def request_elevation(
        self,
        user_id: str,
        minutes: int = None,
        reason: ElevationReason = ElevationReason.GENERAL,
        operation: str = None,
        auto_grant: bool = True,
    ) -> ElevationRequest:
        """
        Request elevated privileges.
        
        Args:
            user_id: User requesting elevation
            minutes: Duration in minutes (default: 15, max: 60)
            reason: Reason for elevation
            operation: Description of operation
            auto_grant: Automatically grant if user is admin
            
        Returns:
            ElevationRequest object
        """
        if minutes is None:
            minutes = self._default_duration
        minutes = max(1, min(self._max_duration, minutes))
        
        now = datetime.now()
        request = ElevationRequest(
            user_id=user_id,
            reason=reason,
            requested_at=now,
            expires_at=now + timedelta(minutes=minutes),
            operation=operation,
        )
        
        # Auto-grant for admin users
        if auto_grant and self.is_admin(user_id):
            request.granted = True
            request.granted_by = "auto"
        else:
            # For now, auto-grant all requests (can be changed to require approval)
            request.granted = True
            request.granted_by = "self"
        
        self._active_elevations[user_id] = request
        self._elevation_history.append(request.to_dict())
        self._save_settings()
        
        logger.info(
            f"Elevation {'granted' if request.granted else 'requested'} for user {user_id}, "
            f"expires in {minutes} minutes"
        )
        
        return request
    
    def revoke_elevation(self, user_id: str) -> bool:
        """Revoke elevated privileges for user."""
        if user_id in self._active_elevations:
            del self._active_elevations[user_id]
            self._save_settings()
            logger.info(f"Elevation revoked for user {user_id}")
            return True
        return False
    
    def can_perform(
        self,
        user_id: str,
        action_name: str,
        auto_request: bool = False,
    ) -> bool:
        """
        Check if user can perform a specific elevated action.
        
        Args:
            user_id: User ID
            action_name: Name of the action (see ELEVATED_ACTIONS)
            auto_request: Automatically request elevation if not elevated
            
        Returns:
            True if user can perform the action
        """
        action = ELEVATED_ACTIONS.get(action_name)
        
        if action is None:
            # Unknown action, deny by default
            logger.warning(f"Unknown elevated action: {action_name}")
            return False
        
        # Admin users with auto_grant actions
        if action.auto_grant and self.is_admin(user_id):
            return True
        
        # Check if currently elevated
        if self.is_elevated(user_id):
            return True
        
        return False
    
    def require_elevation(self, action_name: str):
        """
        Decorator to require elevation for a function.
        
        Usage:
            @manager.require_elevation("file_delete")
            async def delete_file(user_id, path):
                ...
        """
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                # Try to get user_id from args/kwargs
                user_id = kwargs.get("user_id") or (args[0] if args else None)
                
                if user_id and not self.can_perform(str(user_id), action_name):
                    raise PermissionError(
                        f"Elevated privileges required for {action_name}. "
                        f"Use /elevated on to request elevation."
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_status_message(self, user_id: str) -> str:
        """Get status message for /elevated command."""
        elev = self.get_elevation(user_id)
        is_admin = self.is_admin(user_id)
        
        lines = [
            "🔐 **Elevated Mode**",
            "",
        ]
        
        if elev and elev.is_active:
            lines.extend([
                f"Status: ✅ **Active**",
                f"Remaining: {elev.remaining_minutes} minutes",
                f"Granted: {elev.granted_at.strftime('%H:%M') if hasattr(elev, 'granted_at') else 'N/A'}",
                f"Expires: {elev.expires_at.strftime('%H:%M')}",
            ])
            if elev.operation:
                lines.append(f"Operation: {elev.operation}")
        else:
            lines.append("Status: ⬜ **Not Elevated**")
        
        if is_admin:
            lines.append("\n👑 You are an admin user")
        
        lines.extend([
            "",
            "**Commands:**",
            "/elevated on [minutes] - Request elevation (default: 15)",
            "/elevated off - Revoke elevation",
            "/elevate - Alias for /elevated on",
            "",
            "**Protected Actions:**",
        ])
        
        for name, action in ELEVATED_ACTIONS.items():
            lines.append(f"• {name}: {action.description}")
        
        return "\n".join(lines)


# Singleton instance
_elevated_manager: Optional[ElevatedManager] = None


def get_elevated_manager() -> ElevatedManager:
    """Get the global elevated manager instance."""
    global _elevated_manager
    if _elevated_manager is None:
        _elevated_manager = ElevatedManager()
    return _elevated_manager


def reset_elevated_manager():
    """Reset the elevated manager (for testing)."""
    global _elevated_manager
    _elevated_manager = None


def require_elevation(action_name: str):
    """
    Decorator shortcut for requiring elevation.
    
    Usage:
        @require_elevation("file_delete")
        async def delete_file(user_id, path):
            ...
    """
    return get_elevated_manager().require_elevation(action_name)


__all__ = [
    "ElevationReason",
    "ElevationRequest",
    "ElevatedAction",
    "ElevatedManager",
    "ELEVATED_ACTIONS",
    "get_elevated_manager",
    "reset_elevated_manager",
    "require_elevation",
]
