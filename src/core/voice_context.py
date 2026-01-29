"""
Voice Context Awareness System for CursorBot v1.1

Provides context-aware features:
- Time-based context (morning, afternoon, evening)
- Location context (home, office, travel)
- Activity context (working, relaxing, commuting)
- Device context (desktop, mobile)
- App context (current application)
- Conversation context (recent interactions)
- User preferences (learned patterns)

Usage:
    from src.core.voice_context import get_context_engine
    
    engine = get_context_engine()
    context = await engine.get_current_context()
    response = engine.contextualize_response("查一下天氣", context)
"""

import os
import asyncio
import platform
import subprocess
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..utils.logger import logger


# ============================================
# Enums
# ============================================

class TimeOfDay(Enum):
    """Time of day context."""
    EARLY_MORNING = "early_morning"  # 5-8
    MORNING = "morning"              # 8-12
    AFTERNOON = "afternoon"          # 12-17
    EVENING = "evening"              # 17-21
    NIGHT = "night"                  # 21-24
    LATE_NIGHT = "late_night"        # 0-5


class DayType(Enum):
    """Day type context."""
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


class LocationType(Enum):
    """Location context."""
    HOME = "home"
    OFFICE = "office"
    COMMUTE = "commute"
    OUTDOOR = "outdoor"
    TRAVEL = "travel"
    UNKNOWN = "unknown"


class ActivityType(Enum):
    """User activity context."""
    WORKING = "working"
    CODING = "coding"
    MEETING = "meeting"
    RELAXING = "relaxing"
    SLEEPING = "sleeping"
    EXERCISING = "exercising"
    EATING = "eating"
    COMMUTING = "commuting"
    UNKNOWN = "unknown"


class DeviceType(Enum):
    """Device context."""
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    PHONE = "phone"
    TABLET = "tablet"
    WATCH = "watch"
    CAR = "car"
    SMART_SPEAKER = "smart_speaker"


# ============================================
# Data Classes
# ============================================

@dataclass
class TimeContext:
    """Time-related context."""
    time_of_day: TimeOfDay
    day_type: DayType
    hour: int
    weekday: int  # 0=Monday, 6=Sunday
    date: datetime
    is_work_hours: bool = False


@dataclass
class LocationContext:
    """Location-related context."""
    type: LocationType
    wifi_ssid: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


@dataclass
class ActivityContext:
    """Activity-related context."""
    type: ActivityType
    current_app: Optional[str] = None
    recent_apps: List[str] = field(default_factory=list)
    is_screen_active: bool = True
    audio_playing: bool = False


@dataclass
class DeviceContext:
    """Device-related context."""
    type: DeviceType
    platform: str  # darwin, windows, linux
    hostname: str = ""
    battery_level: Optional[int] = None
    is_charging: bool = False
    network_type: str = "unknown"  # wifi, cellular, ethernet


