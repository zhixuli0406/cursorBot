"""
Personal Secretary for CursorBot v1.1

Provides a personalized secretary experience with:
- Daily briefing and reminders
- Calendar management
- Task tracking
- Booking assistance (flights, trains, hotels)
- Personalized responses with secretary persona

Usage:
    from src.core.secretary import get_secretary
    
    secretary = get_secretary()
    response = await secretary.daily_briefing(user_id)
"""

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from ..utils.logger import logger
from ..utils.config import settings


class SecretaryMood(Enum):
    """Secretary mood/tone."""
    CHEERFUL = "cheerful"      # 開朗
    PROFESSIONAL = "professional"  # 專業
    CARING = "caring"          # 關心
    ENERGETIC = "energetic"    # 活力


class TaskPriority(Enum):
    """Task priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    """A task/to-do item."""
    id: str
    title: str
    description: str = ""
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    reminder_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority.value,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "reminder_time": self.reminder_time.isoformat() if self.reminder_time else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=TaskPriority(data.get("priority", "medium")),
            completed=data.get("completed", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            reminder_time=datetime.fromisoformat(data["reminder_time"]) if data.get("reminder_time") else None,
        )


@dataclass
class UserPreferences:
    """User's secretary preferences."""
    user_id: str
    name: str = ""  # User's preferred name
    wake_time: time = field(default_factory=lambda: time(7, 0))
    briefing_enabled: bool = True
    secretary_name: str = "小雅"  # Secretary's name
    language: str = "zh-TW"
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "wake_time": self.wake_time.strftime("%H:%M"),
            "briefing_enabled": self.briefing_enabled,
            "secretary_name": self.secretary_name,
            "language": self.language,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        wake_time_str = data.get("wake_time", "07:00")
        hour, minute = map(int, wake_time_str.split(":"))
        return cls(
            user_id=data["user_id"],
            name=data.get("name", ""),
            wake_time=time(hour, minute),
            briefing_enabled=data.get("briefing_enabled", True),
            secretary_name=data.get("secretary_name", "小雅"),
            language=data.get("language", "zh-TW"),
        )


