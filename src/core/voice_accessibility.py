"""
Voice Accessibility Support for CursorBot v1.1

Provides accessibility features for users with disabilities:
- Screen reader integration
- Voice-only navigation
- High contrast audio feedback
- Haptic feedback coordination
- Adjustable speech settings

Usage:
    from src.core.voice_accessibility import (
        AccessibilityManager,
        ScreenReaderBridge,
        VoiceNavigation,
    )
"""

import asyncio
import platform
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..utils.logger import logger


# ============================================
# Accessibility Settings
# ============================================

class AccessibilityMode(Enum):
    """Accessibility modes."""
    STANDARD = "standard"
    SCREEN_READER = "screen_reader"
    VOICE_ONLY = "voice_only"
    LOW_VISION = "low_vision"
    MOTOR_IMPAIRED = "motor_impaired"


class FeedbackType(Enum):
    """Types of accessibility feedback."""
    AUDIO = "audio"
    HAPTIC = "haptic"
    VISUAL = "visual"
    SPEECH = "speech"


@dataclass
class AccessibilitySettings:
    """User's accessibility settings."""
    # Mode
    mode: AccessibilityMode = AccessibilityMode.STANDARD
    
    # Speech settings
    speech_rate: float = 1.0  # 0.5 - 2.0
    speech_pitch: float = 1.0  # 0.5 - 2.0
    speech_volume: float = 1.0  # 0.0 - 1.0
    speech_voice: str = ""  # Preferred voice
    
    # Feedback
    enable_audio_feedback: bool = True
    enable_haptic_feedback: bool = True
    enable_speech_feedback: bool = True
    
    # Navigation
    verbose_navigation: bool = False
    announce_context: bool = True
    repeat_on_request: bool = True
    
    # Timing
    response_delay: float = 0.0  # Extra delay before responses
    confirmation_timeout: float = 10.0  # Seconds to wait for confirmation
    
    # Screen reader
    screen_reader_integration: bool = False
    announce_typing: bool = False


# ============================================
# Screen Reader Bridge
# ============================================

class ScreenReaderBridge:
    """
    Bridges with system screen readers.
    
    Supports:
    - macOS: VoiceOver
    - Windows: NVDA, JAWS, Narrator
    - Linux: Orca
    """
    
    def __init__(self):
        self._system = platform.system()
        self._screen_reader_active = False
        self._check_screen_reader()
    
    def _check_screen_reader(self) -> None:
        """Check if a screen reader is active."""
        try:
            if self._system == "Darwin":
                # Check VoiceOver on macOS
                result = subprocess.run(
                    ["defaults", "read", "com.apple.universalaccess", "voiceOverOnOffKey"],
                    capture_output=True,
                    text=True
                )
                self._screen_reader_active = result.returncode == 0
                
            elif self._system == "Windows":
                # Check for common screen readers
                # This is simplified - actual implementation would check running processes
                self._screen_reader_active = False
                
            elif self._system == "Linux":
                # Check for Orca
                result = subprocess.run(
                    ["pgrep", "-x", "orca"],
                    capture_output=True
                )
                self._screen_reader_active = result.returncode == 0
                
        except Exception as e:
            logger.debug(f"Screen reader check error: {e}")
            self._screen_reader_active = False
    
    @property
    def is_active(self) -> bool:
        return self._screen_reader_active
    
    async def announce(self, text: str, interrupt: bool = False) -> bool:
        """
        Announce text through screen reader.
        
        Args:
            text: Text to announce
            interrupt: Whether to interrupt current speech
            
        Returns:
            True if successful
        """
        if not self._screen_reader_active:
            return False
        
        try:
            if self._system == "Darwin":
                # Use macOS say command or VoiceOver
                cmd = ["say", text]
                if interrupt:
                    # Stop current speech first
                    subprocess.run(["killall", "say"], capture_output=True)
                
                await asyncio.create_subprocess_exec(*cmd)
                return True
                
            elif self._system == "Linux":
                # Use spd-say (speech-dispatcher)
                cmd = ["spd-say"]
                if interrupt:
                    cmd.append("-C")  # Cancel current
                cmd.append(text)
                
                await asyncio.create_subprocess_exec(*cmd)
                return True
                
        except Exception as e:
            logger.error(f"Screen reader announce error: {e}")
        
        return False
    
    async def announce_progress(self, percent: int) -> None:
        """Announce progress percentage."""
        if percent % 25 == 0:  # Announce at 0, 25, 50, 75, 100
            await self.announce(f"進度 {percent}%")
    
    async def announce_error(self, error: str) -> None:
        """Announce an error with appropriate tone."""
        await self.announce(f"錯誤：{error}", interrupt=True)
    
    async def announce_success(self, message: str) -> None:
        """Announce success."""
        await self.announce(f"成功：{message}")


