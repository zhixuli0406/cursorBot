"""
Apple Calendar Integration for macOS

Provides integration with macOS Calendar.app using AppleScript.
Supports:
- Listing calendars
- Getting events (today, week, range)
- Creating events
- Updating events
- Deleting events

Requirements:
- macOS only
- Calendar.app permissions (System Preferences > Security & Privacy > Automation)
"""

import subprocess
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import platform

from ..utils.logger import logger


class CalendarError(Exception):
    """Calendar operation error."""
    pass


class EventStatus(Enum):
    """Event status types."""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


@dataclass
class CalendarInfo:
    """Calendar information."""
    name: str
    id: str
    color: str = ""
    writable: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "id": self.id,
            "color": self.color,
            "writable": self.writable,
        }


@dataclass
class CalendarEvent:
    """Calendar event."""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    calendar_name: str = ""
    location: str = ""
    notes: str = ""
    url: str = ""
    all_day: bool = False
    status: EventStatus = EventStatus.CONFIRMED
    attendees: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "calendar_name": self.calendar_name,
            "location": self.location,
            "notes": self.notes,
            "url": self.url,
            "all_day": self.all_day,
            "status": self.status.value,
            "attendees": self.attendees,
        }
    
    def format_display(self) -> str:
        """Format for display."""
        time_str = self.start_time.strftime("%H:%M") if not self.all_day else "整天"
        location_str = f" @ {self.location}" if self.location else ""
        return f"• {time_str} - {self.title}{location_str}"


