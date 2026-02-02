"""
Calendar Reminder System for CursorBot v1.1

Provides:
- Daily calendar reminder at 7:00 AM
- Per-user reminder settings
- Multi-platform notification support (Telegram, Discord, LINE, etc.)
- Google Calendar and Apple Calendar integration

Usage:
    from src.core.calendar_reminder import get_reminder_service
    
    service = get_reminder_service()
    await service.start()
    
    # Enable reminder for a user
    service.enable_reminder(user_id="123456", platform="telegram", chat_id="123456")
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import json
from pathlib import Path

from ..utils.logger import logger
from ..utils.config import settings


class ReminderPlatform(Enum):
    """Supported platforms for reminders."""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    LINE = "line"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    TEAMS = "teams"
    GOOGLE_CHAT = "google_chat"


@dataclass
class ReminderSettings:
    """User reminder settings."""
    user_id: str
    platform: ReminderPlatform
    chat_id: str
    enabled: bool = True
    reminder_time: time = field(default_factory=lambda: time(7, 0))  # 7:00 AM
    timezone: str = "Asia/Taipei"
    include_weather: bool = True
    include_summary: bool = True
    quiet_weekends: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_sent: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "platform": self.platform.value,
            "chat_id": self.chat_id,
            "enabled": self.enabled,
            "reminder_time": self.reminder_time.strftime("%H:%M"),
            "timezone": self.timezone,
            "include_weather": self.include_weather,
            "include_summary": self.include_summary,
            "quiet_weekends": self.quiet_weekends,
            "created_at": self.created_at.isoformat(),
            "last_sent": self.last_sent.isoformat() if self.last_sent else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ReminderSettings":
        reminder_time_str = data.get("reminder_time", "07:00")
        hour, minute = map(int, reminder_time_str.split(":"))
        
        return cls(
            user_id=data["user_id"],
            platform=ReminderPlatform(data["platform"]),
            chat_id=data["chat_id"],
            enabled=data.get("enabled", True),
            reminder_time=time(hour, minute),
            timezone=data.get("timezone", "Asia/Taipei"),
            include_weather=data.get("include_weather", True),
            include_summary=data.get("include_summary", True),
            quiet_weekends=data.get("quiet_weekends", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_sent=datetime.fromisoformat(data["last_sent"]) if data.get("last_sent") else None,
        )


@dataclass
class CalendarEventSummary:
    """Summary of a calendar event for reminder."""
    title: str
    start_time: str
    end_time: str
    location: str = ""
    is_all_day: bool = False
    
    def format(self) -> str:
        if self.is_all_day:
            result = f"📌 {self.title} (整天)"
        else:
            result = f"⏰ {self.start_time} - {self.title}"
        
        if self.location:
            result += f"\n   📍 {self.location}"
        
        return result


class CalendarReminderService:
    """
    Calendar reminder service that sends daily reminders.
    
    Features:
    - Multi-platform support
    - Customizable reminder time per user
    - Google Calendar and Apple Calendar integration
    - Weather integration (optional)
    """
    
    def __init__(self):
        self._settings: dict[str, ReminderSettings] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._data_file = Path("data/reminder_settings.json")
        self._send_handlers: dict[ReminderPlatform, Callable] = {}
        
        # Load saved settings
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load reminder settings from file."""
        if self._data_file.exists():
            try:
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self._settings[key] = ReminderSettings.from_dict(value)
                logger.info(f"Loaded {len(self._settings)} reminder settings")
            except Exception as e:
                logger.error(f"Failed to load reminder settings: {e}")
    
    def _save_settings(self) -> None:
        """Save reminder settings to file."""
        try:
            self._data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._data_file, "w", encoding="utf-8") as f:
                data = {k: v.to_dict() for k, v in self._settings.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save reminder settings: {e}")
    
    def register_send_handler(self, platform: ReminderPlatform, handler: Callable) -> None:
        """
        Register a message send handler for a platform.
        
        Args:
            platform: The platform
            handler: Async function that takes (chat_id, message) and sends message
        """
        self._send_handlers[platform] = handler
        logger.info(f"Registered send handler for {platform.value}")
    
    async def start(self) -> None:
        """Start the reminder service."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Calendar reminder service started")
    
    async def stop(self) -> None:
        """Stop the reminder service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Calendar reminder service stopped")
    
    async def _run_loop(self) -> None:
        """Main service loop - checks every minute."""
        while self._running:
            try:
                now = datetime.now()
                
                # Check each user's reminder
                for key, settings in self._settings.items():
                    if not settings.enabled:
                        continue
                    
                    # Check if it's time to send reminder
                    if self._should_send_reminder(settings, now):
                        await self._send_reminder(settings)
                
                # Wait until next minute
                await asyncio.sleep(60 - now.second)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reminder service error: {e}")
                await asyncio.sleep(60)
    
    def _should_send_reminder(self, settings: ReminderSettings, now: datetime) -> bool:
        """Check if reminder should be sent for this user."""
        # Check time
        if now.hour != settings.reminder_time.hour or now.minute != settings.reminder_time.minute:
            return False
        
        # Check weekend
        if settings.quiet_weekends and now.weekday() >= 5:
            return False
        
        # Check if already sent today
        if settings.last_sent:
            if settings.last_sent.date() == now.date():
                return False
        
        return True
    
    async def _send_reminder(self, settings: ReminderSettings, retry_count: int = 0) -> None:
        """Send reminder to user with retry on failure."""
        max_retries = 3
        retry_delay = 30  # seconds
        
        try:
            # Get today's events
            events = await self._get_today_events(settings.user_id)
            
            # Build message
            message = self._build_reminder_message(events, settings)
            
            # Send via platform handler
            handler = self._send_handlers.get(settings.platform)
            if handler:
                await handler(settings.chat_id, message)
                logger.info(f"Sent reminder to {settings.user_id} via {settings.platform.value}")
            else:
                logger.warning(f"No handler for platform {settings.platform.value}")
            
            # Update last sent
            settings.last_sent = datetime.now()
            self._save_settings()
            
        except Exception as e:
            logger.error(f"Failed to send reminder to {settings.user_id} (attempt {retry_count + 1}): {e}")
            
            # Retry on network errors
            if retry_count < max_retries:
                logger.info(f"Retrying reminder for {settings.user_id} in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                await self._send_reminder(settings, retry_count + 1)
            else:
                logger.error(f"Gave up sending reminder to {settings.user_id} after {max_retries + 1} attempts")
    
    async def _get_today_events(self, user_id: str) -> list[CalendarEventSummary]:
        """Get today's calendar events for a user."""
        events = []
        
        # Try Google Calendar
        try:
            from .google_calendar import get_calendar_manager, GOOGLE_API_AVAILABLE
            
            if GOOGLE_API_AVAILABLE:
                calendar = get_calendar_manager()
                if calendar.is_authenticated():
                    google_events = await calendar.get_events_today()
                    for event in google_events:
                        start_time = event.start.strftime("%H:%M") if event.start else ""
                        end_time = event.end.strftime("%H:%M") if event.end else ""
                        
                        events.append(CalendarEventSummary(
                            title=event.title,
                            start_time=start_time,
                            end_time=end_time,
                            location=event.location or "",
                            is_all_day=(start_time == "00:00" and end_time == "00:00"),
                        ))
        except Exception as e:
            logger.debug(f"Google Calendar not available: {e}")
        
        # Try Apple Calendar (macOS only)
        try:
            import platform as plat
            if plat.system() == "Darwin":
                from .apple_calendar import get_apple_calendar
                
                apple_cal = get_apple_calendar()
                if apple_cal.is_available():
                    # get_events_today is synchronous, run in executor
                    import asyncio
                    loop = asyncio.get_event_loop()
                    apple_events = await loop.run_in_executor(None, apple_cal.get_events_today)
                    
                    for event in apple_events:
                        start_time = event.start_time.strftime("%H:%M") if event.start_time else ""
                        end_time = event.end_time.strftime("%H:%M") if event.end_time else ""
                        
                        events.append(CalendarEventSummary(
                            title=event.title,
                            start_time=start_time,
                            end_time=end_time,
                            location=event.location or "",
                            is_all_day=event.all_day,
                        ))
        except Exception as e:
            logger.debug(f"Apple Calendar not available: {e}")
        
        # Sort by start time
        events.sort(key=lambda e: e.start_time)
        
        return events
    
    def _build_reminder_message(
        self,
        events: list[CalendarEventSummary],
        settings: ReminderSettings
    ) -> str:
        """Build the reminder message with secretary persona."""
        from .secretary import get_secretary, SecretaryPersona
        
        secretary = get_secretary()
        prefs = secretary.get_preferences(settings.user_id)
        persona = SecretaryPersona
        
        now = datetime.now()
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        weekday = weekdays[now.weekday()]
        date_str = now.strftime("%Y年%m月%d日")
        
        lines = [
            persona.greeting(prefs.name),
            "",
            f"📅 今天是 {date_str} {weekday}",
            "",
        ]
        
        if events:
            lines.append(f"📋 {persona.calendar_reminder(len(events))}")
            lines.append("")
            
            for event in events:
                lines.append(event.format())
            
            lines.append("")
        else:
            lines.append(f"✨ {persona.calendar_reminder(0)}")
            lines.append("")
        
        # Get tasks
        tasks = secretary.get_today_tasks(settings.user_id)
        all_tasks = secretary.get_tasks(settings.user_id)
        
        if all_tasks:
            lines.append(f"✅ {persona.task_reminder(len(all_tasks))}")
            if tasks:
                lines.append("今天到期的任務：")
                for task in tasks[:3]:
                    lines.append(f"  • {task.title}")
            lines.append("")
        
        # Add care message (randomly)
        import random
        if random.random() < 0.5:
            lines.append(f"💕 {persona.care_message()}")
            lines.append("")
        
        # Sign off with secretary name
        lines.append(f"—— {prefs.secretary_name} {persona.sign_off()}")
        
        return "\n".join(lines)
    
    # ============================================
    # Public API
    # ============================================
    
    def enable_reminder(
        self,
        user_id: str,
        platform: str,
        chat_id: str,
        reminder_time: str = "07:00",
        timezone: str = "Asia/Taipei",
    ) -> ReminderSettings:
        """
        Enable daily reminder for a user.
        
        Args:
            user_id: User ID
            platform: Platform name (telegram, discord, etc.)
            chat_id: Chat/Channel ID for sending messages
            reminder_time: Time to send reminder (HH:MM format)
            timezone: User's timezone
        
        Returns:
            ReminderSettings instance
        """
        hour, minute = map(int, reminder_time.split(":"))
        
        key = f"{platform}:{user_id}"
        settings = ReminderSettings(
            user_id=user_id,
            platform=ReminderPlatform(platform),
            chat_id=chat_id,
            reminder_time=time(hour, minute),
            timezone=timezone,
        )
        
        self._settings[key] = settings
        self._save_settings()
        
        logger.info(f"Enabled reminder for {user_id} at {reminder_time}")
        return settings
    
    def disable_reminder(self, user_id: str, platform: str) -> bool:
        """Disable reminder for a user."""
        key = f"{platform}:{user_id}"
        if key in self._settings:
            self._settings[key].enabled = False
            self._save_settings()
            logger.info(f"Disabled reminder for {user_id}")
            return True
        return False
    
    def update_reminder_time(self, user_id: str, platform: str, reminder_time: str) -> bool:
        """Update reminder time for a user."""
        key = f"{platform}:{user_id}"
        if key in self._settings:
            hour, minute = map(int, reminder_time.split(":"))
            self._settings[key].reminder_time = time(hour, minute)
            self._save_settings()
            logger.info(f"Updated reminder time for {user_id} to {reminder_time}")
            return True
        return False
    
    def get_settings(self, user_id: str, platform: str) -> Optional[ReminderSettings]:
        """Get reminder settings for a user."""
        key = f"{platform}:{user_id}"
        return self._settings.get(key)
    
    def list_all_reminders(self) -> list[ReminderSettings]:
        """List all reminder settings."""
        return list(self._settings.values())
    
    def get_status_message(self, user_id: str, platform: str) -> str:
        """Get status message for a user's reminder settings."""
        settings = self.get_settings(user_id, platform)
        
        if not settings:
            return """📅 **行程提醒設定**

狀態: ⚪ 尚未啟用

**啟用提醒:**
/reminder on - 啟用每日行程提醒
/reminder time 07:00 - 設定提醒時間
/reminder off - 關閉提醒

**功能:**
• 每日早上發送當日行程
• 支援 Google 日曆 / Apple 日曆
• 自訂提醒時間
"""
        
        status = "✅ 已啟用" if settings.enabled else "⏸️ 已暫停"
        time_str = settings.reminder_time.strftime("%H:%M")
        last_sent = settings.last_sent.strftime("%Y/%m/%d %H:%M") if settings.last_sent else "尚未發送"
        
        return f"""📅 **行程提醒設定**

狀態: {status}
提醒時間: {time_str}
時區: {settings.timezone}
上次發送: {last_sent}

**設定選項:**
• 週末靜音: {'是' if settings.quiet_weekends else '否'}
• 包含摘要: {'是' if settings.include_summary else '否'}

**指令:**
/reminder off - 關閉提醒
/reminder time HH:MM - 設定時間
/reminder weekend [on|off] - 週末設定
"""
    
    async def send_test_reminder(self, user_id: str, platform: str) -> bool:
        """Send a test reminder to verify settings."""
        settings = self.get_settings(user_id, platform)
        if not settings:
            return False
        
        try:
            events = await self._get_today_events(user_id)
            message = "🔔 **測試提醒**\n\n" + self._build_reminder_message(events, settings)
            
            handler = self._send_handlers.get(settings.platform)
            if handler:
                await handler(settings.chat_id, message)
                return True
        except Exception as e:
            logger.error(f"Test reminder failed: {e}")
        
        return False


# Global instance
_reminder_service: Optional[CalendarReminderService] = None


def get_reminder_service() -> CalendarReminderService:
    """Get the global CalendarReminderService instance."""
    global _reminder_service
    if _reminder_service is None:
        _reminder_service = CalendarReminderService()
    return _reminder_service


__all__ = [
    "CalendarReminderService",
    "ReminderSettings",
    "ReminderPlatform",
    "CalendarEventSummary",
    "get_reminder_service",
]
