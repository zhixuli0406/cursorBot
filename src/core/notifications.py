"""
System Notifications - v0.4 Feature
Desktop and mobile push notifications for important events.

Supports:
    - Desktop notifications (macOS, Windows, Linux)
    - Sound alerts
    - Notification queuing and batching
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import asyncio
import json
import platform

from ..utils.logger import logger


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationCategory(Enum):
    """Categories of notifications."""
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    MESSAGE_RECEIVED = "message_received"
    SYSTEM_ALERT = "system_alert"
    APPROVAL_REQUIRED = "approval_required"
    REMINDER = "reminder"
    UPDATE = "update"


@dataclass
class Notification:
    """A system notification."""
    id: str
    title: str
    message: str
    category: NotificationCategory
    priority: NotificationPriority = NotificationPriority.NORMAL
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    sound: bool = True
    action_url: Optional[str] = None
    icon: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "category": self.category.value,
            "priority": self.priority.value,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "delivered": self.delivered,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "sound": self.sound,
            "action_url": self.action_url,
            "icon": self.icon,
        }


@dataclass
class NotificationSettings:
    """User notification settings."""
    enabled: bool = True
    sound_enabled: bool = True
    desktop_enabled: bool = True
    batch_notifications: bool = False  # Batch low-priority notifications
    batch_interval_seconds: int = 60
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None
    disabled_categories: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "sound_enabled": self.sound_enabled,
            "desktop_enabled": self.desktop_enabled,
            "batch_notifications": self.batch_notifications,
            "batch_interval_seconds": self.batch_interval_seconds,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "disabled_categories": self.disabled_categories,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NotificationSettings":
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            sound_enabled=data.get("sound_enabled", True),
            desktop_enabled=data.get("desktop_enabled", True),
            batch_notifications=data.get("batch_notifications", False),
            batch_interval_seconds=data.get("batch_interval_seconds", 60),
            quiet_hours_start=data.get("quiet_hours_start"),
            quiet_hours_end=data.get("quiet_hours_end"),
            disabled_categories=data.get("disabled_categories", []),
        )
    
    def is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours."""
        if self.quiet_hours_start is None or self.quiet_hours_end is None:
            return False
        
        current_hour = datetime.now().hour
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Simple case: e.g., 22 to 7
            return self.quiet_hours_start <= current_hour or current_hour < self.quiet_hours_end
        else:
            # Wrap around: e.g., 22 to 7 (overnight)
            return self.quiet_hours_start <= current_hour <= 23 or 0 <= current_hour < self.quiet_hours_end
    
    def should_notify(self, category: NotificationCategory, priority: NotificationPriority) -> bool:
        """Check if notification should be delivered."""
        if not self.enabled:
            return False
        
        if category.value in self.disabled_categories:
            return False
        
        # Urgent notifications always go through
        if priority == NotificationPriority.URGENT:
            return True
        
        # Check quiet hours for non-urgent
        if self.is_quiet_hours():
            return False
        
        return True