# ============================================
# Voice-Only Navigation
# ============================================

@dataclass
class NavigationNode:
    """A node in the navigation tree."""
    id: str
    label: str
    description: str
    children: List["NavigationNode"] = field(default_factory=list)
    action: Optional[Callable] = None
    shortcuts: List[str] = field(default_factory=list)


class VoiceNavigation:
    """
    Enables complete voice-only navigation.
    
    Provides:
    - Hierarchical menu navigation
    - Shortcuts
    - Context announcements
    - History navigation
    """
    
    def __init__(self, settings: AccessibilitySettings = None):
        self._settings = settings or AccessibilitySettings()
        self._root = self._build_navigation_tree()
        self._current_node = self._root
        self._history: List[NavigationNode] = []
        self._shortcuts: Dict[str, NavigationNode] = {}
        self._index_shortcuts()
    
    def _build_navigation_tree(self) -> NavigationNode:
        """Build the navigation tree."""
        return NavigationNode(
            id="root",
            label="主選單",
            description="CursorBot 語音助手主選單",
            children=[
                NavigationNode(
                    id="commands",
                    label="語音指令",
                    description="執行語音指令",
                    shortcuts=["指令", "command"],
                    children=[
                        NavigationNode(
                            id="cmd_system",
                            label="系統控制",
                            description="控制系統設定和應用程式",
                            shortcuts=["系統", "system"]
                        ),
                        NavigationNode(
                            id="cmd_file",
                            label="檔案操作",
                            description="建立、開啟、刪除檔案",
                            shortcuts=["檔案", "file"]
                        ),
                        NavigationNode(
                            id="cmd_code",
                            label="程式碼操作",
                            description="執行、測試、提交程式碼",
                            shortcuts=["程式", "code"]
                        ),
                    ]
                ),
                NavigationNode(
                    id="settings",
                    label="設定",
                    description="調整語音助手設定",
                    shortcuts=["設定", "settings"],
                    children=[
                        NavigationNode(
                            id="set_voice",
                            label="語音設定",
                            description="調整語速、音調、音量",
                            shortcuts=["語音", "voice"]
                        ),
                        NavigationNode(
                            id="set_privacy",
                            label="隱私設定",
                            description="管理資料收集和隱私",
                            shortcuts=["隱私", "privacy"]
                        ),
                        NavigationNode(
                            id="set_access",
                            label="無障礙設定",
                            description="調整無障礙功能",
                            shortcuts=["無障礙", "accessibility"]
                        ),
                    ]
                ),
                NavigationNode(
                    id="help",
                    label="說明",
                    description="取得使用說明和幫助",
                    shortcuts=["說明", "幫助", "help"],
                    children=[
                        NavigationNode(
                            id="help_commands",
                            label="指令清單",
                            description="列出所有可用指令",
                            shortcuts=["指令清單", "list commands"]
                        ),
                        NavigationNode(
                            id="help_tutorial",
                            label="新手教學",
                            description="語音助手使用教學",
                            shortcuts=["教學", "tutorial"]
                        ),
                    ]
                ),
            ]
        )
    
    def _index_shortcuts(self) -> None:
        """Index all shortcuts for quick access."""
        def index_node(node: NavigationNode):
            for shortcut in node.shortcuts:
                self._shortcuts[shortcut.lower()] = node
            
            for child in node.children:
                index_node(child)
        
        index_node(self._root)
    
    def navigate_to(self, target: str) -> Tuple[NavigationNode, str]:
        """
        Navigate to a target by name or shortcut.
        
        Returns:
            (node, announcement)
        """
        target_lower = target.lower()
        
        # Check shortcuts first
        if target_lower in self._shortcuts:
            node = self._shortcuts[target_lower]
            self._history.append(self._current_node)
            self._current_node = node
            return node, self._announce_node(node)
        
        # Check children of current node
        for child in self._current_node.children:
            if target_lower in child.label.lower() or target_lower == child.id:
                self._history.append(self._current_node)
                self._current_node = child
                return child, self._announce_node(child)
        
        return self._current_node, f"找不到「{target}」，請再說一次"
    
    def go_back(self) -> Tuple[NavigationNode, str]:
        """Go back to previous node."""
        if self._history:
            self._current_node = self._history.pop()
            return self._current_node, self._announce_node(self._current_node)
        
        return self._current_node, "已在主選單，無法返回"
    
    def go_home(self) -> Tuple[NavigationNode, str]:
        """Go to root node."""
        self._history.clear()
        self._current_node = self._root
        return self._current_node, self._announce_node(self._current_node)
    
    def list_options(self) -> Tuple[List[NavigationNode], str]:
        """List available options at current node."""
        children = self._current_node.children
        
        if not children:
            return [], f"「{self._current_node.label}」沒有子選項"
        
        options = [child.label for child in children]
        announcement = f"可選擇：{', '.join(options)}"
        
        return children, announcement
    
    def _announce_node(self, node: NavigationNode) -> str:
        """Generate announcement for a node."""
        announcement = f"進入「{node.label}」"
        
        if self._settings.verbose_navigation:
            announcement += f"。{node.description}"
        
        if node.children and self._settings.announce_context:
            child_count = len(node.children)
            announcement += f"。有 {child_count} 個選項"
        
        return announcement
    
    def get_help(self) -> str:
        """Get navigation help."""
        return """語音導航說明：
- 說「選項」或「列出」來查看可用選項
- 說選項名稱來進入該選項
- 說「返回」回到上一層
- 說「主選單」回到最上層
- 說「說明」取得更多幫助"""