class AppleCalendarManager:
    """
    Manager for Apple Calendar integration.
    
    Uses AppleScript to interact with Calendar.app on macOS.
    Includes caching to avoid frequent AppleScript calls.
    
    Environment variables:
        APPLE_CALENDAR_ENABLED: Enable/disable Apple Calendar (default: true)
        APPLE_CALENDAR_TIMEOUT: AppleScript timeout in seconds (default: 8)
        APPLE_CALENDAR_CACHE_TTL: Cache TTL in seconds (default: 60)
    """
    
    def __init__(self):
        """Initialize calendar manager."""
        import os
        
        self._available = None
        self._default_calendar = None
        self._events_cache: dict[str, tuple[datetime, list[CalendarEvent]]] = {}
        self._calendars_cache: tuple[datetime, list[CalendarInfo]] | None = None
        
        # Load settings from environment
        self.cache_ttl = int(os.getenv("APPLE_CALENDAR_CACHE_TTL", "60"))
        self.timeout = int(os.getenv("APPLE_CALENDAR_TIMEOUT", "8"))
        
        # Calendars to include (comma-separated list, empty = all)
        # Example: "工作,家族,行事曆"
        include_str = os.getenv("APPLE_CALENDAR_INCLUDE", "")
        self.include_calendars = [c.strip() for c in include_str.split(",") if c.strip()] if include_str else []
        
        # Calendars to exclude (comma-separated list)
        # Example: "台湾节假日,Holidays"
        exclude_str = os.getenv("APPLE_CALENDAR_EXCLUDE", "")
        self.exclude_calendars = [c.strip() for c in exclude_str.split(",") if c.strip()] if exclude_str else []
        
        if self.include_calendars:
            logger.info(f"Apple Calendar: only including calendars: {self.include_calendars}")
        if self.exclude_calendars:
            logger.info(f"Apple Calendar: excluding calendars: {self.exclude_calendars}")
    
    def is_available(self) -> bool:
        """Check if Apple Calendar is available (macOS only)."""
        if self._available is not None:
            return self._available
        
        # Check if Apple Calendar is disabled via environment variable
        import os
        if os.getenv("APPLE_CALENDAR_ENABLED", "true").lower() in ("false", "0", "no", "off"):
            logger.info("Apple Calendar disabled via APPLE_CALENDAR_ENABLED=false")
            self._available = False
            return False
        
        if platform.system() != "Darwin":
            logger.info("Apple Calendar is only available on macOS")
            self._available = False
            return False
        
        # Quick check - just verify we're on macOS, skip the slow Calendar.app test
        # The actual Calendar.app test will happen on first real query
        self._available = True
        logger.debug("Apple Calendar marked as available (macOS detected)")
        return self._available
    
    def _should_include_calendar(self, calendar_name: str) -> bool:
        """Check if a calendar should be included based on settings."""
        # If include list is specified, only include those
        if self.include_calendars:
            return calendar_name in self.include_calendars
        
        # If exclude list is specified, exclude those
        if self.exclude_calendars:
            return calendar_name not in self.exclude_calendars
        
        # Default: include all
        return True
    
    def _get_filtered_calendar_names(self) -> list[str]:
        """Get list of calendar names to query, applying filters."""
        # First, get all calendar names quickly
        script = 'tell application "Calendar" to return name of calendars'
        result = self._run_applescript(script, timeout=5)
        
        if not result:
            return []
        
        all_calendars = [name.strip() for name in result.split(", ") if name.strip()]
        
        # Apply filters
        filtered = [name for name in all_calendars if self._should_include_calendar(name)]
        
        if len(filtered) < len(all_calendars):
            logger.debug(f"Filtered calendars: {len(filtered)}/{len(all_calendars)}")
        
        return filtered
    
    def _run_applescript(self, script: str, timeout: int = 30, use_jxa: bool = False) -> Optional[str]:
        """Run AppleScript or JXA and return result."""
        try:
            if use_jxa:
                # Use osascript with -l JavaScript for JXA
                result = subprocess.run(
                    ["osascript", "-l", "JavaScript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            else:
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            
            if result.returncode != 0:
                if use_jxa:
                    logger.debug(f"JXA error: {result.stderr[:200]}")
                else:
                    logger.error(f"AppleScript error: {result.stderr}")
                return None
            
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"{'JXA' if use_jxa else 'AppleScript'} timeout after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"{'JXA' if use_jxa else 'AppleScript'} execution error: {e}")
            return None
    
    def list_calendars(self) -> list[CalendarInfo]:
        """List all calendars."""
        if not self.is_available():
            return []
        
        # Simple and fast: just get calendar names
        script = 'tell application "Calendar" to return name of calendars'
        
        result = self._run_applescript(script, timeout=15)
        if not result:
            return []
        
        calendars = []
        # Result is comma-separated list of names
        for name in result.split(", "):
            name = name.strip()
            if name:
                calendars.append(CalendarInfo(
                    name=name,
                    id=name,  # Use name as ID for simplicity
                ))
        
        return calendars
    
    def get_events_today(self, calendar_name: str = "") -> list[CalendarEvent]:
        """Get today's events."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return self.get_events(today, tomorrow, calendar_name)
    
    def get_events_week(self, calendar_name: str = "") -> list[CalendarEvent]:
        """Get this week's events."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Get to start of week (Monday)
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
        return self.get_events(start, end, calendar_name)
    
    def get_events(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_name: str = "",
        use_cache: bool = True,
    ) -> list[CalendarEvent]:
        """
        Get events in date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            calendar_name: Optional specific calendar name to query
            use_cache: Whether to use cached results (default True)
        
        Returns:
            List of CalendarEvent objects
        """
        if not self.is_available():
            return []
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Check cache first
        cache_key = f"{start_str}_{end_str}_{calendar_name}"
        if use_cache and cache_key in self._events_cache:
            cached_time, cached_events = self._events_cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                logger.debug(f"Using cached events for {cache_key}")
                return cached_events
        
        # Get filtered calendar names first (this is fast)
        calendar_names = self._get_filtered_calendar_names()
        if not calendar_names:
            logger.debug("No calendars to query")
            self._events_cache[cache_key] = (datetime.now(), [])
            return []
        
        logger.debug(f"Querying {len(calendar_names)} calendars for events")
        
        # Query each calendar individually with short timeout
        # This way slow calendars don't block everything
        all_events = []
        per_calendar_timeout = max(3, self.timeout // max(1, min(len(calendar_names), 5)))
        
        for cal_name in calendar_names:
            script = f'''
            tell application "Calendar"
                set eventList to {{}}
                set startDate to date "{start_str}"
                set endDate to date "{end_str}"
                
                try
                    set targetCal to calendar "{cal_name}"
                    set calEvents to (every event of targetCal whose start date >= startDate and start date < endDate)
                    repeat with evt in calEvents
                        try
                            set evtTitle to summary of evt
                            set evtStart to start date of evt
                            set evtLoc to ""
                            try
                                set evtLoc to location of evt
                            end try
                            set evtAllDay to allday event of evt
                            set evtInfo to evtTitle & "|||" & ((evtStart) as string) & "|||" & evtLoc & "|||" & evtAllDay & "|||" & "{cal_name}"
                            set end of eventList to evtInfo
                        on error
                            -- Skip problematic events
                        end try
                    end repeat
                on error errMsg
                    -- Calendar not accessible
                end try
                
                return eventList as string
            end tell
            '''
            
            result = self._run_applescript(script, timeout=per_calendar_timeout)
            if result:
                events = self._parse_applescript_events(result, start_str, end_str)
                all_events.extend(events)
            else:
                logger.debug(f"Calendar '{cal_name}' query failed or timed out")
        
        # Sort all events by start time
        all_events.sort(key=lambda e: e.start_time)
        
        # Cache the results
        self._events_cache[cache_key] = (datetime.now(), all_events)
        
        logger.info(f"Apple Calendar found {len(all_events)} events for {start_str} to {end_str}")
        return all_events
    
    def _parse_applescript_events(self, result: str, start_str: str, end_str: str) -> list[CalendarEvent]:
        """Parse AppleScript result into CalendarEvent list."""
        events = []
        
        # AppleScript returns comma-separated list
        for item in result.split(", "):
            if "|||" not in item:
                continue
            
            parts = item.split("|||")
            if len(parts) < 2:
                continue
            
            try:
                title = parts[0].strip()
                if not title:
                    continue
                
                # Parse date - parts[1] is either a timestamp or date string
                date_part = parts[1].strip()
                try:
                    # Try as timestamp first
                    timestamp = float(date_part)
                    start_time = datetime.fromtimestamp(timestamp)
                except ValueError:
                    # Parse as date string
                    start_time = self._parse_applescript_date(date_part)
                
                location = parts[2].strip() if len(parts) > 2 else ""
                all_day_str = parts[3].strip().lower() if len(parts) > 3 else "false"
                all_day = all_day_str == "true"
                calendar_name = parts[4].strip() if len(parts) > 4 else ""
                
                events.append(CalendarEvent(
                    id=f"{title}_{start_time.isoformat()}",
                    title=title,
                    start_time=start_time,
                    end_time=start_time + timedelta(hours=1),
                    calendar_name=calendar_name,
                    location=location,
                    all_day=all_day,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse event '{parts[0] if parts else 'unknown'}': {e}")
        
        # Sort by start time
        events.sort(key=lambda e: e.start_time)
        
        logger.info(f"Apple Calendar found {len(events)} events for range {start_str} to {end_str}")
        for evt in events[:5]:
            logger.debug(f"  - {evt.start_time.strftime('%m/%d %H:%M')} {evt.title}")
        
        return events
    
    def _parse_applescript_date(self, date_str: str) -> datetime:
        """Parse AppleScript date string."""
        import re
        
        date_str = date_str.strip()
        
        # Try Chinese format first: "2026年2月1日 星期日 凌晨12:00:00"
        chinese_match = re.match(
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(?:星期.?)?\s*(凌晨|上午|中午|下午|晚上)?(\d{1,2}):(\d{2}):?(\d{2})?',
            date_str
        )
        if chinese_match:
            year = int(chinese_match.group(1))
            month = int(chinese_match.group(2))
            day = int(chinese_match.group(3))
            period = chinese_match.group(4) or ""
            hour = int(chinese_match.group(5))
            minute = int(chinese_match.group(6))
            second = int(chinese_match.group(7)) if chinese_match.group(7) else 0
            
            # Adjust hour based on Chinese time period
            if period in ("下午", "晚上") and hour < 12:
                hour += 12
            elif period == "凌晨" and hour == 12:
                hour = 0
            elif period == "上午" and hour == 12:
                hour = 0
            
            try:
                return datetime(year, month, day, hour, minute, second)
            except ValueError:
                pass
        
        # Try English formats
        formats = [
            "%A, %B %d, %Y at %I:%M:%S %p",
            "%A, %B %d, %Y %I:%M:%S %p",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %I:%M:%S %p",
            "%d/%m/%Y %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try to extract just date if time parsing fails
        date_only_match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if date_only_match:
            try:
                return datetime(
                    int(date_only_match.group(1)),
                    int(date_only_match.group(2)),
                    int(date_only_match.group(3)),
                    0, 0, 0
                )
            except ValueError:
                pass
        
        # Fallback: try to extract date components
        logger.warning(f"Could not parse date: {date_str}, using now")
        return datetime.now()
    
    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        calendar_name: str = "",
        location: str = "",
        notes: str = "",
        all_day: bool = False,
    ) -> Optional[str]:
        """
        Create a new calendar event.
        
        Returns event ID if successful, None otherwise.
        """
        if not self.is_available():
            return None
        
        # Use default calendar if not specified
        if not calendar_name:
            calendars = self.list_calendars()
            if calendars:
                calendar_name = calendars[0].name
            else:
                logger.error("No calendars available")
                return None
        
        # Format dates for AppleScript
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Escape special characters
        title_escaped = title.replace('"', '\\"')
        location_escaped = location.replace('"', '\\"')
        notes_escaped = notes.replace('"', '\\"')
        
        script = f'''
        tell application "Calendar"
            tell calendar "{calendar_name}"
                set newEvent to make new event with properties {{summary:"{title_escaped}", start date:date "{start_str}", end date:date "{end_str}"}}
                
                if "{location_escaped}" is not "" then
                    set location of newEvent to "{location_escaped}"
                end if
                
                if "{notes_escaped}" is not "" then
                    set description of newEvent to "{notes_escaped}"
                end if
                
                set allday event of newEvent to {str(all_day).lower()}
                
                return uid of newEvent
            end tell
        end tell
        '''
        
        result = self._run_applescript(script)
        if result:
            logger.info(f"Created calendar event: {title}")
            return result
        
        return None
    
    def delete_event(self, event_id: str, calendar_name: str) -> bool:
        """Delete a calendar event."""
        if not self.is_available():
            return False
        
        script = f'''
        tell application "Calendar"
            tell calendar "{calendar_name}"
                set targetEvent to first event whose uid is "{event_id}"
                delete targetEvent
            end tell
        end tell
        '''
        
        result = self._run_applescript(script)
        if result is not None:
            logger.info(f"Deleted calendar event: {event_id}")
            return True
        
        return False
    
    def format_events_display(
        self,
        events: list[CalendarEvent],
        title: str = "行程",
    ) -> str:
        """Format events for display."""
        if not events:
            return f"📅 {title}\n\n沒有行程"
        
        lines = [f"📅 {title}\n"]
        
        # Group by date
        current_date = None
        for event in events:
            event_date = event.start_time.date()
            
            if event_date != current_date:
                current_date = event_date
                date_str = event.start_time.strftime("%m/%d (%a)")
                lines.append(f"\n**{date_str}**")
            
            lines.append(event.format_display())
        
        return "\n".join(lines)


# Singleton instance
_calendar_manager: Optional[AppleCalendarManager] = None


def get_apple_calendar() -> AppleCalendarManager:
    """Get Apple Calendar manager singleton."""
    global _calendar_manager
    if _calendar_manager is None:
        _calendar_manager = AppleCalendarManager()
    return _calendar_manager


def reset_apple_calendar() -> None:
    """Reset Apple Calendar manager (for testing)."""
    global _calendar_manager
    _calendar_manager = None


def clear_calendar_cache() -> None:
    """Clear the calendar events cache."""
    manager = get_apple_calendar()
    manager._events_cache.clear()
    manager._calendars_cache = None
    logger.debug("Calendar cache cleared")


# ============================================
# Command Handlers
# ============================================

async def handle_calendar_command(args: list[str], user_id: str) -> str:
    """
    Handle /calendar command.
    
    Usage:
        /calendar - Show today's events
        /calendar week - Show this week's events
        /calendar list - List calendars
        /calendar add <title> <start> <end> - Add event
    """
    calendar = get_apple_calendar()
    
    if not calendar.is_available():
        return "❌ Apple Calendar 僅在 macOS 上可用"
    
    if not args:
        # Show today's events
        events = calendar.get_events_today()
        return calendar.format_events_display(events, "今日行程")
    
    subcommand = args[0].lower()
    
    if subcommand == "week":
        events = calendar.get_events_week()
        return calendar.format_events_display(events, "本週行程")
    
    elif subcommand == "list":
        calendars = calendar.list_calendars()
        if not calendars:
            return "📅 沒有找到日曆"
        
        lines = ["📅 **可用日曆**\n"]
        for cal in calendars:
            lines.append(f"• {cal.name}")
        return "\n".join(lines)
    
    elif subcommand == "add":
        if len(args) < 4:
            return "❌ 用法: /calendar add <標題> <開始時間> <結束時間>\n例如: /calendar add 開會 2026-01-28T10:00 2026-01-28T11:00"
        
        title = args[1]
        try:
            start = datetime.fromisoformat(args[2])
            end = datetime.fromisoformat(args[3])
        except ValueError:
            return "❌ 時間格式錯誤，請使用 ISO 格式 (YYYY-MM-DDTHH:MM)"
        
        event_id = calendar.create_event(
            title=title,
            start_time=start,
            end_time=end,
        )
        
        if event_id:
            return f"✅ 已建立行程: {title}"
        else:
            return "❌ 建立行程失敗"
    
    elif subcommand == "help":
        return """📅 **Apple Calendar 指令說明**

/calendar - 顯示今日行程
/calendar week - 顯示本週行程
/calendar list - 列出所有日曆
/calendar add <標題> <開始> <結束> - 新增行程

**時間格式**: YYYY-MM-DDTHH:MM
例如: 2026-01-28T10:00

**注意**: 僅在 macOS 上可用
"""
    
    else:
        return f"❌ 未知子指令: {subcommand}\n使用 /calendar help 查看說明"
