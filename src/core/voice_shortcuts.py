"""
System Shortcuts Integration for CursorBot v1.1

Provides integration with system automation:
- macOS Shortcuts (formerly Automator)
- iOS Shortcuts (Siri Shortcuts)
- Android Intents
- System notification interaction

Usage:
    from src.core.voice_shortcuts import (
        ShortcutsManager,
        AndroidIntentHandler,
        NotificationInteraction,
    )
"""

import asyncio
import json
import platform
import subprocess
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..utils.logger import logger


# ============================================
# macOS/iOS Shortcuts Integration
# ============================================

class ShortcutType(Enum):
    """Types of shortcuts."""
    MACOS_SHORTCUT = "macos_shortcut"
    IOS_SHORTCUT = "ios_shortcut"
    AUTOMATOR = "automator"
    APPLE_SCRIPT = "apple_script"


@dataclass
class Shortcut:
    """A system shortcut."""
    name: str
    shortcut_type: ShortcutType
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    trigger_phrases: List[str] = field(default_factory=list)


class MacOSShortcutsManager:
    """
    Manages macOS Shortcuts integration.
    
    Features:
    - List available shortcuts
    - Run shortcuts by name
    - Pass parameters to shortcuts
    - Receive results
    """
    
    def __init__(self):
        self._system = platform.system()
        self._shortcuts_cache: List[Shortcut] = []
        self._last_refresh = None
    
    async def list_shortcuts(self, refresh: bool = False) -> List[Shortcut]:
        """List all available shortcuts."""
        if self._system != "Darwin":
            return []
        
        # Use cache if recent
        if not refresh and self._shortcuts_cache and self._last_refresh:
            age = (datetime.now() - self._last_refresh).total_seconds()
            if age < 300:  # 5 minutes cache
                return self._shortcuts_cache
        
        try:
            # Use shortcuts command-line tool
            process = await asyncio.create_subprocess_exec(
                "shortcuts", "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                shortcuts = []
                for line in stdout.decode().strip().split("\n"):
                    if line:
                        shortcuts.append(Shortcut(
                            name=line.strip(),
                            shortcut_type=ShortcutType.MACOS_SHORTCUT,
                        ))
                
                self._shortcuts_cache = shortcuts
                self._last_refresh = datetime.now()
                return shortcuts
                
        except Exception as e:
            logger.error(f"List shortcuts error: {e}")
        
        return []
    
    async def run_shortcut(
        self,
        name: str,
        input_data: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Run a shortcut by name.
        
        Args:
            name: Shortcut name
            input_data: Optional input to pass
            
        Returns:
            (success, output)
        """
        if self._system != "Darwin":
            return False, "僅支援 macOS"
        
        try:
            cmd = ["shortcuts", "run", name]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdin_data = input_data.encode() if input_data else None
            stdout, stderr = await process.communicate(stdin_data)
            
            if process.returncode == 0:
                output = stdout.decode().strip()
                return True, output or "捷徑執行成功"
            else:
                error = stderr.decode().strip()
                return False, f"執行失敗：{error}"
                
        except FileNotFoundError:
            return False, "找不到 shortcuts 指令，請確認已安裝 macOS Shortcuts"
        except Exception as e:
            logger.error(f"Run shortcut error: {e}")
            return False, f"執行錯誤：{str(e)}"
    
    async def create_shortcut(
        self,
        name: str,
        actions: List[Dict[str, Any]]
    ) -> bool:
        """
        Create a new shortcut programmatically.
        
        Note: This requires user interaction on macOS.
        """
        # macOS Shortcuts don't support programmatic creation from command line
        # Would need to use Shortcuts app or x-callback-url
        logger.warning("Shortcut creation requires manual setup in Shortcuts app")
        return False
    
    def get_shortcut_by_phrase(self, phrase: str) -> Optional[Shortcut]:
        """Find shortcut by trigger phrase."""
        phrase_lower = phrase.lower()
        
        for shortcut in self._shortcuts_cache:
            if phrase_lower in shortcut.name.lower():
                return shortcut
            
            for trigger in shortcut.trigger_phrases:
                if trigger.lower() in phrase_lower:
                    return shortcut
        
        return None


class AppleScriptRunner:
    """
    Runs AppleScript for macOS automation.
    
    Complements Shortcuts for more complex automation.
    """
    
    # Common AppleScript templates
    TEMPLATES = {
        "open_app": 'tell application "{app}" to activate',
        "quit_app": 'tell application "{app}" to quit',
        "get_frontmost_app": 'tell application "System Events" to get name of first process whose frontmost is true',
        "get_volume": 'output volume of (get volume settings)',
        "set_volume": 'set volume output volume {level}',
        "notification": 'display notification "{message}" with title "{title}"',
        "dialog": 'display dialog "{message}" with title "{title}"',
        "get_clipboard": 'the clipboard',
        "set_clipboard": 'set the clipboard to "{text}"',
    }
    
    def __init__(self):
        self._system = platform.system()
    
    async def run(self, script: str) -> Tuple[bool, str]:
        """
        Run an AppleScript.
        
        Args:
            script: AppleScript code
            
        Returns:
            (success, output)
        """
        if self._system != "Darwin":
            return False, "僅支援 macOS"
        
        try:
            process = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True, stdout.decode().strip()
            else:
                return False, stderr.decode().strip()
                
        except Exception as e:
            logger.error(f"AppleScript error: {e}")
            return False, str(e)
    
    async def run_template(self, template_name: str, **kwargs) -> Tuple[bool, str]:
        """Run a template AppleScript."""
        template = self.TEMPLATES.get(template_name)
        if not template:
            return False, f"未知的模板：{template_name}"
        
        script = template.format(**kwargs)
        return await self.run(script)
    
    async def open_app(self, app_name: str) -> Tuple[bool, str]:
        """Open an application."""
        return await self.run_template("open_app", app=app_name)
    
    async def quit_app(self, app_name: str) -> Tuple[bool, str]:
        """Quit an application."""
        return await self.run_template("quit_app", app=app_name)
    
    async def show_notification(self, message: str, title: str = "CursorBot") -> Tuple[bool, str]:
        """Show a system notification."""
        return await self.run_template("notification", message=message, title=title)
    
    async def get_volume(self) -> int:
        """Get current volume level."""
        success, output = await self.run_template("get_volume")
        if success:
            try:
                return int(output)
            except ValueError:
                pass
        return 50
    
    async def set_volume(self, level: int) -> Tuple[bool, str]:
        """Set volume level (0-100)."""
        level = max(0, min(100, level))
        return await self.run_template("set_volume", level=level)


# ============================================
# Android Intents
# ============================================

class AndroidIntentAction(Enum):
    """Common Android intent actions."""
    VIEW = "android.intent.action.VIEW"
    SEND = "android.intent.action.SEND"
    DIAL = "android.intent.action.DIAL"
    CALL = "android.intent.action.CALL"
    SENDTO = "android.intent.action.SENDTO"
    SEARCH = "android.intent.action.WEB_SEARCH"
    MUSIC = "android.intent.action.MUSIC_PLAYER"
    CAMERA = "android.media.action.IMAGE_CAPTURE"
    SETTINGS = "android.settings.SETTINGS"
    WIFI_SETTINGS = "android.settings.WIFI_SETTINGS"
    BLUETOOTH = "android.settings.BLUETOOTH_SETTINGS"
    ALARM = "android.intent.action.SET_ALARM"
    TIMER = "android.intent.action.SET_TIMER"


@dataclass
class AndroidIntent:
    """An Android intent."""
    action: str
    data: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)
    package: Optional[str] = None
    component: Optional[str] = None


class AndroidIntentHandler:
    """
    Handles Android intents for CursorBot Node app.
    
    Generates intents that can be executed by the Android app.
    """
    
    def __init__(self):
        self._registered_handlers: Dict[str, Callable] = {}
    
    def create_intent(
        self,
        action: AndroidIntentAction,
        data: str = None,
        extras: Dict[str, Any] = None,
        package: str = None
    ) -> AndroidIntent:
        """Create an Android intent."""
        return AndroidIntent(
            action=action.value,
            data=data,
            extras=extras or {},
            package=package,
        )
    
    def to_uri(self, intent: AndroidIntent) -> str:
        """Convert intent to URI for sharing."""
        uri = f"intent:{intent.data or '#Intent'}#Intent"
        uri += f";action={intent.action}"
        
        if intent.package:
            uri += f";package={intent.package}"
        
        for key, value in intent.extras.items():
            uri += f";S.{key}={value}"
        
        uri += ";end"
        return uri
    
    def open_url(self, url: str) -> AndroidIntent:
        """Create intent to open a URL."""
        return self.create_intent(
            AndroidIntentAction.VIEW,
            data=url
        )
    
    def dial_phone(self, number: str) -> AndroidIntent:
        """Create intent to dial a phone number."""
        return self.create_intent(
            AndroidIntentAction.DIAL,
            data=f"tel:{number}"
        )
    
    def send_sms(self, number: str, message: str = "") -> AndroidIntent:
        """Create intent to send SMS."""
        return self.create_intent(
            AndroidIntentAction.SENDTO,
            data=f"smsto:{number}",
            extras={"sms_body": message}
        )
    
    def send_email(
        self,
        to: str,
        subject: str = "",
        body: str = ""
    ) -> AndroidIntent:
        """Create intent to send email."""
        return self.create_intent(
            AndroidIntentAction.SENDTO,
            data=f"mailto:{to}",
            extras={
                "android.intent.extra.SUBJECT": subject,
                "android.intent.extra.TEXT": body,
            }
        )
    
    def web_search(self, query: str) -> AndroidIntent:
        """Create intent for web search."""
        return self.create_intent(
            AndroidIntentAction.SEARCH,
            extras={"query": query}
        )
    
    def open_settings(self, setting: str = "main") -> AndroidIntent:
        """Create intent to open settings."""
        settings_map = {
            "main": AndroidIntentAction.SETTINGS,
            "wifi": AndroidIntentAction.WIFI_SETTINGS,
            "bluetooth": AndroidIntentAction.BLUETOOTH,
        }
        
        action = settings_map.get(setting, AndroidIntentAction.SETTINGS)
        return self.create_intent(action)
    
    def set_alarm(
        self,
        hour: int,
        minute: int,
        message: str = ""
    ) -> AndroidIntent:
        """Create intent to set an alarm."""
        return self.create_intent(
            AndroidIntentAction.ALARM,
            extras={
                "android.intent.extra.alarm.HOUR": hour,
                "android.intent.extra.alarm.MINUTES": minute,
                "android.intent.extra.alarm.MESSAGE": message,
            }
        )
    
    def set_timer(self, seconds: int, message: str = "") -> AndroidIntent:
        """Create intent to set a timer."""
        return self.create_intent(
            AndroidIntentAction.TIMER,
            extras={
                "android.intent.extra.alarm.LENGTH": seconds,
                "android.intent.extra.alarm.MESSAGE": message,
            }
        )
    
    def parse_voice_command(self, command: str) -> Optional[AndroidIntent]:
        """
        Parse voice command into an Android intent.
        
        Args:
            command: Voice command text
            
        Returns:
            AndroidIntent if parseable, None otherwise
        """
        command_lower = command.lower()
        
        # URL opening
        if "打開" in command_lower or "open" in command_lower:
            import re
            url_match = re.search(r'(https?://\S+|www\.\S+)', command)
            if url_match:
                url = url_match.group(1)
                if not url.startswith("http"):
                    url = "https://" + url
                return self.open_url(url)
        
        # Phone dialing
        if "撥打" in command_lower or "打電話" in command_lower or "call" in command_lower:
            import re
            phone_match = re.search(r'(\d[\d\-\s]{7,})', command)
            if phone_match:
                number = phone_match.group(1).replace(" ", "").replace("-", "")
                return self.dial_phone(number)
        
        # Web search
        if "搜尋" in command_lower or "search" in command_lower:
            # Extract query
            import re
            query_patterns = [
                r"搜尋\s*(.+)",
                r"search\s+(?:for\s+)?(.+)",
            ]
            for pattern in query_patterns:
                match = re.search(pattern, command_lower)
                if match:
                    return self.web_search(match.group(1))
        
        # Settings
        if "設定" in command_lower or "settings" in command_lower:
            if "wifi" in command_lower or "網路" in command_lower:
                return self.open_settings("wifi")
            elif "藍牙" in command_lower or "bluetooth" in command_lower:
                return self.open_settings("bluetooth")
            else:
                return self.open_settings("main")
        
        return None


# ============================================
# System Notification Interaction
# ============================================

@dataclass
class SystemNotification:
    """A system notification."""
    id: str
    app: str
    title: str
    body: str
    timestamp: datetime
    actions: List[str] = field(default_factory=list)


class NotificationInteraction:
    """
    Interacts with system notifications.
    
    Features:
    - Read notifications
    - Respond to notifications
    - Dismiss notifications
    """
    
    def __init__(self):
        self._system = platform.system()
        self._notification_history: List[SystemNotification] = []
    
    async def get_notifications(self, limit: int = 10) -> List[SystemNotification]:
        """
        Get recent notifications.
        
        Note: macOS doesn't expose notification center via command line.
        This would need native integration.
        """
        if self._system == "Darwin":
            # macOS - would need to use native APIs
            # Return cached history for now
            return self._notification_history[-limit:]
        
        return []
    
    async def send_notification(
        self,
        title: str,
        body: str,
        subtitle: str = "",
        sound: bool = True
    ) -> bool:
        """Send a notification."""
        try:
            if self._system == "Darwin":
                # Use osascript for macOS notification
                script = f'''
                display notification "{body}" with title "{title}"
                '''
                if subtitle:
                    script = f'''
                    display notification "{body}" with title "{title}" subtitle "{subtitle}"
                    '''
                
                process = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.communicate()
                return process.returncode == 0
                
            elif self._system == "Linux":
                # Use notify-send for Linux
                cmd = ["notify-send", title, body]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.communicate()
                return process.returncode == 0
                
        except Exception as e:
            logger.error(f"Send notification error: {e}")
        
        return False
    
    def record_notification(self, notification: SystemNotification) -> None:
        """Record a notification in history."""
        self._notification_history.append(notification)
        
        # Limit history
        if len(self._notification_history) > 100:
            self._notification_history = self._notification_history[-100:]
    
    async def read_notification(self, notification: SystemNotification) -> str:
        """Generate text-to-speech text for a notification."""
        return f"{notification.app} 通知：{notification.title}。{notification.body}"
    
    def get_notification_summary(self) -> str:
        """Get summary of recent notifications."""
        if not self._notification_history:
            return "沒有最近的通知"
        
        # Group by app
        by_app: Dict[str, int] = {}
        for n in self._notification_history[-20:]:
            by_app[n.app] = by_app.get(n.app, 0) + 1
        
        parts = [f"{app} {count} 則" for app, count in by_app.items()]
        return f"最近通知：{', '.join(parts)}"


# ============================================
# Unified Shortcuts Manager
# ============================================

class ShortcutsManager:
    """
    Unified manager for all shortcut/automation systems.
    
    Provides a common interface across platforms.
    """
    
    def __init__(self):
        self._system = platform.system()
        
        # Platform-specific handlers
        self._macos_shortcuts = MacOSShortcutsManager() if self._system == "Darwin" else None
        self._applescript = AppleScriptRunner() if self._system == "Darwin" else None
        self._android_intents = AndroidIntentHandler()
        self._notifications = NotificationInteraction()
        
        # Voice trigger mapping
        self._triggers: Dict[str, Callable] = {}
        self._register_default_triggers()
    
    def _register_default_triggers(self) -> None:
        """Register default voice triggers."""
        self._triggers = {
            # App control
            "打開": self._handle_open,
            "關閉": self._handle_close,
            "open": self._handle_open,
            "close": self._handle_close,
            
            # Volume
            "音量": self._handle_volume,
            "volume": self._handle_volume,
            
            # Notification
            "通知": self._handle_notification,
            "notification": self._handle_notification,
            
            # Shortcut
            "捷徑": self._handle_shortcut,
            "shortcut": self._handle_shortcut,
        }
    
    async def process_command(self, command: str) -> str:
        """
        Process a voice command.
        
        Routes to appropriate handler based on command.
        """
        command_lower = command.lower()
        
        for trigger, handler in self._triggers.items():
            if trigger in command_lower:
                return await handler(command)
        
        return "無法識別的指令"
    
    async def _handle_open(self, command: str) -> str:
        """Handle open commands."""
        import re
        
        # Extract app name
        patterns = [
            r"打開\s*(.+)",
            r"開啟\s*(.+)",
            r"open\s+(.+)",
            r"launch\s+(.+)",
        ]
        
        app_name = None
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                app_name = match.group(1).strip()
                break
        
        if not app_name:
            return "請指定要打開的應用程式"
        
        if self._applescript:
            success, result = await self._applescript.open_app(app_name)
            return f"已打開 {app_name}" if success else result
        
        return f"正在打開 {app_name}"
    
    async def _handle_close(self, command: str) -> str:
        """Handle close commands."""
        import re
        
        patterns = [
            r"關閉\s*(.+)",
            r"close\s+(.+)",
            r"quit\s+(.+)",
        ]
        
        app_name = None
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                app_name = match.group(1).strip()
                break
        
        if not app_name:
            return "請指定要關閉的應用程式"
        
        if self._applescript:
            success, result = await self._applescript.quit_app(app_name)
            return f"已關閉 {app_name}" if success else result
        
        return f"正在關閉 {app_name}"
    
    async def _handle_volume(self, command: str) -> str:
        """Handle volume commands."""
        import re
        
        if not self._applescript:
            return "音量控制僅支援 macOS"
        
        command_lower = command.lower()
        
        if "大" in command_lower or "高" in command_lower or "up" in command_lower:
            current = await self._applescript.get_volume()
            new_level = min(100, current + 10)
            await self._applescript.set_volume(new_level)
            return f"音量已調高至 {new_level}%"
        
        elif "小" in command_lower or "低" in command_lower or "down" in command_lower:
            current = await self._applescript.get_volume()
            new_level = max(0, current - 10)
            await self._applescript.set_volume(new_level)
            return f"音量已調低至 {new_level}%"
        
        elif "靜音" in command_lower or "mute" in command_lower:
            await self._applescript.set_volume(0)
            return "已靜音"
        
        # Check for specific level
        level_match = re.search(r"(\d+)", command)
        if level_match:
            level = int(level_match.group(1))
            await self._applescript.set_volume(level)
            return f"音量已設定為 {level}%"
        
        # Return current volume
        current = await self._applescript.get_volume()
        return f"目前音量 {current}%"
    
    async def _handle_notification(self, command: str) -> str:
        """Handle notification commands."""
        command_lower = command.lower()
        
        if "讀" in command_lower or "唸" in command_lower or "read" in command_lower:
            notifications = await self._notifications.get_notifications(5)
            if not notifications:
                return "沒有最近的通知"
            
            # Read the most recent
            return await self._notifications.read_notification(notifications[-1])
        
        if "摘要" in command_lower or "summary" in command_lower:
            return self._notifications.get_notification_summary()
        
        return "可以說「讀通知」或「通知摘要」"
    
    async def _handle_shortcut(self, command: str) -> str:
        """Handle shortcut commands."""
        import re
        
        if not self._macos_shortcuts:
            return "捷徑功能僅支援 macOS"
        
        # List shortcuts
        if "列出" in command.lower() or "list" in command.lower():
            shortcuts = await self._macos_shortcuts.list_shortcuts()
            if not shortcuts:
                return "找不到任何捷徑"
            
            names = [s.name for s in shortcuts[:10]]
            return f"可用捷徑：{', '.join(names)}"
        
        # Run shortcut
        patterns = [
            r"執行捷徑\s*(.+)",
            r"run shortcut\s+(.+)",
            r"捷徑\s*(.+)",
        ]
        
        shortcut_name = None
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                shortcut_name = match.group(1).strip()
                break
        
        if shortcut_name:
            success, result = await self._macos_shortcuts.run_shortcut(shortcut_name)
            return result
        
        return "請說「列出捷徑」或「執行捷徑 [名稱]」"
    
    async def run_shortcut(self, name: str, input_data: str = None) -> Tuple[bool, str]:
        """Run a shortcut by name."""
        if self._macos_shortcuts:
            return await self._macos_shortcuts.run_shortcut(name, input_data)
        return False, "不支援此平台"
    
    async def list_shortcuts(self) -> List[Shortcut]:
        """List available shortcuts."""
        if self._macos_shortcuts:
            return await self._macos_shortcuts.list_shortcuts()
        return []
    
    def create_android_intent(
        self,
        action: AndroidIntentAction,
        **kwargs
    ) -> AndroidIntent:
        """Create an Android intent."""
        return self._android_intents.create_intent(action, **kwargs)
    
    async def send_notification(self, title: str, body: str) -> bool:
        """Send a system notification."""
        return await self._notifications.send_notification(title, body)


# ============================================
# Global Instance
# ============================================

_shortcuts_manager: Optional[ShortcutsManager] = None


def get_shortcuts_manager() -> ShortcutsManager:
    global _shortcuts_manager
    if _shortcuts_manager is None:
        _shortcuts_manager = ShortcutsManager()
    return _shortcuts_manager


__all__ = [
    # macOS
    "MacOSShortcutsManager",
    "AppleScriptRunner",
    "Shortcut",
    "ShortcutType",
    # Android
    "AndroidIntentHandler",
    "AndroidIntent",
    "AndroidIntentAction",
    # Notifications
    "NotificationInteraction",
    "SystemNotification",
    # Manager
    "ShortcutsManager",
    "get_shortcuts_manager",
]