# ============================================
# Audio Feedback System
# ============================================

class AudioFeedback:
    """
    Manages audio feedback for accessibility.
    
    Provides distinct sounds for different events.
    """
    
    # Sound patterns (frequency, duration pairs)
    SOUNDS = {
        "success": [(800, 0.1), (1000, 0.1)],  # Rising tone
        "error": [(400, 0.2), (300, 0.2)],      # Falling tone
        "alert": [(600, 0.1), (600, 0.1), (600, 0.1)],  # Beeps
        "navigation": [(500, 0.05)],            # Short beep
        "confirmation": [(700, 0.1)],           # Single beep
        "start": [(400, 0.1), (600, 0.1), (800, 0.1)],  # Rising sequence
        "stop": [(800, 0.1), (600, 0.1), (400, 0.1)],   # Falling sequence
    }
    
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._system = platform.system()
    
    async def play(self, sound_type: str) -> None:
        """Play a feedback sound."""
        if not self._enabled:
            return
        
        pattern = self.SOUNDS.get(sound_type)
        if not pattern:
            return
        
        try:
            if self._system == "Darwin":
                # Use macOS afplay with generated sounds
                # For simplicity, use system sounds
                sound_map = {
                    "success": "/System/Library/Sounds/Glass.aiff",
                    "error": "/System/Library/Sounds/Basso.aiff",
                    "alert": "/System/Library/Sounds/Ping.aiff",
                    "navigation": "/System/Library/Sounds/Pop.aiff",
                    "confirmation": "/System/Library/Sounds/Tink.aiff",
                    "start": "/System/Library/Sounds/Blow.aiff",
                    "stop": "/System/Library/Sounds/Sosumi.aiff",
                }
                
                sound_file = sound_map.get(sound_type)
                if sound_file:
                    await asyncio.create_subprocess_exec(
                        "afplay", sound_file,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    
            elif self._system == "Linux":
                # Use paplay or similar
                pass
                
        except Exception as e:
            logger.debug(f"Audio feedback error: {e}")
    
    def enable(self) -> None:
        self._enabled = True
    
    def disable(self) -> None:
        self._enabled = False


# ============================================
# Haptic Feedback (for supported devices)
# ============================================

class HapticFeedback:
    """
    Manages haptic feedback for accessibility.
    
    Works with devices that support haptics.
    """
    
    # Haptic patterns
    PATTERNS = {
        "light": "light",
        "medium": "medium",
        "heavy": "heavy",
        "success": "success",
        "error": "error",
        "selection": "selection",
    }
    
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._system = platform.system()
    
    async def trigger(self, pattern: str = "light") -> None:
        """Trigger haptic feedback."""
        if not self._enabled:
            return
        
        # Haptic feedback is primarily for mobile/watch devices
        # On desktop, we might coordinate with trackpad haptics
        try:
            if self._system == "Darwin":
                # macOS doesn't have direct haptic API from command line
                # Would need to use native code
                pass
        except Exception as e:
            logger.debug(f"Haptic feedback error: {e}")
    
    def enable(self) -> None:
        self._enabled = True
    
    def disable(self) -> None:
        self._enabled = False


# ============================================
# Accessibility Manager
# ============================================

class AccessibilityManager:
    """
    Central manager for all accessibility features.
    
    Coordinates:
    - Screen reader integration
    - Voice navigation
    - Audio/haptic feedback
    - Speech settings
    """
    
    def __init__(self, settings: AccessibilitySettings = None):
        self.settings = settings or AccessibilitySettings()
        self.screen_reader = ScreenReaderBridge()
        self.navigation = VoiceNavigation(self.settings)
        self.audio = AudioFeedback(self.settings.enable_audio_feedback)
        self.haptic = HapticFeedback(self.settings.enable_haptic_feedback)
        
        # Detect if we should auto-enable accessibility
        self._auto_detect()
    
    def _auto_detect(self) -> None:
        """Auto-detect accessibility needs."""
        if self.screen_reader.is_active:
            self.settings.mode = AccessibilityMode.SCREEN_READER
            self.settings.screen_reader_integration = True
            self.settings.verbose_navigation = True
            logger.info("Screen reader detected, enabling accessibility mode")
    
    async def announce(self, text: str, feedback_type: str = None) -> None:
        """
        Announce text with appropriate feedback.
        
        Args:
            text: Text to announce
            feedback_type: Optional sound to play
        """
        # Play audio feedback
        if feedback_type:
            await self.audio.play(feedback_type)
        
        # Trigger haptic
        await self.haptic.trigger("light")
        
        # Announce through screen reader or TTS
        if self.settings.screen_reader_integration:
            await self.screen_reader.announce(text)
        elif self.settings.enable_speech_feedback:
            # Use TTS
            await self._speak(text)
    
    async def _speak(self, text: str) -> None:
        """Speak text using TTS."""
        try:
            if platform.system() == "Darwin":
                rate = int(self.settings.speech_rate * 175)  # Default is ~175 wpm
                
                await asyncio.create_subprocess_exec(
                    "say",
                    "-r", str(rate),
                    text,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
        except Exception as e:
            logger.debug(f"TTS error: {e}")
    
    async def confirm(self, prompt: str) -> bool:
        """
        Request voice confirmation.
        
        Returns True if user confirms.
        """
        await self.announce(f"{prompt}。請說「確認」或「取消」", "confirmation")
        
        # In real implementation, would listen for response
        # For now, return True (would integrate with voice recognition)
        return True
    
    def navigate(self, command: str) -> str:
        """
        Process navigation command.
        
        Returns announcement text.
        """
        command_lower = command.lower()
        
        if "返回" in command_lower or "back" in command_lower:
            _, announcement = self.navigation.go_back()
        elif "主選單" in command_lower or "home" in command_lower:
            _, announcement = self.navigation.go_home()
        elif "選項" in command_lower or "列出" in command_lower or "list" in command_lower:
            _, announcement = self.navigation.list_options()
        elif "說明" in command_lower or "help" in command_lower:
            announcement = self.navigation.get_help()
        else:
            _, announcement = self.navigation.navigate_to(command)
        
        return announcement
    
    def update_settings(self, **kwargs) -> None:
        """Update accessibility settings."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        
        # Apply changes
        self.audio._enabled = self.settings.enable_audio_feedback
        self.haptic._enabled = self.settings.enable_haptic_feedback
    
    def get_quick_help(self) -> str:
        """Get quick accessibility help."""
        return """無障礙功能說明：
- 語音導航：說「選項」查看可用選項
- 語速調整：說「語速快一點」或「語速慢一點」
- 重複：說「再說一次」重複上一個回應
- 幫助：說「幫助」取得更多說明
- 暫停：說「暫停」停止當前操作"""
    
    def get_settings_summary(self) -> str:
        """Get current accessibility settings summary."""
        mode_names = {
            AccessibilityMode.STANDARD: "標準",
            AccessibilityMode.SCREEN_READER: "螢幕閱讀器",
            AccessibilityMode.VOICE_ONLY: "純語音",
            AccessibilityMode.LOW_VISION: "低視力",
            AccessibilityMode.MOTOR_IMPAIRED: "行動輔助",
        }
        
        return f"""無障礙設定：
- 模式：{mode_names.get(self.settings.mode, '標準')}
- 語速：{self.settings.speech_rate:.1f}x
- 音量：{int(self.settings.speech_volume * 100)}%
- 音效回饋：{'開啟' if self.settings.enable_audio_feedback else '關閉'}
- 觸覺回饋：{'開啟' if self.settings.enable_haptic_feedback else '關閉'}
- 詳細導航：{'開啟' if self.settings.verbose_navigation else '關閉'}"""


# ============================================
# Keyboard Shortcuts for Voice Commands
# ============================================

class VoiceShortcuts:
    """
    Manages voice command shortcuts for quick access.
    
    Allows users to define custom trigger phrases.
    """
    
    DEFAULT_SHORTCUTS = {
        # Navigation
        "主選單": "go_home",
        "返回": "go_back",
        "列出選項": "list_options",
        "說明": "show_help",
        
        # Speed
        "快一點": "speed_up",
        "慢一點": "speed_down",
        "正常速度": "speed_normal",
        
        # Volume
        "大聲一點": "volume_up",
        "小聲一點": "volume_down",
        
        # Control
        "暫停": "pause",
        "繼續": "resume",
        "停止": "stop",
        "重複": "repeat",
        "取消": "cancel",
    }
    
    def __init__(self):
        self._shortcuts = dict(self.DEFAULT_SHORTCUTS)
        self._custom_shortcuts: Dict[str, str] = {}
    
    def add_shortcut(self, phrase: str, action: str) -> None:
        """Add a custom shortcut."""
        self._custom_shortcuts[phrase.lower()] = action
    
    def remove_shortcut(self, phrase: str) -> bool:
        """Remove a custom shortcut."""
        phrase_lower = phrase.lower()
        if phrase_lower in self._custom_shortcuts:
            del self._custom_shortcuts[phrase_lower]
            return True
        return False
    
    def get_action(self, phrase: str) -> Optional[str]:
        """Get action for a phrase."""
        phrase_lower = phrase.lower()
        
        # Check custom first
        if phrase_lower in self._custom_shortcuts:
            return self._custom_shortcuts[phrase_lower]
        
        # Check defaults
        for trigger, action in self._shortcuts.items():
            if trigger in phrase_lower:
                return action
        
        return None
    
    def list_shortcuts(self) -> Dict[str, str]:
        """List all shortcuts."""
        all_shortcuts = dict(self._shortcuts)
        all_shortcuts.update(self._custom_shortcuts)
        return all_shortcuts


# ============================================
# Global Instance
# ============================================

_accessibility_manager: Optional[AccessibilityManager] = None


def get_accessibility_manager() -> AccessibilityManager:
    global _accessibility_manager
    if _accessibility_manager is None:
        _accessibility_manager = AccessibilityManager()
    return _accessibility_manager


__all__ = [
    # Settings
    "AccessibilitySettings",
    "AccessibilityMode",
    "FeedbackType",
    # Screen Reader
    "ScreenReaderBridge",
    # Navigation
    "VoiceNavigation",
    "NavigationNode",
    # Feedback
    "AudioFeedback",
    "HapticFeedback",
    # Manager
    "AccessibilityManager",
    "get_accessibility_manager",
    # Shortcuts
    "VoiceShortcuts",
]