@dataclass
class UserContext:
    """User preference context."""
    name: str = ""
    language: str = "zh-TW"
    voice_style: str = "friendly"
    preferred_assistant_name: str = "小助手"
    work_start_hour: int = 9
    work_end_hour: int = 18
    home_wifi: List[str] = field(default_factory=list)
    office_wifi: List[str] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Conversation context."""
    recent_topics: List[str] = field(default_factory=list)
    recent_entities: Dict[str, Any] = field(default_factory=dict)
    follow_up_expected: bool = False
    last_intent: Optional[str] = None
    conversation_start: Optional[datetime] = None


@dataclass
class FullContext:
    """Complete context snapshot."""
    time: TimeContext
    location: LocationContext
    activity: ActivityContext
    device: DeviceContext
    user: UserContext
    conversation: ConversationContext
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================
# Context Providers
# ============================================

class TimeContextProvider:
    """Provides time-related context."""
    
    def get_context(self) -> TimeContext:
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()
        
        # Determine time of day
        if 5 <= hour < 8:
            time_of_day = TimeOfDay.EARLY_MORNING
        elif 8 <= hour < 12:
            time_of_day = TimeOfDay.MORNING
        elif 12 <= hour < 17:
            time_of_day = TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            time_of_day = TimeOfDay.EVENING
        elif 21 <= hour < 24:
            time_of_day = TimeOfDay.NIGHT
        else:
            time_of_day = TimeOfDay.LATE_NIGHT
        
        # Determine day type
        day_type = DayType.WEEKEND if weekday >= 5 else DayType.WEEKDAY
        
        # Work hours (default 9-18, weekdays)
        is_work_hours = (
            day_type == DayType.WEEKDAY and
            9 <= hour < 18
        )
        
        return TimeContext(
            time_of_day=time_of_day,
            day_type=day_type,
            hour=hour,
            weekday=weekday,
            date=now,
            is_work_hours=is_work_hours
        )


class LocationContextProvider:
    """Provides location-related context."""
    
    def __init__(self, user_context: UserContext):
        self.user_context = user_context
    
    async def get_context(self) -> LocationContext:
        wifi_ssid = await self._get_wifi_ssid()
        
        # Determine location based on WiFi
        location_type = LocationType.UNKNOWN
        
        if wifi_ssid:
            if wifi_ssid in self.user_context.home_wifi:
                location_type = LocationType.HOME
            elif wifi_ssid in self.user_context.office_wifi:
                location_type = LocationType.OFFICE
        
        return LocationContext(
            type=location_type,
            wifi_ssid=wifi_ssid
        )
    
    async def _get_wifi_ssid(self) -> Optional[str]:
        """Get current WiFi SSID."""
        system = platform.system()
        
        try:
            if system == "Darwin":
                cmd = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | grep ' SSID' | awk '{print $2}'"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                return stdout.decode().strip() or None
            
            elif system == "Windows":
                cmd = "netsh wlan show interfaces | findstr /R \"^....SSID\""
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                output = stdout.decode().strip()
                if output:
                    return output.split(":")[-1].strip()
            
            elif system == "Linux":
                cmd = "iwgetid -r"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                return stdout.decode().strip() or None
                
        except Exception as e:
            logger.debug(f"Could not get WiFi SSID: {e}")
        
        return None


class ActivityContextProvider:
    """Provides activity-related context."""
    
    def __init__(self):
        self._system = platform.system()
    
    async def get_context(self) -> ActivityContext:
        current_app = await self._get_active_app()
        is_screen_active = await self._is_screen_active()
        audio_playing = await self._is_audio_playing()
        
        # Infer activity from app
        activity_type = self._infer_activity(current_app)
        
        return ActivityContext(
            type=activity_type,
            current_app=current_app,
            is_screen_active=is_screen_active,
            audio_playing=audio_playing
        )
    
    async def _get_active_app(self) -> Optional[str]:
        """Get currently active application."""
        try:
            if self._system == "Darwin":
                cmd = """osascript -e 'tell application "System Events" to get name of first process where frontmost is true'"""
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                return stdout.decode().strip() or None
            
            elif self._system == "Windows":
                # Would need pywin32 or similar
                pass
                
        except Exception as e:
            logger.debug(f"Could not get active app: {e}")
        
        return None
    
    async def _is_screen_active(self) -> bool:
        """Check if screen is active (not locked/sleeping)."""
        try:
            if self._system == "Darwin":
                # Check display sleep status
                cmd = "ioreg -c AppleBacklightDisplay | grep 'brightness'"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                return bool(stdout)
        except Exception:
            pass
        
        return True  # Default to active
    
    async def _is_audio_playing(self) -> bool:
        """Check if audio is currently playing."""
        try:
            if self._system == "Darwin":
                cmd = "pmset -g | grep 'sleep'"
                # This is a simplification - would need more complex logic
                pass
        except Exception:
            pass
        
        return False
    
    def _infer_activity(self, app: Optional[str]) -> ActivityType:
        """Infer user activity from current app."""
        if not app:
            return ActivityType.UNKNOWN
        
        app_lower = app.lower()
        
        coding_apps = ["cursor", "code", "visual studio", "xcode", "intellij", "pycharm", "webstorm"]
        meeting_apps = ["zoom", "teams", "meet", "webex", "slack"]
        relax_apps = ["spotify", "netflix", "youtube", "music", "safari", "chrome"]
        
        for coding_app in coding_apps:
            if coding_app in app_lower:
                return ActivityType.CODING
        
        for meeting_app in meeting_apps:
            if meeting_app in app_lower:
                return ActivityType.MEETING
        
        for relax_app in relax_apps:
            if relax_app in app_lower:
                return ActivityType.RELAXING
        
        return ActivityType.WORKING


class DeviceContextProvider:
    """Provides device-related context."""
    
    def __init__(self):
        self._system = platform.system().lower()
    
    async def get_context(self) -> DeviceContext:
        device_type = self._determine_device_type()
        battery = await self._get_battery_info()
        hostname = platform.node()
        
        return DeviceContext(
            type=device_type,
            platform=self._system,
            hostname=hostname,
            battery_level=battery.get("level") if battery else None,
            is_charging=battery.get("charging", False) if battery else False
        )
    
    def _determine_device_type(self) -> DeviceType:
        """Determine device type."""
        if self._system == "darwin":
            # Check if laptop or desktop
            try:
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"],
                    capture_output=True, text=True
                )
                if "MacBook" in result.stdout:
                    return DeviceType.LAPTOP
                else:
                    return DeviceType.DESKTOP
            except Exception:
                pass
        
        return DeviceType.DESKTOP
    
    async def _get_battery_info(self) -> Optional[Dict]:
        """Get battery information."""
        try:
            if self._system == "darwin":
                cmd = "pmset -g batt"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                output = stdout.decode()
                
                # Parse battery percentage
                import re
                match = re.search(r"(\d+)%", output)
                if match:
                    level = int(match.group(1))
                    charging = "charging" in output.lower() or "AC Power" in output
                    return {"level": level, "charging": charging}
                    
        except Exception as e:
            logger.debug(f"Could not get battery info: {e}")
        
        return None


# ============================================
# Context Engine
# ============================================

class ContextEngine:
    """
    Central context engine for voice assistant.
    
    Aggregates context from multiple providers and provides
    context-aware features.
    """
    
    def __init__(self):
        self._user_context = UserContext()
        self._conversation_context = ConversationContext()
        
        # Initialize providers
        self._time_provider = TimeContextProvider()
        self._location_provider = LocationContextProvider(self._user_context)
        self._activity_provider = ActivityContextProvider()
        self._device_provider = DeviceContextProvider()
        
        # Context cache
        self._cache: Optional[FullContext] = None
        self._cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=10)
        
        # User preferences file
        self._prefs_file = Path.home() / ".cursorbot" / "voice_prefs.json"
        self._load_preferences()
    
    async def get_current_context(self, force_refresh: bool = False) -> FullContext:
        """
        Get current context snapshot.
        
        Args:
            force_refresh: Force refresh even if cached
            
        Returns:
            FullContext snapshot
        """
        # Check cache
        if not force_refresh and self._cache and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_duration:
                return self._cache
        
        # Gather context from all providers
        time_ctx = self._time_provider.get_context()
        
        # Run async providers concurrently
        location_ctx, activity_ctx, device_ctx = await asyncio.gather(
            self._location_provider.get_context(),
            self._activity_provider.get_context(),
            self._device_provider.get_context()
        )
        
        context = FullContext(
            time=time_ctx,
            location=location_ctx,
            activity=activity_ctx,
            device=device_ctx,
            user=self._user_context,
            conversation=self._conversation_context
        )
        
        # Cache
        self._cache = context
        self._cache_time = datetime.now()
        
        return context
    
    def get_greeting(self, context: Optional[FullContext] = None) -> str:
        """Get contextual greeting."""
        if context is None:
            time_ctx = self._time_provider.get_context()
        else:
            time_ctx = context.time
        
        name = self._user_context.name or ""
        name_suffix = f"，{name}" if name else ""
        
        greetings = {
            TimeOfDay.EARLY_MORNING: f"早安{name_suffix}！這麼早就起來了呢。",
            TimeOfDay.MORNING: f"早安{name_suffix}！今天也請多多指教。",
            TimeOfDay.AFTERNOON: f"下午好{name_suffix}！",
            TimeOfDay.EVENING: f"晚上好{name_suffix}！",
            TimeOfDay.NIGHT: f"夜深了{name_suffix}，需要什麼幫忙嗎？",
            TimeOfDay.LATE_NIGHT: f"{name_suffix}還沒睡嗎？注意休息哦。",
        }
        
        return greetings.get(time_ctx.time_of_day, f"你好{name_suffix}！")
    
    def contextualize_response(self, query: str, context: FullContext) -> str:
        """
        Add contextual information to enhance response.
        
        Args:
            query: User's query
            context: Current context
            
        Returns:
            Contextualized prompt additions
        """
        additions = []
        
        # Time context
        time_info = f"現在是{context.time.date.strftime('%Y年%m月%d日')}，"
        time_info += f"{'週末' if context.time.day_type == DayType.WEEKEND else '平日'}，"
        time_info += f"{self._get_time_description(context.time.time_of_day)}。"
        additions.append(time_info)
        
        # Location context
        if context.location.type != LocationType.UNKNOWN:
            loc_map = {
                LocationType.HOME: "用戶目前在家",
                LocationType.OFFICE: "用戶目前在辦公室",
            }
            if context.location.type in loc_map:
                additions.append(loc_map[context.location.type])
        
        # Activity context
        if context.activity.current_app:
            additions.append(f"用戶正在使用 {context.activity.current_app}")
        
        activity_map = {
            ActivityType.CODING: "用戶正在編寫程式",
            ActivityType.MEETING: "用戶正在開會",
        }
        if context.activity.type in activity_map:
            additions.append(activity_map[context.activity.type])
        
        # Device context
        if context.device.battery_level and context.device.battery_level < 20:
            if not context.device.is_charging:
                additions.append("注意：設備電量較低")
        
        return "\n".join(additions)
    
    def _get_time_description(self, time_of_day: TimeOfDay) -> str:
        """Get human-readable time description."""
        descriptions = {
            TimeOfDay.EARLY_MORNING: "清晨",
            TimeOfDay.MORNING: "上午",
            TimeOfDay.AFTERNOON: "下午",
            TimeOfDay.EVENING: "傍晚",
            TimeOfDay.NIGHT: "晚上",
            TimeOfDay.LATE_NIGHT: "深夜",
        }
        return descriptions.get(time_of_day, "")
    
    # ============================================
    # Conversation Context
    # ============================================
    
    def update_conversation(
        self,
        topic: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None
    ) -> None:
        """Update conversation context."""
        if topic:
            self._conversation_context.recent_topics.append(topic)
            # Keep only recent topics
            if len(self._conversation_context.recent_topics) > 10:
                self._conversation_context.recent_topics.pop(0)
        
        if entities:
            self._conversation_context.recent_entities.update(entities)
        
        if intent:
            self._conversation_context.last_intent = intent
        
        if not self._conversation_context.conversation_start:
            self._conversation_context.conversation_start = datetime.now()
    
    def clear_conversation(self) -> None:
        """Clear conversation context."""
        self._conversation_context = ConversationContext()
    
    def get_follow_up_context(self) -> Dict[str, Any]:
        """Get context for follow-up questions."""
        return {
            "recent_topics": self._conversation_context.recent_topics[-3:],
            "entities": self._conversation_context.recent_entities,
            "last_intent": self._conversation_context.last_intent,
        }
    
    # ============================================
    # User Preferences
    # ============================================
    
    def set_user_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        if hasattr(self._user_context, key):
            setattr(self._user_context, key, value)
            self._save_preferences()
    
    def _load_preferences(self) -> None:
        """Load user preferences from file."""
        try:
            if self._prefs_file.exists():
                with open(self._prefs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for key, value in data.items():
                    if hasattr(self._user_context, key):
                        setattr(self._user_context, key, value)
                
                logger.debug("Loaded voice preferences")
        except Exception as e:
            logger.debug(f"Could not load preferences: {e}")
    
    def _save_preferences(self) -> None:
        """Save user preferences to file."""
        try:
            self._prefs_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "name": self._user_context.name,
                "language": self._user_context.language,
                "voice_style": self._user_context.voice_style,
                "preferred_assistant_name": self._user_context.preferred_assistant_name,
                "work_start_hour": self._user_context.work_start_hour,
                "work_end_hour": self._user_context.work_end_hour,
                "home_wifi": self._user_context.home_wifi,
                "office_wifi": self._user_context.office_wifi,
            }
            
            with open(self._prefs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.debug(f"Could not save preferences: {e}")
    
    # ============================================
    # Smart Suggestions
    # ============================================
    
    def get_suggestions(self, context: FullContext) -> List[str]:
        """Get contextual suggestions for the user."""
        suggestions = []
        
        # Morning suggestions
        if context.time.time_of_day == TimeOfDay.MORNING:
            suggestions.extend([
                "查看今天的行程",
                "閱讀新聞摘要",
                "查看天氣",
            ])
        
        # Work hour suggestions
        if context.time.is_work_hours:
            if context.activity.type == ActivityType.CODING:
                suggestions.extend([
                    "執行 Git commit",
                    "執行測試",
                    "搜尋文件",
                ])
        
        # Evening suggestions
        if context.time.time_of_day in (TimeOfDay.EVENING, TimeOfDay.NIGHT):
            suggestions.extend([
                "播放音樂",
                "設定明天的提醒",
            ])
        
        # Battery low suggestion
        if context.device.battery_level and context.device.battery_level < 20:
            if not context.device.is_charging:
                suggestions.insert(0, "電量較低，建議充電")
        
        return suggestions[:5]  # Return top 5


# ============================================
# Global Instance
# ============================================

_context_engine: Optional[ContextEngine] = None


def get_context_engine() -> ContextEngine:
    """Get or create the global context engine."""
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine()
    return _context_engine


__all__ = [
    # Enums
    "TimeOfDay",
    "DayType",
    "LocationType",
    "ActivityType",
    "DeviceType",
    # Data classes
    "TimeContext",
    "LocationContext",
    "ActivityContext",
    "DeviceContext",
    "UserContext",
    "ConversationContext",
    "FullContext",
    # Engine
    "ContextEngine",
    "get_context_engine",
]
