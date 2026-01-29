"""
Voice Commands System for CursorBot v1.1

Provides voice command execution:
- System control commands
- Application control
- Code operations
- File operations
- Smart home integration
- Custom commands

Usage:
    from src.core.voice_commands import get_command_executor
    
    executor = get_command_executor()
    result = await executor.execute(intent)
"""

import os
import asyncio
import subprocess
import platform
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from ..utils.logger import logger
from .voice_assistant import Intent, IntentCategory


# ============================================
# Enums
# ============================================

class CommandCategory(Enum):
    """Command categories."""
    SYSTEM = "system"           # System control
    APPLICATION = "application" # App control
    FILE = "file"               # File operations
    CODE = "code"               # Code operations
    WEB = "web"                 # Web operations
    CALENDAR = "calendar"       # Calendar operations
    REMINDER = "reminder"       # Reminder operations
    MEDIA = "media"             # Media control
    SMART_HOME = "smart_home"   # IoT control
    CUSTOM = "custom"           # Custom commands


class CommandStatus(Enum):
    """Command execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"
    REQUIRES_CONFIRMATION = "requires_confirmation"


# ============================================
# Data Classes
# ============================================

@dataclass
class CommandResult:
    """Result of command execution."""
    status: CommandStatus
    message: str = ""
    data: Any = None
    error: Optional[str] = None
    requires_response: bool = True
    response_text: str = ""


@dataclass
class CommandDefinition:
    """Definition of a voice command."""
    name: str
    category: CommandCategory
    patterns: List[str]  # Regex patterns to match
    handler: Callable
    description: str = ""
    requires_confirmation: bool = False
    system: str = "all"  # all, macos, windows, linux


# ============================================
# Command Handlers
# ============================================

class CommandHandler(ABC):
    """Abstract command handler."""
    
    @abstractmethod
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        """Execute the command."""
        pass
    
    @abstractmethod
    def can_handle(self, intent: Intent) -> bool:
        """Check if this handler can handle the intent."""
        pass


class SystemCommandHandler(CommandHandler):
    """Handle system control commands."""
    
    COMMANDS = {
        "volume_up": {
            "patterns": [r"調高音量|volume up|增加音量|大聲一點"],
            "macos": "osascript -e 'set volume output volume ((output volume of (get volume settings)) + 10)'",
            "windows": "nircmd.exe changesysvolume 6553",
        },
        "volume_down": {
            "patterns": [r"調低音量|volume down|減少音量|小聲一點"],
            "macos": "osascript -e 'set volume output volume ((output volume of (get volume settings)) - 10)'",
            "windows": "nircmd.exe changesysvolume -6553",
        },
        "mute": {
            "patterns": [r"靜音|mute|關閉聲音"],
            "macos": "osascript -e 'set volume with output muted'",
            "windows": "nircmd.exe mutesysvolume 1",
        },
        "unmute": {
            "patterns": [r"取消靜音|unmute|開啟聲音"],
            "macos": "osascript -e 'set volume without output muted'",
            "windows": "nircmd.exe mutesysvolume 0",
        },
        "brightness_up": {
            "patterns": [r"調高亮度|brightness up|增加亮度|亮一點"],
            "macos": "brightness 0.1",  # Requires brightness CLI tool
        },
        "brightness_down": {
            "patterns": [r"調低亮度|brightness down|減少亮度|暗一點"],
            "macos": "brightness -0.1",
        },
        "screenshot": {
            "patterns": [r"截圖|screenshot|螢幕截圖|capture screen"],
            "macos": "screencapture -i ~/Desktop/screenshot_$(date +%Y%m%d_%H%M%S).png",
            "windows": "snippingtool",
        },
        "lock_screen": {
            "patterns": [r"鎖定螢幕|lock screen|鎖屏|lock"],
            "macos": "pmset displaysleepnow",
            "windows": "rundll32.exe user32.dll,LockWorkStation",
        },
        "sleep": {
            "patterns": [r"休眠|sleep|睡眠模式"],
            "macos": "pmset sleepnow",
            "windows": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        },
    }
    
    def __init__(self):
        self._system = platform.system().lower()
    
    def can_handle(self, intent: Intent) -> bool:
        if intent.category != IntentCategory.CONTROL:
            return False
        
        text = intent.raw_text.lower()
        for cmd_name, cmd_info in self.COMMANDS.items():
            for pattern in cmd_info["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        return False
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text.lower()
        
        for cmd_name, cmd_info in self.COMMANDS.items():
            for pattern in cmd_info["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    return await self._run_command(cmd_name, cmd_info)
        
        return CommandResult(
            status=CommandStatus.FAILED,
            message="Unknown system command",
            response_text="抱歉，我不知道如何執行這個系統指令。"
        )
    
    async def _run_command(self, name: str, info: Dict) -> CommandResult:
        # Get platform-specific command
        cmd = None
        if self._system == "darwin":
            cmd = info.get("macos")
        elif self._system == "windows":
            cmd = info.get("windows")
        elif self._system == "linux":
            cmd = info.get("linux") or info.get("macos")  # Try macOS command on Linux
        
        if not cmd:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Command not supported on {self._system}",
                response_text=f"抱歉，這個指令在 {self._system} 上不支援。"
            )
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message=f"Executed: {name}",
                    response_text=self._get_success_response(name)
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    error=stderr.decode(),
                    response_text="執行時發生錯誤。"
                )
        except Exception as e:
            logger.error(f"System command error: {e}")
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text="執行指令時發生錯誤。"
            )
    
    def _get_success_response(self, name: str) -> str:
        responses = {
            "volume_up": "好的，音量已調高。",
            "volume_down": "好的，音量已調低。",
            "mute": "已靜音。",
            "unmute": "已取消靜音。",
            "brightness_up": "好的，螢幕亮度已提高。",
            "brightness_down": "好的，螢幕亮度已降低。",
            "screenshot": "已截圖，儲存在桌面。",
            "lock_screen": "螢幕已鎖定。",
            "sleep": "系統將進入休眠模式。",
        }
        return responses.get(name, "指令已執行。")


class ApplicationCommandHandler(CommandHandler):
    """Handle application control commands."""
    
    APP_ALIASES = {
        # macOS apps
        "cursor": ["Cursor", "cursor"],
        "vscode": ["Visual Studio Code", "code", "vscode"],
        "terminal": ["Terminal", "terminal", "終端機"],
        "finder": ["Finder", "finder", "檔案管理"],
        "safari": ["Safari", "safari"],
        "chrome": ["Google Chrome", "chrome", "谷歌瀏覽器"],
        "slack": ["Slack", "slack"],
        "discord": ["Discord", "discord"],
        "spotify": ["Spotify", "spotify"],
        "music": ["Music", "music", "音樂"],
        "notes": ["Notes", "notes", "備忘錄"],
        "calendar": ["Calendar", "calendar", "行事曆", "日曆"],
        "messages": ["Messages", "messages", "訊息"],
        "mail": ["Mail", "mail", "郵件"],
        "photos": ["Photos", "photos", "照片"],
        "preview": ["Preview", "preview", "預覽程式"],
        "settings": ["System Preferences", "System Settings", "設定", "偏好設定"],
    }
    
    def __init__(self):
        self._system = platform.system().lower()
    
    def can_handle(self, intent: Intent) -> bool:
        if intent.category != IntentCategory.COMMAND:
            return False
        
        text = intent.raw_text.lower()
        patterns = [r"打開|開啟|啟動|open|launch|start|關閉|close|quit|結束"]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text.lower()
        
        # Determine action (open or close)
        is_close = bool(re.search(r"關閉|close|quit|結束|停止", text))
        
        # Find app name
        app_name = self._extract_app_name(text)
        if not app_name:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Could not identify application",
                response_text="抱歉，我不確定您要操作哪個應用程式。"
            )
        
        if is_close:
            return await self._close_app(app_name)
        else:
            return await self._open_app(app_name)
    
    def _extract_app_name(self, text: str) -> Optional[str]:
        """Extract application name from text."""
        text_lower = text.lower()
        
        for canonical, aliases in self.APP_ALIASES.items():
            for alias in aliases:
                if alias.lower() in text_lower:
                    return aliases[0]  # Return the first (primary) name
        
        # Try to extract app name after keywords
        match = re.search(r"(?:打開|開啟|啟動|open|launch|關閉|close|quit)\s+(\w+)", text)
        if match:
            return match.group(1)
        
        return None
    
    async def _open_app(self, app_name: str) -> CommandResult:
        try:
            if self._system == "darwin":
                cmd = f"open -a '{app_name}'"
            elif self._system == "windows":
                cmd = f"start {app_name}"
            else:
                cmd = app_name.lower()
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=f"Opened {app_name}",
                response_text=f"已開啟 {app_name}。"
            )
        except Exception as e:
            logger.error(f"Open app error: {e}")
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"無法開啟 {app_name}。"
            )
    
    async def _close_app(self, app_name: str) -> CommandResult:
        try:
            if self._system == "darwin":
                cmd = f"osascript -e 'quit app \"{app_name}\"'"
            elif self._system == "windows":
                cmd = f"taskkill /IM {app_name}.exe /F"
            else:
                cmd = f"pkill -f {app_name}"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message=f"Closed {app_name}",
                response_text=f"已關閉 {app_name}。"
            )
        except Exception as e:
            logger.error(f"Close app error: {e}")
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"無法關閉 {app_name}。"
            )


class CodeCommandHandler(CommandHandler):
    """Handle code-related commands."""
    
    def can_handle(self, intent: Intent) -> bool:
        return intent.category == IntentCategory.CODE
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text.lower()
        
        # Git commands
        if re.search(r"git\s*commit|提交|commit", text):
            return await self._git_commit(intent)
        elif re.search(r"git\s*push|推送|push", text):
            return await self._git_push()
        elif re.search(r"git\s*pull|拉取|pull", text):
            return await self._git_pull()
        elif re.search(r"git\s*status|狀態|status", text):
            return await self._git_status()
        
        # Build/test commands
        elif re.search(r"執行測試|run\s*test|test", text):
            return await self._run_tests()
        elif re.search(r"建置|build|編譯|compile", text):
            return await self._build_project()
        
        return CommandResult(
            status=CommandStatus.FAILED,
            message="Unknown code command",
            response_text="我不確定您要執行什麼程式碼操作。"
        )
    
    async def _git_commit(self, intent: Intent) -> CommandResult:
        # Extract commit message
        match = re.search(r"(?:訊息|message)[：:\s]*[「「]?(.+?)[」」]?$", intent.raw_text)
        message = match.group(1) if match else "Update via voice command"
        
        try:
            # Stage all changes
            await asyncio.create_subprocess_shell("git add -A")
            
            # Commit
            process = await asyncio.create_subprocess_shell(
                f'git commit -m "{message}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    message="Git commit successful",
                    response_text=f"已提交變更，訊息：{message}"
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    error=stderr.decode(),
                    response_text="提交失敗，可能沒有需要提交的變更。"
                )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text="執行 Git 提交時發生錯誤。"
            )
    
    async def _git_push(self) -> CommandResult:
        try:
            process = await asyncio.create_subprocess_shell(
                "git push",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    response_text="已推送到遠端倉庫。"
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    error=stderr.decode(),
                    response_text="推送失敗，請檢查網路連線和權限。"
                )
        except Exception as e:
            return CommandResult(status=CommandStatus.FAILED, error=str(e))
    
    async def _git_pull(self) -> CommandResult:
        try:
            process = await asyncio.create_subprocess_shell(
                "git pull",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    response_text="已從遠端倉庫拉取最新程式碼。"
                )
            else:
                return CommandResult(
                    status=CommandStatus.FAILED,
                    error=stderr.decode(),
                    response_text="拉取失敗。"
                )
        except Exception as e:
            return CommandResult(status=CommandStatus.FAILED, error=str(e))
    
    async def _git_status(self) -> CommandResult:
        try:
            process = await asyncio.create_subprocess_shell(
                "git status --short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode().strip()
            if output:
                lines = output.split("\n")
                count = len(lines)
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"changes": lines},
                    response_text=f"有 {count} 個檔案有變更。"
                )
            else:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    response_text="工作目錄是乾淨的，沒有待提交的變更。"
                )
        except Exception as e:
            return CommandResult(status=CommandStatus.FAILED, error=str(e))
    
    async def _run_tests(self) -> CommandResult:
        # Try common test commands
        test_commands = [
            "npm test",
            "yarn test",
            "pytest",
            "python -m pytest",
            "go test ./...",
        ]
        
        for cmd in test_commands:
            # Check if the tool exists
            check_cmd = cmd.split()[0]
            result = await asyncio.create_subprocess_shell(
                f"which {check_cmd}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                return CommandResult(
                    status=CommandStatus.PENDING,
                    message=f"Running: {cmd}",
                    response_text=f"正在執行測試：{cmd}"
                )
        
        return CommandResult(
            status=CommandStatus.FAILED,
            response_text="找不到可用的測試框架。"
        )
    
    async def _build_project(self) -> CommandResult:
        # Try common build commands
        build_commands = [
            ("package.json", "npm run build"),
            ("Makefile", "make"),
            ("build.gradle", "./gradlew build"),
            ("pom.xml", "mvn package"),
            ("Cargo.toml", "cargo build"),
        ]
        
        for marker, cmd in build_commands:
            if os.path.exists(marker):
                return CommandResult(
                    status=CommandStatus.PENDING,
                    message=f"Building with: {cmd}",
                    response_text=f"正在建置專案：{cmd}"
                )
        
        return CommandResult(
            status=CommandStatus.FAILED,
            response_text="找不到可用的建置系統。"
        )


class WebCommandHandler(CommandHandler):
    """Handle web-related commands."""
    
    SEARCH_ENGINES = {
        "google": "https://www.google.com/search?q=",
        "bing": "https://www.bing.com/search?q=",
        "duckduckgo": "https://duckduckgo.com/?q=",
    }
    
    QUICK_URLS = {
        "github": "https://github.com",
        "youtube": "https://www.youtube.com",
        "twitter": "https://twitter.com",
        "facebook": "https://www.facebook.com",
        "gmail": "https://mail.google.com",
        "google": "https://www.google.com",
    }
    
    def can_handle(self, intent: Intent) -> bool:
        return intent.category == IntentCategory.SEARCH
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text.lower()
        
        # Check for quick URLs
        for name, url in self.QUICK_URLS.items():
            if name in text:
                return await self._open_url(url, name)
        
        # Extract search query
        match = re.search(r"(?:搜尋|search|找|查)\s*(.+)", text, re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            return await self._search(query)
        
        return CommandResult(
            status=CommandStatus.FAILED,
            response_text="我不確定您要搜尋什麼。"
        )
    
    async def _open_url(self, url: str, name: str) -> CommandResult:
        try:
            if platform.system() == "Darwin":
                cmd = f"open '{url}'"
            elif platform.system() == "Windows":
                cmd = f"start {url}"
            else:
                cmd = f"xdg-open '{url}'"
            
            await asyncio.create_subprocess_shell(cmd)
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"已開啟 {name}。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"無法開啟 {name}。"
            )
    
    async def _search(self, query: str, engine: str = "google") -> CommandResult:
        import urllib.parse
        
        base_url = self.SEARCH_ENGINES.get(engine, self.SEARCH_ENGINES["google"])
        url = base_url + urllib.parse.quote(query)
        
        try:
            if platform.system() == "Darwin":
                cmd = f"open '{url}'"
            elif platform.system() == "Windows":
                cmd = f"start {url}"
            else:
                cmd = f"xdg-open '{url}'"
            
            await asyncio.create_subprocess_shell(cmd)
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"正在搜尋：{query}"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text="無法開啟搜尋結果。"
            )


class ReminderCommandHandler(CommandHandler):
    """Handle reminder commands."""
    
    def __init__(self):
        self._reminders: List[Dict] = []
    
    def can_handle(self, intent: Intent) -> bool:
        return intent.category == IntentCategory.REMINDER
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text
        
        # Extract reminder content and time
        content = self._extract_content(text)
        reminder_time = self._extract_time(text)
        
        if not content:
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text="請告訴我要提醒您什麼事情。"
            )
        
        # Create reminder
        reminder = {
            "content": content,
            "time": reminder_time,
            "created": datetime.now(),
        }
        self._reminders.append(reminder)
        
        if reminder_time:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data=reminder,
                response_text=f"好的，我會在{self._format_time(reminder_time)}提醒您：{content}"
            )
        else:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data=reminder,
                response_text=f"好的，我記住了：{content}"
            )
    
    def _extract_content(self, text: str) -> Optional[str]:
        # Remove common prefixes
        text = re.sub(r"^(提醒我|記住|remind me to|remember)\s*", "", text, flags=re.IGNORECASE)
        
        # Remove time expressions
        text = re.sub(r"(明天|今天|後天|下午|上午|晚上|早上|\d+分鐘後|\d+小時後)", "", text)
        
        return text.strip() if text.strip() else None
    
    def _extract_time(self, text: str) -> Optional[datetime]:
        now = datetime.now()
        
        # Minutes from now
        match = re.search(r"(\d+)\s*分鐘", text)
        if match:
            minutes = int(match.group(1))
            return now + timedelta(minutes=minutes)
        
        # Hours from now
        match = re.search(r"(\d+)\s*小時", text)
        if match:
            hours = int(match.group(1))
            return now + timedelta(hours=hours)
        
        # Tomorrow
        if "明天" in text:
            return now.replace(hour=9, minute=0, second=0) + timedelta(days=1)
        
        return None
    
    def _format_time(self, dt: datetime) -> str:
        now = datetime.now()
        diff = dt - now
        
        if diff.days > 0:
            return f"{diff.days}天後"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours}小時後"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes}分鐘後"
        else:
            return "稍後"


# ============================================
# Command Executor
# ============================================

class CommandExecutor:
    """
    Central command executor for voice commands.
    
    Routes intents to appropriate handlers and manages execution.
    """
    
    def __init__(self):
        self._handlers: List[CommandHandler] = []
        self._custom_commands: Dict[str, Callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default command handlers."""
        from .voice_integrations import (
            FileOperationHandler, ClipboardHandler, WeatherHandler,
            CalendarVoiceHandler, TranslationHandler, VoiceSearchHandler,
        )
        
        self._handlers = [
            SystemCommandHandler(),
            ApplicationCommandHandler(),
            CodeCommandHandler(),
            WebCommandHandler(),
            ReminderCommandHandler(),
            # v1.1 extended handlers
            FileOperationHandler(),
            ClipboardHandler(),
            WeatherHandler(),
            CalendarVoiceHandler(),
            TranslationHandler(),
            VoiceSearchHandler(),
        ]
    
    def register_handler(self, handler: CommandHandler) -> None:
        """Register a custom command handler."""
        self._handlers.insert(0, handler)  # Custom handlers have priority
    
    def register_command(self, pattern: str, handler: Callable) -> None:
        """Register a simple command with pattern."""
        self._custom_commands[pattern] = handler
    
    async def execute(self, intent: Intent) -> CommandResult:
        """
        Execute a command based on intent.
        
        Args:
            intent: Recognized intent
            
        Returns:
            CommandResult
        """
        # Try custom commands first
        for pattern, handler in self._custom_commands.items():
            if re.search(pattern, intent.raw_text, re.IGNORECASE):
                try:
                    result = await handler(intent)
                    if isinstance(result, CommandResult):
                        return result
                    return CommandResult(
                        status=CommandStatus.SUCCESS,
                        data=result,
                        response_text=str(result)
                    )
                except Exception as e:
                    logger.error(f"Custom command error: {e}")
                    return CommandResult(
                        status=CommandStatus.FAILED,
                        error=str(e)
                    )
        
        # Try registered handlers
        for handler in self._handlers:
            if handler.can_handle(intent):
                try:
                    return await handler.execute(intent)
                except Exception as e:
                    logger.error(f"Handler error: {e}")
                    return CommandResult(
                        status=CommandStatus.FAILED,
                        error=str(e)
                    )
        
        # No handler found - treat as chat
        return CommandResult(
            status=CommandStatus.SUCCESS,
            message="No specific handler, treating as chat",
            response_text="",  # Let the LLM handle it
            requires_response=True
        )
    
    def get_available_commands(self) -> List[str]:
        """Get list of available command categories."""
        return [
            "系統控制：音量、亮度、截圖、鎖屏",
            "應用程式：打開/關閉 Cursor、Chrome、Terminal 等",
            "程式碼：Git commit、push、pull、執行測試、建置",
            "網頁：搜尋、開啟網站",
            "提醒：設定提醒、記住事項",
        ]


# ============================================
# Global Instance
# ============================================

_command_executor: Optional[CommandExecutor] = None


def get_command_executor() -> CommandExecutor:
    """Get or create the global command executor."""
    global _command_executor
    if _command_executor is None:
        _command_executor = CommandExecutor()
    return _command_executor


__all__ = [
    "CommandCategory",
    "CommandStatus",
    "CommandResult",
    "CommandDefinition",
    "CommandHandler",
    "CommandExecutor",
    "get_command_executor",
]
