"""
Permissions System for CursorBot

Provides:
- Group admin management
- Group whitelist/blacklist
- Elevated permissions for privileged operations
- Role-based access control
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Set

from ..utils.logger import logger


class Role(Enum):
    """User roles for access control."""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    OWNER = "owner"


class Permission(Enum):
    """Available permissions."""
    # Basic
    SEND_MESSAGE = "send_message"
    USE_COMMANDS = "use_commands"
    
    # Agent
    USE_AGENT = "use_agent"
    USE_SKILLS = "use_skills"
    
    # Advanced
    EXECUTE_CODE = "execute_code"
    FILE_ACCESS = "file_access"
    TERMINAL_ACCESS = "terminal_access"
    
    # Admin
    MANAGE_USERS = "manage_users"
    MANAGE_GROUP = "manage_group"
    MANAGE_BOT = "manage_bot"
    
    # Elevated
    ELEVATED_OPERATIONS = "elevated_operations"
    SYSTEM_ACCESS = "system_access"


# Default permissions by role
ROLE_PERMISSIONS = {
    Role.USER: {
        Permission.SEND_MESSAGE,
        Permission.USE_COMMANDS,
        Permission.USE_AGENT,
        Permission.USE_SKILLS,
    },
    Role.MODERATOR: {
        Permission.SEND_MESSAGE,
        Permission.USE_COMMANDS,
        Permission.USE_AGENT,
        Permission.USE_SKILLS,
        Permission.EXECUTE_CODE,
        Permission.FILE_ACCESS,
        Permission.MANAGE_USERS,
    },
    Role.ADMIN: {
        Permission.SEND_MESSAGE,
        Permission.USE_COMMANDS,
        Permission.USE_AGENT,
        Permission.USE_SKILLS,
        Permission.EXECUTE_CODE,
        Permission.FILE_ACCESS,
        Permission.TERMINAL_ACCESS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_GROUP,
    },
    Role.OWNER: set(Permission),  # All permissions
}


@dataclass
class UserPermissions:
    """Permissions for a specific user."""
    user_id: int
    role: Role = Role.USER
    custom_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    elevated_until: Optional[datetime] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        # Check denied first
        if permission in self.denied_permissions:
            return False
        
        # Check custom permissions
        if permission in self.custom_permissions:
            return True
        
        # Check elevated
        if permission == Permission.ELEVATED_OPERATIONS:
            if self.elevated_until and datetime.now() < self.elevated_until:
                return True
        
        # Check role permissions
        return permission in ROLE_PERMISSIONS.get(self.role, set())
    
    def grant_permission(self, permission: Permission) -> None:
        """Grant a specific permission."""
        self.custom_permissions.add(permission)
        self.denied_permissions.discard(permission)
    
    def revoke_permission(self, permission: Permission) -> None:
        """Revoke a specific permission."""
        self.custom_permissions.discard(permission)
        self.denied_permissions.add(permission)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "custom_permissions": [p.value for p in self.custom_permissions],
            "denied_permissions": [p.value for p in self.denied_permissions],
            "elevated_until": self.elevated_until.isoformat() if self.elevated_until else None,
        }


@dataclass
class GroupSettings:
    """Settings for a specific group."""
    group_id: int
    enabled: bool = True
    whitelist_mode: bool = False  # If True, only whitelisted users can use bot
    whitelist: Set[int] = field(default_factory=set)
    blacklist: Set[int] = field(default_factory=set)
    admins: Set[int] = field(default_factory=set)
    moderators: Set[int] = field(default_factory=set)
    allowed_commands: Set[str] = field(default_factory=set)  # Empty = all commands
    disabled_commands: Set[str] = field(default_factory=set)
    rate_limit: int = 0  # Messages per minute, 0 = no limit
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use bot in this group."""
        if not self.enabled:
            return False
        
        if user_id in self.blacklist:
            return False
        
        if self.whitelist_mode:
            return user_id in self.whitelist or user_id in self.admins
        
        return True
    
    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed in this group."""
        if command in self.disabled_commands:
            return False
        
        if self.allowed_commands and command not in self.allowed_commands:
            return False
        
        return True
    
    def get_user_role(self, user_id: int) -> Role:
        """Get user's role in this group."""
        if user_id in self.admins:
            return Role.ADMIN
        if user_id in self.moderators:
            return Role.MODERATOR
        return Role.USER
    
    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "enabled": self.enabled,
            "whitelist_mode": self.whitelist_mode,
            "whitelist_count": len(self.whitelist),
            "blacklist_count": len(self.blacklist),
            "admin_count": len(self.admins),
            "moderator_count": len(self.moderators),
        }