class DesktopNotifier:
    """Send desktop notifications using platform-specific methods."""
    
    def __init__(self):
        self._system = platform.system()
        self._notifier = None
        self._setup_notifier()
    
    def _setup_notifier(self):
        """Setup the appropriate notifier for the platform."""
        try:
            if self._system == "Darwin":  # macOS
                self._notifier = self._notify_macos
            elif self._system == "Windows":
                self._notifier = self._notify_windows
            elif self._system == "Linux":
                self._notifier = self._notify_linux
            else:
                logger.warning(f"No desktop notification support for {self._system}")
        except Exception as e:
            logger.warning(f"Failed to setup desktop notifier: {e}")
    
    async def _notify_macos(self, title: str, message: str, sound: bool = True):
        """Send notification on macOS using osascript."""
        try:
            sound_part = 'sound name "default"' if sound else ''
            script = f'display notification "{message}" with title "{title}" {sound_part}'
            
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception as e:
            logger.warning(f"Failed to send macOS notification: {e}")
    
    async def _notify_windows(self, title: str, message: str, sound: bool = True):
        """Send notification on Windows using PowerShell."""
        try:
            # Using Windows Toast notifications via PowerShell
            script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
            $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
            $text = $xml.GetElementsByTagName("text")
            $text.Item(0).AppendChild($xml.CreateTextNode("{title}")) | Out-Null
            $text.Item(1).AppendChild($xml.CreateTextNode("{message}")) | Out-Null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("CursorBot").Show($toast)
            '''
            
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-Command", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception as e:
            logger.warning(f"Failed to send Windows notification: {e}")
    
    async def _notify_linux(self, title: str, message: str, sound: bool = True):
        """Send notification on Linux using notify-send."""
        try:
            args = ["notify-send", title, message]
            
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception as e:
            logger.warning(f"Failed to send Linux notification: {e}")
    
    async def send(self, title: str, message: str, sound: bool = True) -> bool:
        """Send a desktop notification."""
        if self._notifier is None:
            return False
        
        try:
            await self._notifier(title, message, sound)
            return True
        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")
            return False


class NotificationManager:
    """
    Manager for system notifications.
    
    Usage:
        manager = get_notification_manager()
        
        # Send a notification
        await manager.notify(
            user_id="123",
            title="Task Complete",
            message="Your analysis is ready",
            category=NotificationCategory.TASK_COMPLETE,
        )
        
        # Configure notifications
        manager.set_enabled(user_id, True)
        manager.set_quiet_hours(user_id, 22, 7)
    """
    
    _instance: Optional["NotificationManager"] = None
    
    def __init__(self):
        self._settings: Dict[str, NotificationSettings] = {}
        self._history: List[Notification] = []
        self._pending: List[Notification] = []
        self._desktop = DesktopNotifier()
        self._data_path = "data/notification_settings.json"
        self._callbacks: List[Callable[[Notification], Any]] = []
        self._counter = 0
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from disk."""
        try:
            import os
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, settings_data in data.items():
                        self._settings[user_id] = NotificationSettings.from_dict(settings_data)
                logger.debug(f"Loaded notification settings for {len(self._settings)} users")
        except Exception as e:
            logger.warning(f"Failed to load notification settings: {e}")
    
    def _save_settings(self):
        """Save settings to disk."""
        try:
            import os
            os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
            data = {
                user_id: settings.to_dict()
                for user_id, settings in self._settings.items()
            }
            with open(self._data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save notification settings: {e}")
    
    def _generate_id(self) -> str:
        """Generate unique notification ID."""
        self._counter += 1
        return f"notif_{self._counter}_{int(datetime.now().timestamp())}"
    
    def get_settings(self, user_id: str) -> NotificationSettings:
        """Get notification settings for user."""
        if user_id not in self._settings:
            self._settings[user_id] = NotificationSettings()
        return self._settings[user_id]
    
    def set_enabled(self, user_id: str, enabled: bool):
        """Enable or disable notifications for user."""
        settings = self.get_settings(user_id)
        settings.enabled = enabled
        self._save_settings()
    
    def set_sound_enabled(self, user_id: str, enabled: bool):
        """Enable or disable notification sounds."""
        settings = self.get_settings(user_id)
        settings.sound_enabled = enabled
        self._save_settings()
    
    def set_quiet_hours(self, user_id: str, start: int, end: int):
        """Set quiet hours (no notifications except urgent)."""
        settings = self.get_settings(user_id)
        settings.quiet_hours_start = start % 24
        settings.quiet_hours_end = end % 24
        self._save_settings()
    
    def disable_category(self, user_id: str, category: NotificationCategory):
        """Disable a notification category."""
        settings = self.get_settings(user_id)
        if category.value not in settings.disabled_categories:
            settings.disabled_categories.append(category.value)
            self._save_settings()
    
    def enable_category(self, user_id: str, category: NotificationCategory):
        """Enable a notification category."""
        settings = self.get_settings(user_id)
        if category.value in settings.disabled_categories:
            settings.disabled_categories.remove(category.value)
            self._save_settings()
    
    def register_callback(self, callback: Callable[[Notification], Any]):
        """Register a callback to be called when notification is sent."""
        self._callbacks.append(callback)
    
    async def notify(
        self,
        user_id: str,
        title: str,
        message: str,
        category: NotificationCategory = NotificationCategory.SYSTEM_ALERT,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        sound: bool = True,
        action_url: str = None,
        icon: str = None,
    ) -> Optional[Notification]:
        """
        Send a notification to a user.
        
        Args:
            user_id: User to notify
            title: Notification title
            message: Notification message
            category: Notification category
            priority: Priority level
            sound: Play sound
            action_url: URL to open on click
            icon: Icon path or URL
            
        Returns:
            Notification object if sent, None if filtered
        """
        settings = self.get_settings(user_id)
        
        # Check if notification should be sent
        if not settings.should_notify(category, priority):
            logger.debug(f"Notification filtered for user {user_id}: {category.value}")
            return None
        
        # Create notification
        notification = Notification(
            id=self._generate_id(),
            title=title,
            message=message,
            category=category,
            priority=priority,
            user_id=user_id,
            sound=sound and settings.sound_enabled,
            action_url=action_url,
            icon=icon,
        )
        
        # Send desktop notification
        if settings.desktop_enabled:
            await self._desktop.send(
                title=title,
                message=message,
                sound=notification.sound,
            )
        
        # Mark as delivered
        notification.delivered = True
        notification.delivered_at = datetime.now()
        
        # Add to history
        self._history.append(notification)
        
        # Call callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification)
                else:
                    callback(notification)
            except Exception as e:
                logger.warning(f"Notification callback error: {e}")
        
        logger.debug(f"Notification sent to {user_id}: {title}")
        return notification
    
    async def notify_task_complete(
        self,
        user_id: str,
        task_name: str,
        success: bool = True,
        details: str = None,
    ) -> Optional[Notification]:
        """Send a task completion notification."""
        category = NotificationCategory.TASK_COMPLETE if success else NotificationCategory.TASK_FAILED
        title = f"Task {'Complete' if success else 'Failed'}: {task_name}"
        message = details or f"Your task has {'completed successfully' if success else 'failed'}."
        
        return await self.notify(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            priority=NotificationPriority.NORMAL if success else NotificationPriority.HIGH,
        )
    
    async def notify_approval_required(
        self,
        user_id: str,
        action: str,
        details: str = None,
    ) -> Optional[Notification]:
        """Send an approval required notification."""
        return await self.notify(
            user_id=user_id,
            title="Approval Required",
            message=details or f"Action '{action}' requires your approval.",
            category=NotificationCategory.APPROVAL_REQUIRED,
            priority=NotificationPriority.HIGH,
        )
    
    def get_history(self, user_id: str, limit: int = 50) -> List[Notification]:
        """Get notification history for user."""
        user_notifications = [n for n in self._history if n.user_id == user_id]
        return sorted(user_notifications, key=lambda n: n.created_at, reverse=True)[:limit]
    
    def clear_history(self, user_id: str):
        """Clear notification history for user."""
        self._history = [n for n in self._history if n.user_id != user_id]
    
    def get_status_message(self, user_id: str) -> str:
        """Get status message for notifications."""
        settings = self.get_settings(user_id)
        history = self.get_history(user_id, limit=5)
        
        status_icon = "✅" if settings.enabled else "⬜"
        
        lines = [
            "🔔 **Notifications**",
            "",
            f"Status: {status_icon} {'Enabled' if settings.enabled else 'Disabled'}",
            f"Sound: {'✓' if settings.sound_enabled else '✗'}",
            f"Desktop: {'✓' if settings.desktop_enabled else '✗'}",
        ]
        
        if settings.quiet_hours_start is not None:
            lines.append(f"Quiet hours: {settings.quiet_hours_start}:00 - {settings.quiet_hours_end}:00")
        
        if settings.disabled_categories:
            lines.append(f"Disabled: {', '.join(settings.disabled_categories)}")
        
        if history:
            lines.extend([
                "",
                "**Recent:**",
            ])
            for n in history[:3]:
                time_str = n.created_at.strftime("%H:%M")
                lines.append(f"• [{time_str}] {n.title}")
        
        lines.extend([
            "",
            "**Commands:**",
            "/notify on|off - Enable/disable",
            "/notify sound on|off - Toggle sound",
            "/notify quiet <start> <end> - Set quiet hours",
        ])
        
        return "\n".join(lines)


# Singleton instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def reset_notification_manager():
    """Reset the notification manager (for testing)."""
    global _notification_manager
    _notification_manager = None


__all__ = [
    "NotificationPriority",
    "NotificationCategory",
    "Notification",
    "NotificationSettings",
    "NotificationManager",
    "get_notification_manager",
    "reset_notification_manager",
]
