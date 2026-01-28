"""
Minimal Permissions Module - v0.4 Feature
Platform-specific minimal permission configuration.

Documents and enforces the minimum permissions required for each platform.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from ..utils.logger import logger


class Platform(Enum):
    """Supported platforms."""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    LINE = "line"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    TEAMS = "teams"
    GOOGLE_CHAT = "google_chat"
    SIGNAL = "signal"


class PermissionScope(Enum):
    """Permission scopes."""
    # Message permissions
    READ_MESSAGES = "read_messages"
    SEND_MESSAGES = "send_messages"
    EDIT_MESSAGES = "edit_messages"
    DELETE_MESSAGES = "delete_messages"
    
    # User permissions
    READ_USER_INFO = "read_user_info"
    READ_USER_PRESENCE = "read_user_presence"
    
    # Channel/Group permissions
    READ_CHANNELS = "read_channels"
    MANAGE_CHANNELS = "manage_channels"
    
    # Media permissions
    SEND_MEDIA = "send_media"
    READ_MEDIA = "read_media"
    
    # Webhook permissions
    RECEIVE_WEBHOOKS = "receive_webhooks"
    
    # Voice permissions
    VOICE_CONNECT = "voice_connect"
    VOICE_SPEAK = "voice_speak"
    
    # Admin permissions
    ADMIN = "admin"
    BAN_USERS = "ban_users"
    KICK_USERS = "kick_users"


@dataclass
class PlatformPermissions:
    """Permission requirements for a platform."""
    platform: Platform
    required: Set[PermissionScope] = field(default_factory=set)
    optional: Set[PermissionScope] = field(default_factory=set)
    description: str = ""
    setup_url: str = ""
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "required": [p.value for p in self.required],
            "optional": [p.value for p in self.optional],
            "description": self.description,
            "setup_url": self.setup_url,
        }


# Minimal permissions for each platform
PLATFORM_PERMISSIONS: Dict[Platform, PlatformPermissions] = {
    Platform.TELEGRAM: PlatformPermissions(
        platform=Platform.TELEGRAM,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
            PermissionScope.READ_USER_INFO,
        },
        optional={
            PermissionScope.EDIT_MESSAGES,
            PermissionScope.DELETE_MESSAGES,
            PermissionScope.SEND_MEDIA,
            PermissionScope.READ_MEDIA,
        },
        description="Telegram Bot API permissions",
        setup_url="https://core.telegram.org/bots#botfather",
    ),
    
    Platform.DISCORD: PlatformPermissions(
        platform=Platform.DISCORD,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
            PermissionScope.READ_USER_INFO,
        },
        optional={
            PermissionScope.EDIT_MESSAGES,
            PermissionScope.DELETE_MESSAGES,
            PermissionScope.SEND_MEDIA,
            PermissionScope.VOICE_CONNECT,
            PermissionScope.VOICE_SPEAK,
            PermissionScope.READ_CHANNELS,
        },
        description="Discord Bot permissions (integers: 274877975552)",
        setup_url="https://discord.com/developers/applications",
    ),
    
    Platform.LINE: PlatformPermissions(
        platform=Platform.LINE,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
            PermissionScope.RECEIVE_WEBHOOKS,
        },
        optional={
            PermissionScope.READ_USER_INFO,
            PermissionScope.SEND_MEDIA,
        },
        description="LINE Messaging API permissions",
        setup_url="https://developers.line.biz/console/",
    ),
    
    Platform.SLACK: PlatformPermissions(
        platform=Platform.SLACK,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
            PermissionScope.RECEIVE_WEBHOOKS,
        },
        optional={
            PermissionScope.READ_USER_INFO,
            PermissionScope.READ_CHANNELS,
            PermissionScope.SEND_MEDIA,
        },
        description="Slack Bot OAuth Scopes: chat:write, channels:history, users:read",
        setup_url="https://api.slack.com/apps",
    ),
    
    Platform.WHATSAPP: PlatformPermissions(
        platform=Platform.WHATSAPP,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
            PermissionScope.RECEIVE_WEBHOOKS,
        },
        optional={
            PermissionScope.SEND_MEDIA,
            PermissionScope.READ_MEDIA,
        },
        description="WhatsApp Cloud API permissions",
        setup_url="https://developers.facebook.com/apps/",
    ),
    
    Platform.TEAMS: PlatformPermissions(
        platform=Platform.TEAMS,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
            PermissionScope.RECEIVE_WEBHOOKS,
        },
        optional={
            PermissionScope.READ_USER_INFO,
            PermissionScope.READ_CHANNELS,
        },
        description="Microsoft Teams Bot Framework permissions",
        setup_url="https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps",
    ),
    
    Platform.GOOGLE_CHAT: PlatformPermissions(
        platform=Platform.GOOGLE_CHAT,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
            PermissionScope.RECEIVE_WEBHOOKS,
        },
        optional={
            PermissionScope.READ_USER_INFO,
        },
        description="Google Chat API permissions",
        setup_url="https://console.cloud.google.com/apis/credentials",
    ),
    
    Platform.SIGNAL: PlatformPermissions(
        platform=Platform.SIGNAL,
        required={
            PermissionScope.READ_MESSAGES,
            PermissionScope.SEND_MESSAGES,
        },
        optional={
            PermissionScope.SEND_MEDIA,
        },
        description="Signal (via signal-cli) - requires registered phone number",
        setup_url="https://github.com/AsamK/signal-cli",
    ),
}


@dataclass
class PermissionAudit:
    """Result of a permission audit."""
    platform: Platform
    granted: Set[PermissionScope]
    missing_required: Set[PermissionScope]
    missing_optional: Set[PermissionScope]
    is_valid: bool
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "granted": [p.value for p in self.granted],
            "missing_required": [p.value for p in self.missing_required],
            "missing_optional": [p.value for p in self.missing_optional],
            "is_valid": self.is_valid,
            "warnings": self.warnings,
        }


class MinimalPermissionsManager:
    """
    Manager for platform permissions.
    
    Usage:
        manager = get_permissions_manager()
        
        # Get required permissions for platform
        perms = manager.get_required_permissions(Platform.DISCORD)
        
        # Audit current permissions
        audit = manager.audit_permissions(Platform.DISCORD, granted_scopes)
    """
    
    _instance: Optional["MinimalPermissionsManager"] = None
    
    def __init__(self):
        self._permissions = PLATFORM_PERMISSIONS.copy()
        self._granted: Dict[Platform, Set[PermissionScope]] = {}
    
    def get_platform_permissions(self, platform: Platform) -> PlatformPermissions:
        """Get permission configuration for platform."""
        return self._permissions.get(platform)
    
    def get_required_permissions(self, platform: Platform) -> Set[PermissionScope]:
        """Get required permissions for platform."""
        perms = self._permissions.get(platform)
        return perms.required if perms else set()
    
    def get_optional_permissions(self, platform: Platform) -> Set[PermissionScope]:
        """Get optional permissions for platform."""
        perms = self._permissions.get(platform)
        return perms.optional if perms else set()
    
    def set_granted_permissions(
        self,
        platform: Platform,
        scopes: Set[PermissionScope],
    ):
        """Set granted permissions for platform."""
        self._granted[platform] = scopes
    
    def audit_permissions(
        self,
        platform: Platform,
        granted: Set[PermissionScope] = None,
    ) -> PermissionAudit:
        """
        Audit permissions for a platform.
        
        Returns audit result with missing permissions.
        """
        if granted is None:
            granted = self._granted.get(platform, set())
        
        perms = self._permissions.get(platform)
        if not perms:
            return PermissionAudit(
                platform=platform,
                granted=granted,
                missing_required=set(),
                missing_optional=set(),
                is_valid=True,
                warnings=["Unknown platform, skipping audit"],
            )
        
        missing_required = perms.required - granted
        missing_optional = perms.optional - granted
        
        warnings = []
        
        if missing_required:
            warnings.append(
                f"Missing required permissions: {', '.join(p.value for p in missing_required)}"
            )
        
        if missing_optional:
            warnings.append(
                f"Missing optional permissions (some features may not work): "
                f"{', '.join(p.value for p in missing_optional)}"
            )
        
        return PermissionAudit(
            platform=platform,
            granted=granted,
            missing_required=missing_required,
            missing_optional=missing_optional,
            is_valid=len(missing_required) == 0,
            warnings=warnings,
        )
    
    def has_permission(
        self,
        platform: Platform,
        scope: PermissionScope,
    ) -> bool:
        """Check if platform has a specific permission."""
        granted = self._granted.get(platform, set())
        return scope in granted
    
    def get_setup_instructions(self, platform: Platform) -> str:
        """Get setup instructions for platform permissions."""
        perms = self._permissions.get(platform)
        if not perms:
            return f"Unknown platform: {platform.value}"
        
        lines = [
            f"🔐 **{platform.value.upper()} Permission Setup**",
            "",
            perms.description,
            "",
            "**Required Permissions:**",
        ]
        
        for p in perms.required:
            lines.append(f"  • {p.value}")
        
        if perms.optional:
            lines.append("")
            lines.append("**Optional Permissions:**")
            for p in perms.optional:
                lines.append(f"  • {p.value}")
        
        lines.extend([
            "",
            f"**Setup URL:** {perms.setup_url}",
        ])
        
        return "\n".join(lines)
    
    def get_all_platforms_status(self) -> List[dict]:
        """Get permission status for all platforms."""
        result = []
        
        for platform in Platform:
            audit = self.audit_permissions(platform)
            result.append({
                "platform": platform.value,
                "configured": platform in self._granted,
                "valid": audit.is_valid,
                "missing_required": len(audit.missing_required),
                "missing_optional": len(audit.missing_optional),
            })
        
        return result
    
    def get_status_message(self) -> str:
        """Get formatted status message."""
        lines = [
            "🔐 **Platform Permissions**",
            "",
        ]
        
        for platform in Platform:
            perms = self._permissions.get(platform)
            granted = self._granted.get(platform, set())
            
            if platform in self._granted:
                audit = self.audit_permissions(platform)
                if audit.is_valid:
                    status = "✅"
                else:
                    status = "⚠️"
            else:
                status = "⬜"
            
            required_count = len(perms.required) if perms else 0
            granted_count = len(granted & perms.required) if perms else 0
            
            lines.append(
                f"{status} {platform.value}: {granted_count}/{required_count} required"
            )
        
        lines.extend([
            "",
            "Use `/permissions <platform>` to see details",
        ])
        
        return "\n".join(lines)


# Singleton instance
_permissions_manager: Optional[MinimalPermissionsManager] = None


def get_minimal_permissions_manager() -> MinimalPermissionsManager:
    """Get the global permissions manager instance."""
    global _permissions_manager
    if _permissions_manager is None:
        _permissions_manager = MinimalPermissionsManager()
    return _permissions_manager


def reset_minimal_permissions_manager():
    """Reset the permissions manager (for testing)."""
    global _permissions_manager
    _permissions_manager = None


__all__ = [
    "Platform",
    "PermissionScope",
    "PlatformPermissions",
    "PermissionAudit",
    "MinimalPermissionsManager",
    "PLATFORM_PERMISSIONS",
    "get_minimal_permissions_manager",
    "reset_minimal_permissions_manager",
]