class SecretaryPersona:
    """
    Secretary persona for generating personalized responses.
    """
    
    # Greetings by time of day
    GREETINGS = {
        "morning": [
            "早安～{name}！新的一天開始了呢 ☀️",
            "早安！{name}，今天也要元氣滿滿喔～",
            "{name}早安！我已經幫您整理好今天的行程了 📋",
            "早上好～{name}！希望您昨晚睡得好 💤",
        ],
        "afternoon": [
            "{name}下午好！工作順利嗎？",
            "午安～{name}！記得喝杯水休息一下喔 ☕",
            "{name}，下午了呢！有什麼需要我幫忙的嗎？",
        ],
        "evening": [
            "{name}晚上好！辛苦了一天～",
            "晚安～{name}！今天過得怎麼樣呢？",
            "{name}，已經晚上了呢，別太累囉！",
        ],
        "night": [
            "{name}，已經很晚了呢，早點休息吧 🌙",
            "夜深了～{name}要注意身體喔！",
            "{name}還沒睡嗎？記得早點休息～",
        ],
    }
    
    # Task reminders
    TASK_REMINDERS = [
        "提醒您，今天有 {count} 件待辦事項要處理喔！",
        "別忘了今天還有 {count} 件事情等著您～",
        "今天的待辦清單有 {count} 項，一起加油吧！",
    ]
    
    # No tasks
    NO_TASKS = [
        "今天沒有待辦事項呢，可以放鬆一下～",
        "待辦清單是空的！有什麼新任務要交給我嗎？",
        "今天暫時沒有特別要做的事情喔～",
    ]
    
    # Calendar reminders
    CALENDAR_REMINDERS = [
        "今天有 {count} 個行程安排，我幫您整理如下：",
        "您今天有 {count} 個約會/會議喔：",
        "提醒您今天的 {count} 個行程：",
    ]
    
    # No events
    NO_EVENTS = [
        "今天沒有安排任何行程呢～",
        "行事曆上今天是空白的，有要安排什麼嗎？",
        "今天沒有會議或約會～",
    ]
    
    # Confirmations
    CONFIRMATIONS = [
        "好的，我知道了！✨",
        "收到～我馬上處理！",
        "沒問題，交給我吧！💪",
        "好的，已經幫您記下了！📝",
    ]
    
    # Booking assistance
    BOOKING_HELP = [
        "好的！請告訴我出發地、目的地和日期，我來幫您查詢～",
        "沒問題！請問您要訂什麼時候的票呢？",
        "收到～麻煩告訴我詳細資訊，我來協助您！",
    ]
    
    # Care messages
    CARE_MESSAGES = [
        "記得多喝水喔～ 💧",
        "工作之餘也要注意休息呢！",
        "天氣變化大，記得添衣保暖～",
        "午餐吃了嗎？要好好吃飯喔！",
        "眼睛累了就休息一下吧～",
    ]
    
    # Sign off
    SIGN_OFFS = [
        "有任何需要隨時叫我～",
        "需要幫忙的話記得找我喔！",
        "我會一直在這裡的～",
        "祝您今天順利！✨",
    ]
    
    @classmethod
    def get_time_period(cls) -> str:
        """Get current time period."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    @classmethod
    def greeting(cls, name: str = "") -> str:
        """Get a greeting based on time of day."""
        period = cls.get_time_period()
        template = random.choice(cls.GREETINGS[period])
        return template.format(name=name or "主人")
    
    @classmethod
    def task_reminder(cls, count: int) -> str:
        """Get task reminder message."""
        if count == 0:
            return random.choice(cls.NO_TASKS)
        return random.choice(cls.TASK_REMINDERS).format(count=count)
    
    @classmethod
    def calendar_reminder(cls, count: int) -> str:
        """Get calendar reminder message."""
        if count == 0:
            return random.choice(cls.NO_EVENTS)
        return random.choice(cls.CALENDAR_REMINDERS).format(count=count)
    
    @classmethod
    def confirmation(cls) -> str:
        """Get confirmation message."""
        return random.choice(cls.CONFIRMATIONS)
    
    @classmethod
    def booking_help(cls) -> str:
        """Get booking help message."""
        return random.choice(cls.BOOKING_HELP)
    
    @classmethod
    def care_message(cls) -> str:
        """Get a caring message."""
        return random.choice(cls.CARE_MESSAGES)
    
    @classmethod
    def sign_off(cls) -> str:
        """Get sign off message."""
        return random.choice(cls.SIGN_OFFS)


class PersonalSecretary:
    """
    Personal secretary that manages tasks, calendar, and provides
    personalized assistance.
    """
    
    def __init__(self):
        self._tasks: dict[str, list[Task]] = {}  # user_id -> tasks
        self._preferences: dict[str, UserPreferences] = {}
        self._data_dir = Path("data/secretary")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load_data()
    
    def _load_data(self) -> None:
        """Load saved data."""
        # Load tasks
        tasks_file = self._data_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, tasks_data in data.items():
                        self._tasks[user_id] = [Task.from_dict(t) for t in tasks_data]
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
        
        # Load preferences
        prefs_file = self._data_dir / "preferences.json"
        if prefs_file.exists():
            try:
                with open(prefs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, pref_data in data.items():
                        self._preferences[user_id] = UserPreferences.from_dict(pref_data)
            except Exception as e:
                logger.error(f"Failed to load preferences: {e}")
    
    def _save_data(self) -> None:
        """Save data to files."""
        # Save tasks
        tasks_file = self._data_dir / "tasks.json"
        try:
            with open(tasks_file, "w", encoding="utf-8") as f:
                data = {uid: [t.to_dict() for t in tasks] for uid, tasks in self._tasks.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
        
        # Save preferences
        prefs_file = self._data_dir / "preferences.json"
        try:
            with open(prefs_file, "w", encoding="utf-8") as f:
                data = {uid: pref.to_dict() for uid, pref in self._preferences.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
    
    def get_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences."""
        if user_id not in self._preferences:
            self._preferences[user_id] = UserPreferences(user_id=user_id)
        return self._preferences[user_id]
    
    def set_user_name(self, user_id: str, name: str) -> None:
        """Set user's preferred name."""
        prefs = self.get_preferences(user_id)
        prefs.name = name
        self._save_data()
    
    def set_secretary_name(self, user_id: str, name: str) -> None:
        """Set secretary's name for user."""
        prefs = self.get_preferences(user_id)
        prefs.secretary_name = name
        self._save_data()
    
    # ============================================
    # Task Management
    # ============================================
    
    def add_task(
        self,
        user_id: str,
        title: str,
        description: str = "",
        due_date: Optional[datetime] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Task:
        """Add a new task."""
        import uuid
        
        task = Task(
            id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
        )
        
        if user_id not in self._tasks:
            self._tasks[user_id] = []
        
        self._tasks[user_id].append(task)
        self._save_data()
        
        return task
    
    def get_tasks(self, user_id: str, include_completed: bool = False) -> list[Task]:
        """Get user's tasks."""
        tasks = self._tasks.get(user_id, [])
        if not include_completed:
            tasks = [t for t in tasks if not t.completed]
        return sorted(tasks, key=lambda t: (t.priority.value, t.due_date or datetime.max))
    
    def get_today_tasks(self, user_id: str) -> list[Task]:
        """Get tasks due today."""
        today = datetime.now().date()
        tasks = self.get_tasks(user_id)
        return [t for t in tasks if t.due_date and t.due_date.date() == today]
    
    def complete_task(self, user_id: str, task_id: str) -> bool:
        """Mark a task as completed."""
        tasks = self._tasks.get(user_id, [])
        for task in tasks:
            if task.id == task_id:
                task.completed = True
                self._save_data()
                return True
        return False
    
    def delete_task(self, user_id: str, task_id: str) -> bool:
        """Delete a task."""
        if user_id not in self._tasks:
            return False
        
        original_len = len(self._tasks[user_id])
        self._tasks[user_id] = [t for t in self._tasks[user_id] if t.id != task_id]
        
        if len(self._tasks[user_id]) < original_len:
            self._save_data()
            return True
        return False
    
    # ============================================
    # Daily Briefing
    # ============================================
    
    async def daily_briefing(self, user_id: str) -> str:
        """Generate daily briefing for user."""
        prefs = self.get_preferences(user_id)
        persona = SecretaryPersona
        
        lines = []
        
        # Greeting
        lines.append(persona.greeting(prefs.name))
        lines.append("")
        
        # Today's date
        now = datetime.now()
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        date_str = f"📅 今天是 {now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]}"
        lines.append(date_str)
        lines.append("")
        
        # Calendar events
        events = await self._get_calendar_events(user_id)
        lines.append(f"📋 {persona.calendar_reminder(len(events))}")
        if events:
            for event in events[:5]:  # Show max 5 events
                time_str = event.get("time", "")
                title = event.get("title", "")
                location = event.get("location", "")
                line = f"  • {time_str} - {title}"
                if location:
                    line += f" 📍{location}"
                lines.append(line)
        lines.append("")
        
        # Tasks
        tasks = self.get_today_tasks(user_id)
        all_tasks = self.get_tasks(user_id)
        lines.append(f"✅ {persona.task_reminder(len(all_tasks))}")
        if tasks:
            lines.append("今天到期的任務：")
            for task in tasks[:5]:
                priority_icon = "🔴" if task.priority == TaskPriority.HIGH else "🟡" if task.priority == TaskPriority.MEDIUM else "🟢"
                lines.append(f"  {priority_icon} {task.title}")
        lines.append("")
        
        # Care message (randomly)
        if random.random() < 0.5:
            lines.append(f"💕 {persona.care_message()}")
            lines.append("")
        
        # Sign off
        lines.append(f"—— {prefs.secretary_name} {persona.sign_off()}")
        
        return "\n".join(lines)
    
    async def _get_calendar_events(self, user_id: str) -> list[dict]:
        """Get today's calendar events."""
        events = []
        
        # Try Apple Calendar
        try:
            import platform
            if platform.system() == "Darwin":
                from .apple_calendar import get_apple_calendar
                apple_cal = get_apple_calendar()
                if apple_cal.is_available():
                    apple_events = apple_cal.get_events_today()
                    for event in apple_events:
                        time_str = event.start_time.strftime("%H:%M") if event.start_time else "整天"
                        events.append({
                            "time": time_str,
                            "title": event.title,
                            "location": event.location,
                        })
        except Exception as e:
            logger.debug(f"Apple Calendar not available: {e}")
        
        # Try Google Calendar
        try:
            from .google_calendar import get_calendar_manager, GOOGLE_API_AVAILABLE
            if GOOGLE_API_AVAILABLE:
                google_cal = get_calendar_manager()
                if google_cal.is_authenticated:
                    google_events = await google_cal.get_events_today()
                    for event in google_events:
                        time_str = event.start.strftime("%H:%M") if event.start else "整天"
                        events.append({
                            "time": time_str,
                            "title": event.title,
                            "location": event.location or "",
                        })
        except Exception as e:
            logger.debug(f"Google Calendar not available: {e}")
        
        # Sort by time
        events.sort(key=lambda e: e["time"])
        return events
    
    # ============================================
    # Response Generation
    # ============================================
    
    def format_response(self, user_id: str, content: str, include_sign_off: bool = True) -> str:
        """Format a response with secretary persona."""
        prefs = self.get_preferences(user_id)
        persona = SecretaryPersona
        
        lines = [content]
        
        if include_sign_off:
            lines.append("")
            lines.append(f"—— {prefs.secretary_name}")
        
        return "\n".join(lines)
    
    def task_added_response(self, user_id: str, task: Task) -> str:
        """Response for task added."""
        prefs = self.get_preferences(user_id)
        persona = SecretaryPersona
        
        lines = [
            persona.confirmation(),
            "",
            f"📝 已新增待辦事項：",
            f"  標題：{task.title}",
        ]
        
        if task.due_date:
            lines.append(f"  到期：{task.due_date.strftime('%Y/%m/%d %H:%M')}")
        
        priority_text = {"high": "高", "medium": "中", "low": "低"}
        lines.append(f"  優先級：{priority_text.get(task.priority.value, '中')}")
        
        lines.append("")
        lines.append(f"—— {prefs.secretary_name}")
        
        return "\n".join(lines)
    
    def task_list_response(self, user_id: str) -> str:
        """Response for task list."""
        prefs = self.get_preferences(user_id)
        tasks = self.get_tasks(user_id)
        
        if not tasks:
            return self.format_response(
                user_id,
                f"{prefs.name or '主人'}，目前沒有待辦事項呢～\n有什麼任務要交給我嗎？"
            )
        
        lines = [f"📋 {prefs.name or '主人'}的待辦清單：", ""]
        
        for i, task in enumerate(tasks[:10], 1):
            priority_icon = "🔴" if task.priority == TaskPriority.HIGH else "🟡" if task.priority == TaskPriority.MEDIUM else "🟢"
            status = "✅" if task.completed else "⬜"
            line = f"{i}. {status} {priority_icon} {task.title}"
            if task.due_date:
                line += f" (到期: {task.due_date.strftime('%m/%d')})"
            lines.append(line)
        
        if len(tasks) > 10:
            lines.append(f"... 還有 {len(tasks) - 10} 項")
        
        lines.append("")
        lines.append(f"共 {len(tasks)} 項待辦")
        
        return self.format_response(user_id, "\n".join(lines))
    
    def booking_response(self, user_id: str, booking_type: str) -> str:
        """Response for booking request."""
        prefs = self.get_preferences(user_id)
        persona = SecretaryPersona
        
        type_names = {
            "flight": "機票",
            "train": "火車票",
            "hotel": "飯店",
            "restaurant": "餐廳",
        }
        type_name = type_names.get(booking_type, "票務")
        
        lines = [
            persona.booking_help(),
            "",
            f"🎫 {type_name}預訂協助",
            "",
            "請提供以下資訊：",
        ]
        
        if booking_type == "flight":
            lines.extend([
                "  ✈️ 出發地：",
                "  ✈️ 目的地：",
                "  📅 出發日期：",
                "  📅 回程日期（如有）：",
                "  👥 人數：",
                "  💺 艙等偏好：",
            ])
        elif booking_type == "train":
            lines.extend([
                "  🚄 出發站：",
                "  🚄 到達站：",
                "  📅 日期：",
                "  ⏰ 偏好時段：",
                "  👥 人數：",
            ])
        elif booking_type == "hotel":
            lines.extend([
                "  📍 目的地/地區：",
                "  📅 入住日期：",
                "  📅 退房日期：",
                "  👥 人數/房數：",
                "  💰 預算範圍：",
            ])
        
        lines.append("")
        lines.append(f"—— {prefs.secretary_name}")
        
        return "\n".join(lines)
    
    def calendar_add_response(self, user_id: str, event_title: str, event_time: str) -> str:
        """Response for calendar event added."""
        prefs = self.get_preferences(user_id)
        persona = SecretaryPersona
        
        lines = [
            persona.confirmation(),
            "",
            f"📅 已新增行程：",
            f"  標題：{event_title}",
            f"  時間：{event_time}",
            "",
            "需要設定提醒嗎？",
            "",
            f"—— {prefs.secretary_name}",
        ]
        
        return "\n".join(lines)


# ============================================
# Natural Language Understanding
# ============================================

class AssistantIntent(Enum):
    """Intent types for assistant mode."""
    GREETING = "greeting"              # 打招呼
    ADD_TASK = "add_task"              # 新增待辦
    LIST_TASKS = "list_tasks"          # 查看待辦
    COMPLETE_TASK = "complete_task"    # 完成待辦
    SHOW_CALENDAR = "show_calendar"    # 查看行程
    ADD_EVENT = "add_event"            # 新增行程
    BOOK_TICKET = "book_ticket"        # 訂票
    BOOK_HOTEL = "book_hotel"          # 訂飯店
    DAILY_BRIEFING = "daily_briefing"  # 每日簡報
    REMINDER = "reminder"              # 設定提醒
    WEATHER = "weather"                # 查天氣
    CHAT = "chat"                      # 一般聊天
    HELP = "help"                      # 求助
    UNKNOWN = "unknown"                # 無法辨識


@dataclass
class IntentResult:
    """Result of intent recognition."""
    intent: AssistantIntent
    confidence: float
    entities: dict = field(default_factory=dict)
    original_text: str = ""


class AssistantNLU:
    """
    Natural Language Understanding for Assistant Mode.
    Recognizes user intents from natural language.
    """
    
    # Intent patterns (keyword-based for now, can be upgraded to ML)
    INTENT_PATTERNS = {
        AssistantIntent.GREETING: [
            "你好", "嗨", "早安", "午安", "晚安", "哈囉", "hi", "hello",
            "在嗎", "在不在", "hey",
        ],
        AssistantIntent.ADD_TASK: [
            "幫我記", "新增待辦", "加一個任務", "待辦", "要做", "記一下",
            "幫我加", "提醒我", "別忘了", "記得",
        ],
        AssistantIntent.LIST_TASKS: [
            "有什麼事", "待辦清單", "要做什麼", "有哪些任務", "列出待辦",
            "今天要做", "還有什麼", "任務列表",
        ],
        AssistantIntent.COMPLETE_TASK: [
            "完成了", "做完了", "搞定", "ok了", "好了", "done",
            "已完成", "弄好了",
        ],
        AssistantIntent.SHOW_CALENDAR: [
            "行程", "日曆", "今天有什麼", "有約嗎", "有會嗎", "有會議",
            "有安排", "schedule", "calendar", "這週", "本週",
        ],
        AssistantIntent.ADD_EVENT: [
            "排個", "安排", "約", "預約", "新增行程", "加行程",
            "幫我排", "訂個時間",
        ],
        AssistantIntent.BOOK_TICKET: [
            "訂票", "買票", "機票", "火車票", "高鐵", "車票",
            "飛機", "訂機票", "訂火車",
        ],
        AssistantIntent.BOOK_HOTEL: [
            "訂房", "飯店", "酒店", "住宿", "旅館", "民宿",
            "訂飯店", "找住的",
        ],
        AssistantIntent.DAILY_BRIEFING: [
            "簡報", "今天", "報告", "briefing", "概況",
            "今天怎樣", "今日",
        ],
        AssistantIntent.REMINDER: [
            "提醒", "叫我", "通知我", "記得提醒", "鬧鐘",
            "點叫我", "點提醒",
        ],
        AssistantIntent.WEATHER: [
            "天氣", "下雨", "氣溫", "穿什麼", "會不會下雨",
            "熱嗎", "冷嗎",
        ],
        AssistantIntent.HELP: [
            "怎麼用", "可以做什麼", "功能", "幫助", "help",
            "能幫我什麼", "你會什麼",
        ],
    }
    
    # Entity extraction patterns
    TIME_PATTERNS = [
        r"(\d{1,2})點", r"(\d{1,2}):(\d{2})", r"(\d{1,2})時",
        r"(早上|上午|中午|下午|晚上)(\d{1,2})點?",
    ]
    
    DATE_PATTERNS = [
        r"今天", r"明天", r"後天", r"下週[一二三四五六日]",
        r"(\d{1,2})[/月](\d{1,2})[日號]?",
    ]
    
    LOCATION_PATTERNS = [
        r"(台北|台中|高雄|台南|新北|桃園)",
        r"(東京|大阪|首爾|香港|新加坡|曼谷)",
        r"到([\u4e00-\u9fa5]{2,})",
        r"從([\u4e00-\u9fa5]{2,})",
    ]
    
    @classmethod
    def recognize_intent(cls, text: str) -> IntentResult:
        """Recognize intent from user text."""
        text_lower = text.lower().strip()
        
        best_intent = AssistantIntent.UNKNOWN
        best_confidence = 0.0
        entities = {}
        
        # Check each intent pattern
        for intent, patterns in cls.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    # Calculate confidence based on pattern match
                    confidence = len(pattern) / len(text_lower) * 0.8 + 0.2
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent
        
        # Extract entities based on intent
        if best_intent == AssistantIntent.ADD_TASK:
            # Extract task title
            import re
            # Remove common prefixes
            task_text = text
            for prefix in ["幫我記", "新增待辦", "加一個任務", "幫我加", "提醒我", "記一下", "別忘了", "記得"]:
                task_text = task_text.replace(prefix, "").strip()
            if task_text:
                entities["task_title"] = task_text
        
        elif best_intent == AssistantIntent.BOOK_TICKET:
            import re
            # Extract locations
            for pattern in cls.LOCATION_PATTERNS:
                matches = re.findall(pattern, text)
                if matches:
                    if "destination" not in entities:
                        entities["destination"] = matches[0] if isinstance(matches[0], str) else matches[0][0]
            
            # Extract ticket type
            if any(k in text for k in ["機票", "飛機"]):
                entities["ticket_type"] = "flight"
            elif any(k in text for k in ["高鐵", "火車", "車票"]):
                entities["ticket_type"] = "train"
        
        elif best_intent == AssistantIntent.COMPLETE_TASK:
            import re
            # Extract task number
            match = re.search(r"第?(\d+)", text)
            if match:
                entities["task_number"] = int(match.group(1))
        
        # If no clear intent, default to chat
        if best_intent == AssistantIntent.UNKNOWN and len(text) > 2:
            best_intent = AssistantIntent.CHAT
            best_confidence = 0.5
        
        return IntentResult(
            intent=best_intent,
            confidence=best_confidence,
            entities=entities,
            original_text=text,
        )


class AssistantMode:
    """
    Assistant Mode handler for natural conversation.
    """
    
    def __init__(self, secretary: "PersonalSecretary"):
        self.secretary = secretary
        self.nlu = AssistantNLU()
    
    async def process_message(self, user_id: str, text: str) -> str:
        """Process a message in assistant mode."""
        prefs = self.secretary.get_preferences(user_id)
        
        # Recognize intent
        result = self.nlu.recognize_intent(text)
        
        # Handle based on intent
        handlers = {
            AssistantIntent.GREETING: self._handle_greeting,
            AssistantIntent.ADD_TASK: self._handle_add_task,
            AssistantIntent.LIST_TASKS: self._handle_list_tasks,
            AssistantIntent.COMPLETE_TASK: self._handle_complete_task,
            AssistantIntent.SHOW_CALENDAR: self._handle_show_calendar,
            AssistantIntent.DAILY_BRIEFING: self._handle_briefing,
            AssistantIntent.BOOK_TICKET: self._handle_book_ticket,
            AssistantIntent.BOOK_HOTEL: self._handle_book_hotel,
            AssistantIntent.HELP: self._handle_help,
            AssistantIntent.CHAT: self._handle_chat,
        }
        
        handler = handlers.get(result.intent, self._handle_unknown)
        response = await handler(user_id, result)
        
        return response
    
    async def _handle_greeting(self, user_id: str, result: IntentResult) -> str:
        """Handle greeting."""
        prefs = self.secretary.get_preferences(user_id)
        persona = SecretaryPersona
        
        greeting = persona.greeting(prefs.name)
        responses = [
            f"{greeting}\n\n有什麼我可以幫您的嗎？",
            f"{greeting}\n\n今天想做什麼呢？",
            f"{greeting}\n\n需要我幫您看看今天的行程嗎？",
        ]
        
        import random
        response = random.choice(responses)
        return f"{response}\n\n—— {prefs.secretary_name}"
    
    async def _handle_add_task(self, user_id: str, result: IntentResult) -> str:
        """Handle add task intent."""
        prefs = self.secretary.get_preferences(user_id)
        
        task_title = result.entities.get("task_title", "")
        if not task_title:
            return f"好的～請問要記什麼事情呢？\n\n—— {prefs.secretary_name}"
        
        task = self.secretary.add_task(user_id, task_title)
        return self.secretary.task_added_response(user_id, task)
    
    async def _handle_list_tasks(self, user_id: str, result: IntentResult) -> str:
        """Handle list tasks intent."""
        return self.secretary.task_list_response(user_id)
    
    async def _handle_complete_task(self, user_id: str, result: IntentResult) -> str:
        """Handle complete task intent."""
        prefs = self.secretary.get_preferences(user_id)
        task_num = result.entities.get("task_number")
        
        if not task_num:
            tasks = self.secretary.get_tasks(user_id)
            if not tasks:
                return f"目前沒有待辦事項呢～\n\n—— {prefs.secretary_name}"
            return f"請問是完成第幾項呢？\n\n{self.secretary.task_list_response(user_id)}"
        
        tasks = self.secretary.get_tasks(user_id)
        if 0 < task_num <= len(tasks):
            task = tasks[task_num - 1]
            if self.secretary.complete_task(user_id, task.id):
                return f"✅ 太棒了！「{task.title}」已完成！\n\n繼續加油喔～💪\n\n—— {prefs.secretary_name}"
        
        return f"找不到第 {task_num} 項任務呢，請確認一下編號～\n\n—— {prefs.secretary_name}"
    
    async def _handle_show_calendar(self, user_id: str, result: IntentResult) -> str:
        """Handle show calendar intent."""
        prefs = self.secretary.get_preferences(user_id)
        events = await self.secretary._get_calendar_events(user_id)
        
        if not events:
            return f"今天沒有安排行程呢～有需要幫您排什麼嗎？\n\n—— {prefs.secretary_name}"
        
        lines = [f"📅 {prefs.name or '主人'}今天的行程：", ""]
        for event in events[:5]:
            time_str = event.get("time", "")
            title = event.get("title", "")
            location = event.get("location", "")
            line = f"  • {time_str} - {title}"
            if location:
                line += f" 📍{location}"
            lines.append(line)
        
        lines.append("")
        lines.append(f"—— {prefs.secretary_name}")
        return "\n".join(lines)
    
    async def _handle_briefing(self, user_id: str, result: IntentResult) -> str:
        """Handle daily briefing intent."""
        return await self.secretary.daily_briefing(user_id)
    
    async def _handle_book_ticket(self, user_id: str, result: IntentResult) -> str:
        """Handle book ticket intent."""
        ticket_type = result.entities.get("ticket_type", "train")
        return self.secretary.booking_response(user_id, ticket_type)
    
    async def _handle_book_hotel(self, user_id: str, result: IntentResult) -> str:
        """Handle book hotel intent."""
        return self.secretary.booking_response(user_id, "hotel")
    
    async def _handle_help(self, user_id: str, result: IntentResult) -> str:
        """Handle help intent."""
        prefs = self.secretary.get_preferences(user_id)
        
        return f"""當然可以！我是您的專屬秘書 {prefs.secretary_name}～

我可以幫您：
📋 **待辦管理** - 「幫我記 XXX」「待辦清單」「第一項完成了」
📅 **行程查詢** - 「今天有什麼行程」「這週有會議嗎」
🎫 **訂票協助** - 「我要訂機票」「幫我訂高鐵」
🏨 **訂房協助** - 「訂飯店」「找住宿」
📊 **每日簡報** - 「今天怎樣」「給我簡報」

您也可以直接跟我聊天喔！

試試說：「幫我記明天要開會」
或是：「今天有什麼事要做」

—— {prefs.secretary_name}，隨時為您服務！💕
"""
    
    async def _handle_chat(self, user_id: str, result: IntentResult) -> str:
        """Handle general chat - use LLM."""
        prefs = self.secretary.get_preferences(user_id)
        
        # Try to use LLM for natural conversation
        try:
            from .llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            # Create secretary persona prompt
            system_prompt = f"""你是一位名叫「{prefs.secretary_name}」的專屬女秘書，說話溫柔親切、體貼細心。
使用繁體中文回覆，語氣要像關心主人的秘書，適時加入可愛的表情符號。
用戶的名字是「{prefs.name or '主人'}」，請適時稱呼他。
回覆要簡潔，不要太長（2-4句話）。
結尾要署名「—— {prefs.secretary_name}」。"""
            
            response = await manager.generate(
                prompt=result.original_text,
                system_prompt=system_prompt,
                user_id=user_id,
            )
            
            if response:
                return response
        except Exception as e:
            logger.debug(f"LLM chat failed: {e}")
        
        # Fallback responses
        import random
        fallbacks = [
            f"收到～有什麼需要我幫忙的嗎？\n\n—— {prefs.secretary_name}",
            f"嗯嗯，我在聽～\n\n—— {prefs.secretary_name}",
            f"好的好的～還有其他事嗎？\n\n—— {prefs.secretary_name}",
        ]
        return random.choice(fallbacks)
    
    async def _handle_unknown(self, user_id: str, result: IntentResult) -> str:
        """Handle unknown intent."""
        prefs = self.secretary.get_preferences(user_id)
        
        return f"""抱歉，我不太確定您的意思呢～

您可以試試：
• 「幫我記 XXX」- 新增待辦
• 「今天有什麼行程」- 查看行程
• 「訂機票」- 訂票協助
• 「今天怎樣」- 每日簡報

或是直接告訴我您需要什麼幫助！

—— {prefs.secretary_name}"""


# Global instance
_secretary: Optional[PersonalSecretary] = None
_assistant_mode: Optional[AssistantMode] = None


def get_secretary() -> PersonalSecretary:
    """Get the global PersonalSecretary instance."""
    global _secretary
    if _secretary is None:
        _secretary = PersonalSecretary()
    return _secretary


def get_assistant_mode() -> AssistantMode:
    """Get the global AssistantMode instance."""
    global _assistant_mode
    if _assistant_mode is None:
        _assistant_mode = AssistantMode(get_secretary())
    return _assistant_mode


__all__ = [
    "PersonalSecretary",
    "SecretaryPersona",
    "Task",
    "TaskPriority",
    "UserPreferences",
    "AssistantIntent",
    "AssistantNLU",
    "AssistantMode",
    "get_secretary",
    "get_assistant_mode",
]