class PermissionManager:
    """
    Manages permissions for users and groups.
    """
    
    def __init__(self):
        self._user_permissions: dict[int, UserPermissions] = {}
        self._group_settings: dict[int, GroupSettings] = {}
        self._global_admins: Set[int] = set()
        self._global_blacklist: Set[int] = set()
    
    # ============================================
    # Global Settings
    # ============================================
    
    def add_global_admin(self, user_id: int) -> None:
        """Add a global admin."""
        self._global_admins.add(user_id)
        logger.info(f"Added global admin: {user_id}")
    
    def remove_global_admin(self, user_id: int) -> None:
        """Remove a global admin."""
        self._global_admins.discard(user_id)
        logger.info(f"Removed global admin: {user_id}")
    
    def is_global_admin(self, user_id: int) -> bool:
        """Check if user is a global admin."""
        return user_id in self._global_admins
    
    def add_to_global_blacklist(self, user_id: int) -> None:
        """Add user to global blacklist."""
        self._global_blacklist.add(user_id)
        logger.info(f"Added to global blacklist: {user_id}")
    
    def remove_from_global_blacklist(self, user_id: int) -> None:
        """Remove user from global blacklist."""
        self._global_blacklist.discard(user_id)
    
    def is_globally_blacklisted(self, user_id: int) -> bool:
        """Check if user is globally blacklisted."""
        return user_id in self._global_blacklist
    
    # ============================================
    # User Permissions
    # ============================================
    
    def get_user_permissions(self, user_id: int) -> UserPermissions:
        """Get or create permissions for a user."""
        if user_id not in self._user_permissions:
            self._user_permissions[user_id] = UserPermissions(user_id=user_id)
        return self._user_permissions[user_id]
    
    def set_user_role(self, user_id: int, role: Role) -> None:
        """Set user's global role."""
        perms = self.get_user_permissions(user_id)
        perms.role = role
        logger.info(f"Set user {user_id} role to {role.value}")
    
    def check_permission(
        self,
        user_id: int,
        permission: Permission,
        group_id: int = None,
    ) -> bool:
        """
        Check if user has a permission.
        
        Args:
            user_id: User ID
            permission: Permission to check
            group_id: Optional group ID for group-specific checks
        
        Returns:
            True if user has permission
        """
        # Global blacklist check
        if self.is_globally_blacklisted(user_id):
            return False
        
        # Global admin bypass
        if self.is_global_admin(user_id):
            return True
        
        # Get user permissions
        user_perms = self.get_user_permissions(user_id)
        
        # Group-specific check
        if group_id:
            group = self.get_group_settings(group_id)
            
            # Check if user is allowed in group
            if not group.is_user_allowed(user_id):
                return False
            
            # Check group role
            group_role = group.get_user_role(user_id)
            if group_role.value > user_perms.role.value:
                # Use group role if higher
                return permission in ROLE_PERMISSIONS.get(group_role, set())
        
        return user_perms.has_permission(permission)
    
    # ============================================
    # Elevated Permissions
    # ============================================
    
    def elevate_user(self, user_id: int, duration_minutes: int = 30) -> bool:
        """
        Grant temporary elevated permissions.
        
        Args:
            user_id: User to elevate
            duration_minutes: Duration of elevation
        
        Returns:
            True if successful
        """
        from datetime import timedelta
        
        perms = self.get_user_permissions(user_id)
        perms.elevated_until = datetime.now() + timedelta(minutes=duration_minutes)
        logger.info(f"Elevated user {user_id} for {duration_minutes} minutes")
        return True
    
    def revoke_elevation(self, user_id: int) -> None:
        """Revoke elevated permissions."""
        perms = self.get_user_permissions(user_id)
        perms.elevated_until = None
        logger.info(f"Revoked elevation for user {user_id}")
    
    def is_elevated(self, user_id: int) -> bool:
        """Check if user is currently elevated."""
        perms = self.get_user_permissions(user_id)
        if perms.elevated_until:
            return datetime.now() < perms.elevated_until
        return False
    
    # ============================================
    # Group Settings
    # ============================================
    
    def get_group_settings(self, group_id: int) -> GroupSettings:
        """Get or create settings for a group."""
        if group_id not in self._group_settings:
            self._group_settings[group_id] = GroupSettings(group_id=group_id)
        return self._group_settings[group_id]
    
    def set_group_enabled(self, group_id: int, enabled: bool) -> None:
        """Enable or disable bot in a group."""
        group = self.get_group_settings(group_id)
        group.enabled = enabled
        logger.info(f"Set group {group_id} enabled: {enabled}")
    
    def set_group_whitelist_mode(self, group_id: int, enabled: bool) -> None:
        """Enable or disable whitelist mode for a group."""
        group = self.get_group_settings(group_id)
        group.whitelist_mode = enabled
        logger.info(f"Set group {group_id} whitelist mode: {enabled}")
    
    def add_group_admin(self, group_id: int, user_id: int) -> None:
        """Add admin to a group."""
        group = self.get_group_settings(group_id)
        group.admins.add(user_id)
        group.moderators.discard(user_id)  # Remove from moderators if present
        logger.info(f"Added admin {user_id} to group {group_id}")
    
    def remove_group_admin(self, group_id: int, user_id: int) -> None:
        """Remove admin from a group."""
        group = self.get_group_settings(group_id)
        group.admins.discard(user_id)
    
    def add_group_moderator(self, group_id: int, user_id: int) -> None:
        """Add moderator to a group."""
        group = self.get_group_settings(group_id)
        if user_id not in group.admins:  # Don't demote admins
            group.moderators.add(user_id)
            logger.info(f"Added moderator {user_id} to group {group_id}")
    
    def add_to_whitelist(self, group_id: int, user_id: int) -> None:
        """Add user to group whitelist."""
        group = self.get_group_settings(group_id)
        group.whitelist.add(user_id)
        group.blacklist.discard(user_id)
    
    def add_to_blacklist(self, group_id: int, user_id: int) -> None:
        """Add user to group blacklist."""
        group = self.get_group_settings(group_id)
        group.blacklist.add(user_id)
        group.whitelist.discard(user_id)
    
    def disable_command_in_group(self, group_id: int, command: str) -> None:
        """Disable a command in a group."""
        group = self.get_group_settings(group_id)
        group.disabled_commands.add(command)
    
    def enable_command_in_group(self, group_id: int, command: str) -> None:
        """Enable a command in a group."""
        group = self.get_group_settings(group_id)
        group.disabled_commands.discard(command)
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_stats(self) -> dict:
        """Get permission system statistics."""
        return {
            "global_admins": len(self._global_admins),
            "global_blacklist": len(self._global_blacklist),
            "users_with_permissions": len(self._user_permissions),
            "groups_configured": len(self._group_settings),
            "elevated_users": sum(
                1 for p in self._user_permissions.values()
                if p.elevated_until and datetime.now() < p.elevated_until
            ),
        }


# ============================================
# Global Instance
# ============================================

_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get the global permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def require_permission(permission: Permission):
    """
    Decorator to require a permission for a handler.
    
    Usage:
        @require_permission(Permission.EXECUTE_CODE)
        async def execute_code_handler(update, context):
            ...
    """
    def decorator(func):
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            group_id = update.effective_chat.id if update.effective_chat.type != "private" else None
            
            manager = get_permission_manager()
            if not manager.check_permission(user_id, permission, group_id):
                await update.message.reply_text(
                    f"You don't have permission for this action.\n"
                    f"Required: {permission.value}"
                )
                return
            
            return await func(update, context, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


__all__ = [
    "Role",
    "Permission",
    "UserPermissions",
    "GroupSettings",
    "PermissionManager",
    "get_permission_manager",
    "require_permission",
]
