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
from ..integrations.weather_service import get_weather_service


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


class RecurringType(Enum):
    """Recurring task types."""
    NONE = "none"           # Not recurring
    DAILY = "daily"         # Every day
    WEEKLY = "weekly"       # Every week
    MONTHLY = "monthly"     # Every month
    WEEKDAYS = "weekdays"   # Mon-Fri only


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
    # Recurring task fields
    recurring: RecurringType = RecurringType.NONE
    recurring_time: Optional[time] = None  # Time of day for recurring reminder
    recurring_days: list[int] = field(default_factory=list)  # For weekly: [0=Mon, 6=Sun]
    last_reminded: Optional[datetime] = None  # Track last reminder sent
    
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
            "recurring": self.recurring.value,
            "recurring_time": self.recurring_time.isoformat() if self.recurring_time else None,
            "recurring_days": self.recurring_days,
            "last_reminded": self.last_reminded.isoformat() if self.last_reminded else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        recurring_time = None
        if data.get("recurring_time"):
            try:
                recurring_time = time.fromisoformat(data["recurring_time"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=TaskPriority(data.get("priority", "medium")),
            completed=data.get("completed", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            reminder_time=datetime.fromisoformat(data["reminder_time"]) if data.get("reminder_time") else None,
            recurring=RecurringType(data.get("recurring", "none")),
            recurring_time=recurring_time,
            recurring_days=data.get("recurring_days", []),
            last_reminded=datetime.fromisoformat(data["last_reminded"]) if data.get("last_reminded") else None,
        )
    
    def should_remind_now(self) -> bool:
        """Check if this recurring task should trigger a reminder now."""
        if self.recurring == RecurringType.NONE:
            return False
        if self.completed:
            return False
        if not self.recurring_time:
            return False
        
        now = datetime.now()
        
        # Check if already reminded today
        if self.last_reminded and self.last_reminded.date() == now.date():
            return False
        
        # Check if current time matches (within 1 minute window)
        if now.hour != self.recurring_time.hour or now.minute != self.recurring_time.minute:
            return False
        
        # Check recurring type
        if self.recurring == RecurringType.DAILY:
            return True
        elif self.recurring == RecurringType.WEEKDAYS:
            return now.weekday() < 5  # Mon-Fri = 0-4
        elif self.recurring == RecurringType.WEEKLY:
            return now.weekday() in self.recurring_days if self.recurring_days else True
        elif self.recurring == RecurringType.MONTHLY:
            # Remind on same day of month as created
            return now.day == self.created_at.day
        
        return False


@dataclass
class PersonaTemplate:
    """Template for a secretary persona."""
    id: str                    # Unique identifier
    name: str                  # Display name
    description: str           # Short description
    tone: str                  # Speaking tone/style
    emoji_style: str           # Emoji usage style
    greeting_style: str        # How to greet
    care_level: str            # How caring (low/medium/high)
    formality: str             # Formality level (casual/normal/formal)
    signature: str             # Signature at end of messages
    
    # Custom prompts
    system_prompt_addon: str = ""  # Additional system prompt
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tone": self.tone,
            "emoji_style": self.emoji_style,
            "greeting_style": self.greeting_style,
            "care_level": self.care_level,
            "formality": self.formality,
            "signature": self.signature,
            "system_prompt_addon": self.system_prompt_addon,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PersonaTemplate":
        return cls(**data)


# Pre-defined persona templates
PRESET_PERSONAS: dict[str, PersonaTemplate] = {
    "gentle": PersonaTemplate(
        id="gentle",
        name="小雅",
        description="溫柔體貼的女秘書",
        tone="溫柔親切、體貼細心",
        emoji_style="適度使用可愛表情（✨💕📅✈️）",
        greeting_style="親切問候，關心對方狀態",
        care_level="high",
        formality="casual",
        signature="—— 小雅 💕",
        system_prompt_addon="說話要溫柔體貼，像個貼心的閨蜜一樣關心用戶。",
    ),
    "professional": PersonaTemplate(
        id="professional",
        name="雅琳",
        description="專業幹練的商務秘書",
        tone="專業得體、簡潔有力",
        emoji_style="少量使用專業表情（📋✅📊）",
        greeting_style="禮貌專業，直奔主題",
        care_level="medium",
        formality="formal",
        signature="—— 雅琳",
        system_prompt_addon="說話要專業幹練，像個經驗豐富的商務秘書，高效處理事務。",
    ),
    "cheerful": PersonaTemplate(
        id="cheerful",
        name="小晴",
        description="活潑開朗的元氣秘書",
        tone="活潑開朗、充滿活力",
        emoji_style="豐富使用表情（🎉✨🌟💪🔥）",
        greeting_style="熱情洋溢，充滿能量",
        care_level="high",
        formality="casual",
        signature="—— 小晴 ✨",
        system_prompt_addon="說話要活潑開朗，像個元氣滿滿的小太陽，給用戶帶來正能量！",
    ),
    "cool": PersonaTemplate(
        id="cool",
        name="冰凝",
        description="冷酷高效的執行秘書",
        tone="冷靜理性、一針見血",
        emoji_style="極少使用表情",
        greeting_style="簡潔直接，不廢話",
        care_level="low",
        formality="normal",
        signature="—— 冰凝",
        system_prompt_addon="說話要冷靜理性，不拖泥帶水，直接給出最有效的建議和行動。",
    ),
    "cute": PersonaTemplate(
        id="cute",
        name="萌萌",
        description="可愛軟萌的小助手",
        tone="軟萌可愛、撒嬌賣萌",
        emoji_style="大量使用可愛表情（🥺💕✨🌸😊）",
        greeting_style="撒嬌式問候，軟萌可愛",
        care_level="high",
        formality="casual",
        signature="—— 萌萌 (◕ᴗ◕✿)",
        system_prompt_addon="說話要軟萌可愛，可以適當撒嬌，用可愛的語氣讓用戶開心！偶爾用「～」結尾。",
    ),
    "butler": PersonaTemplate(
        id="butler",
        name="賽巴斯",
        description="優雅紳士的男管家",
        tone="優雅紳士、從容不迫",
        emoji_style="適度使用優雅表情（🎩☕📜）",
        greeting_style="尊敬有禮，稱呼主人",
        care_level="medium",
        formality="formal",
        signature="—— 賽巴斯，您忠實的管家",
        system_prompt_addon="說話要優雅紳士，像個經典的英式管家，用「主人」稱呼用戶，保持從容優雅。",
    ),
}


@dataclass
class UserPreferences:
    """User's secretary preferences."""
    user_id: str
    name: str = ""  # User's preferred name
    wake_time: time = field(default_factory=lambda: time(7, 0))
    briefing_enabled: bool = True
    secretary_name: str = "小雅"  # Secretary's name
    language: str = "zh-TW"
    persona_id: str = "gentle"  # Current persona template ID
    custom_personas: dict = field(default_factory=dict)  # User's custom personas
    
    def get_current_persona(self) -> PersonaTemplate:
        """Get the current active persona."""
        # Check custom personas first
        if self.persona_id in self.custom_personas:
            return PersonaTemplate.from_dict(self.custom_personas[self.persona_id])
        # Then check presets
        if self.persona_id in PRESET_PERSONAS:
            persona = PRESET_PERSONAS[self.persona_id]
            # Override name if user has customized it
            if self.secretary_name != persona.name:
                return PersonaTemplate(
                    id=persona.id,
                    name=self.secretary_name,
                    description=persona.description,
                    tone=persona.tone,
                    emoji_style=persona.emoji_style,
                    greeting_style=persona.greeting_style,
                    care_level=persona.care_level,
                    formality=persona.formality,
                    signature=f"—— {self.secretary_name}",
                    system_prompt_addon=persona.system_prompt_addon,
                )
            return persona
        # Default to gentle
        return PRESET_PERSONAS["gentle"]
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "wake_time": self.wake_time.strftime("%H:%M"),
            "briefing_enabled": self.briefing_enabled,
            "secretary_name": self.secretary_name,
            "language": self.language,
            "persona_id": self.persona_id,
            "custom_personas": self.custom_personas,
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
            persona_id=data.get("persona_id", "gentle"),
            custom_personas=data.get("custom_personas", {}),
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
    # Persona Management
    # ============================================
    
    def get_available_personas(self, user_id: str) -> list[PersonaTemplate]:
        """Get all available personas (preset + custom)."""
        prefs = self.get_preferences(user_id)
        personas = list(PRESET_PERSONAS.values())
        
        # Add custom personas
        for persona_data in prefs.custom_personas.values():
            personas.append(PersonaTemplate.from_dict(persona_data))
        
        return personas
    
    def set_persona(self, user_id: str, persona_id: str) -> bool:
        """Set the active persona for user."""
        prefs = self.get_preferences(user_id)
        
        # Check if persona exists
        if persona_id not in PRESET_PERSONAS and persona_id not in prefs.custom_personas:
            return False
        
        prefs.persona_id = persona_id
        
        # Update secretary name to match persona
        if persona_id in PRESET_PERSONAS:
            prefs.secretary_name = PRESET_PERSONAS[persona_id].name
        elif persona_id in prefs.custom_personas:
            prefs.secretary_name = prefs.custom_personas[persona_id]["name"]
        
        self._save_data()
        return True
    
    def add_custom_persona(
        self,
        user_id: str,
        persona_id: str,
        name: str,
        description: str,
        tone: str,
        emoji_style: str = "適度使用表情",
        greeting_style: str = "親切問候",
        care_level: str = "medium",
        formality: str = "normal",
        signature: str = None,
        system_prompt_addon: str = "",
    ) -> PersonaTemplate:
        """Add a custom persona for user."""
        prefs = self.get_preferences(user_id)
        
        persona = PersonaTemplate(
            id=persona_id,
            name=name,
            description=description,
            tone=tone,
            emoji_style=emoji_style,
            greeting_style=greeting_style,
            care_level=care_level,
            formality=formality,
            signature=signature or f"—— {name}",
            system_prompt_addon=system_prompt_addon,
        )
        
        prefs.custom_personas[persona_id] = persona.to_dict()
        self._save_data()
        
        return persona
    
    def delete_custom_persona(self, user_id: str, persona_id: str) -> bool:
        """Delete a custom persona."""
        prefs = self.get_preferences(user_id)
        
        if persona_id not in prefs.custom_personas:
            return False
        
        del prefs.custom_personas[persona_id]
        
        # If current persona was deleted, switch to default
        if prefs.persona_id == persona_id:
            prefs.persona_id = "gentle"
            prefs.secretary_name = PRESET_PERSONAS["gentle"].name
        
        self._save_data()
        return True
    
    def get_current_persona(self, user_id: str) -> PersonaTemplate:
        """Get the current active persona."""
        prefs = self.get_preferences(user_id)
        return prefs.get_current_persona()
    
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
    
    def add_recurring_task(
        self,
        user_id: str,
        title: str,
        recurring: RecurringType,
        recurring_time: time,
        recurring_days: list[int] = None,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Task:
        """Add a new recurring task. Checks for duplicates first."""
        import uuid
        
        # Check for duplicate recurring task
        existing_tasks = self._tasks.get(user_id, [])
        for existing in existing_tasks:
            if (existing.recurring != RecurringType.NONE and  # Is recurring
                existing.title.lower() == title.lower() and  # Same title
                existing.recurring == recurring and  # Same type
                existing.recurring_time == recurring_time and  # Same time
                not existing.completed):  # Not completed
                logger.info(f"Duplicate recurring task detected, skipping: {title}")
                return existing  # Return existing task instead of creating duplicate
        
        task = Task(
            id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            priority=priority,
            recurring=recurring,
            recurring_time=recurring_time,
            recurring_days=recurring_days or [],
        )
        
        if user_id not in self._tasks:
            self._tasks[user_id] = []
        
        self._tasks[user_id].append(task)
        self._save_data()
        
        logger.info(f"Added recurring task: {title} ({recurring.value} at {recurring_time})")
        return task
    
    def get_recurring_tasks(self, user_id: str) -> list[Task]:
        """Get user's recurring tasks."""
        tasks = self._tasks.get(user_id, [])
        return [t for t in tasks if t.recurring != RecurringType.NONE and not t.completed]
    
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
    
    async def daily_briefing(self, user_id: str, briefing_type: dict = None) -> str:
        """
        Generate daily briefing for user.
        
        Args:
            user_id: User identifier
            briefing_type: Optional dict with 'type', 'name', 'greeting' for time-based briefing
        """
        prefs = self.get_preferences(user_id)
        persona = SecretaryPersona
        
        lines = []
        
        # Determine greeting based on briefing type or current time
        now = datetime.now()
        if briefing_type:
            greeting_word = briefing_type.get("greeting", "您好")
            briefing_name = briefing_type.get("name", "日報")
        else:
            # Determine from current hour
            hour = now.hour
            if 5 <= hour < 12:
                greeting_word = "早安"
                briefing_name = "早報"
            elif 12 <= hour < 18:
                greeting_word = "午安"
                briefing_name = "午報"
            elif 18 <= hour < 24:
                greeting_word = "晚安"
                briefing_name = "晚報"
            else:
                greeting_word = "夜深了"
                briefing_name = "夜報"
        
        # Greeting with time-based message
        name_part = f"{prefs.name}，" if prefs.name else ""
        lines.append(f"📰 **{briefing_name}** | {greeting_word}，{name_part}這是您的{briefing_name}～")
        lines.append("")
        
        # Today's date
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        date_str = f"📅 今天是 {now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]}"
        lines.append(date_str)
        lines.append("")

        # Weather
        try:
            weather_service = get_weather_service()
            weather_data = await weather_service.get_weather()
            if weather_data:
                weather_text = weather_service.format_weather(weather_data)
                lines.append(weather_text)

                # Add weather advice
                weather_advice = weather_service.get_weather_advice(weather_data)
                if weather_advice:
                    lines.append(weather_advice)

                lines.append("")
        except Exception as e:
            logger.debug(f"Failed to fetch weather for briefing: {e}")

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
        
        # Care message (randomly, but not for night briefing)
        show_care = True
        if briefing_type and briefing_type.get("type") == "night":
            show_care = False
        
        if show_care and random.random() < 0.5:
            lines.append(f"💕 {persona.care_message()}")
            lines.append("")
        
        # Sign off
        lines.append(f"—— {prefs.secretary_name} {persona.sign_off()}")
        
        return "\n".join(lines)
    
    async def _get_calendar_events(self, user_id: str, scope: str = "today") -> list[dict]:
        """
        Get calendar events for specified scope.
        
        Args:
            user_id: User identifier
            scope: "today", "week", "next_week", or "month"
        
        Returns:
            List of event dicts with date, time, title, location
        """
        events = []
        
        # Calculate date range based on scope
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if scope == "today":
            start_date = today
            end_date = today + timedelta(days=1)
        elif scope == "week":
            # This week (Monday to Sunday)
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=7)
        elif scope == "next_week":
            # Next week (next Monday to next Sunday)
            days_since_monday = today.weekday()
            next_monday = today + timedelta(days=(7 - days_since_monday))
            start_date = next_monday
            end_date = next_monday + timedelta(days=7)
        elif scope == "month":
            # This month
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1)
        else:
            start_date = today
            end_date = today + timedelta(days=1)
        
        # Try Apple Calendar
        try:
            import platform
            if platform.system() == "Darwin":
                from .apple_calendar import get_apple_calendar
                apple_cal = get_apple_calendar()
                if apple_cal.is_available():
                    apple_events = apple_cal.get_events(start_date, end_date)
                    
                    for event in apple_events:
                        date_str = event.start_time.strftime("%m/%d") if event.start_time else ""
                        weekday = ['一', '二', '三', '四', '五', '六', '日'][event.start_time.weekday()] if event.start_time else ""
                        time_str = event.start_time.strftime("%H:%M") if event.start_time else "整天"
                        events.append({
                            "date": f"{date_str}({weekday})",
                            "time": time_str,
                            "title": event.title,
                            "location": event.location or "",
                            "start": event.start_time,
                        })
        except Exception as e:
            logger.debug(f"Apple Calendar not available: {e}")
        
        # Try Google Calendar
        try:
            from .google_calendar import get_calendar_manager, GOOGLE_API_AVAILABLE
            if GOOGLE_API_AVAILABLE:
                google_cal = get_calendar_manager()
                if google_cal.is_authenticated:
                    google_events = await google_cal.get_events(
                        calendar_id="primary",
                        start_time=start_date,
                        end_time=end_date,
                        max_results=50,
                    )
                    
                    for event in google_events:
                        date_str = event.start.strftime("%m/%d") if event.start else ""
                        weekday = ['一', '二', '三', '四', '五', '六', '日'][event.start.weekday()] if event.start else ""
                        time_str = event.start.strftime("%H:%M") if event.start else "整天"
                        events.append({
                            "date": f"{date_str}({weekday})",
                            "time": time_str,
                            "title": event.title,
                            "location": event.location or "",
                            "start": event.start,
                        })
        except Exception as e:
            logger.debug(f"Google Calendar not available: {e}")
        
        # Sort by start time
        events.sort(key=lambda e: e.get("start") or datetime.min)
        
        # Remove internal start field
        for e in events:
            e.pop("start", None)
        
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
        
        # Check if it's a recurring task
        is_recurring = task.recurring != RecurringType.NONE
        
        if is_recurring:
            recurring_type_names = {
                RecurringType.DAILY: "每日",
                RecurringType.WEEKLY: "每週",
                RecurringType.WEEKDAYS: "平日",
                RecurringType.MONTHLY: "每月",
            }
            type_name = recurring_type_names.get(task.recurring, "")
            time_str = task.recurring_time.strftime("%H:%M") if task.recurring_time else ""
            
            lines = [
                persona.confirmation(),
                "",
                f"🔁 已新增重複提醒：",
                f"  標題：{task.title}",
                f"  頻率：{type_name}",
                f"  時間：{time_str}",
            ]
        else:
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
        
        # Separate recurring and one-time tasks
        recurring_tasks = [t for t in tasks if t.recurring != RecurringType.NONE]
        one_time_tasks = [t for t in tasks if t.recurring == RecurringType.NONE]
        
        lines = [f"📋 {prefs.name or '主人'}的待辦清單：", ""]
        
        # Show one-time tasks first
        if one_time_tasks:
            for i, task in enumerate(one_time_tasks[:8], 1):
                priority_icon = "🔴" if task.priority == TaskPriority.HIGH else "🟡" if task.priority == TaskPriority.MEDIUM else "🟢"
                status = "✅" if task.completed else "⬜"
                line = f"{i}. {status} {priority_icon} {task.title}"
                if task.due_date:
                    line += f" (到期: {task.due_date.strftime('%m/%d')})"
                lines.append(line)
        
        # Show recurring tasks with index for deletion
        if recurring_tasks:
            lines.append("")
            lines.append("🔁 重複提醒：")
            recurring_type_names = {
                RecurringType.DAILY: "每日",
                RecurringType.WEEKLY: "每週",
                RecurringType.WEEKDAYS: "平日",
                RecurringType.MONTHLY: "每月",
            }
            # Start index after one-time tasks
            start_idx = len(one_time_tasks) + 1
            for idx, task in enumerate(recurring_tasks[:5], start_idx):
                type_name = recurring_type_names.get(task.recurring, "")
                time_str = task.recurring_time.strftime("%H:%M") if task.recurring_time else ""
                lines.append(f"  {idx}. {task.title} ({type_name} {time_str}) [ID: {task.id}]")
        
        if len(one_time_tasks) > 8:
            lines.append(f"... 還有 {len(one_time_tasks) - 8} 項一般待辦")
        
        lines.append("")
        lines.append(f"共 {len(one_time_tasks)} 項待辦，{len(recurring_tasks)} 項重複提醒")
        lines.append("")
        lines.append("📝 指令：")
        lines.append("  /todo done <編號> - 完成任務")
        lines.append("  /todo del <編號> - 刪除任務")
        lines.append("  /todo clear - 清除已完成")
        
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
# Web Search Service
# ============================================

class WebSearchService:
    """
    Web search service for assistant mode.
    Reuses WebSearchAgentSkill from skills.py.
    """

    # Keywords that strongly indicate a web search is needed
    SEARCH_TRIGGER_KEYWORDS = [
        "搜尋", "查一下", "幫我查", "查詢", "找一下", "搜一下", "search", "google",
        "什麼是", "是什麼", "怎麼做", "為什麼",
        "最新", "新聞", "現在", "目前",
        "哪裡", "多少錢", "價格", "票價", "時刻表",
        "航班", "班機", "評價", "推薦",
        "匯率", "股價", "股票",
    ]

    # Keywords that do NOT need web search (handled by existing features)
    SKIP_KEYWORDS = [
        "幫我記", "新增待辦", "記一下", "完成了", "做完了",
        "你好", "嗨", "早安", "午安", "晚安",
        "簡報", "怎麼用", "功能", "幫助",
    ]

    def __init__(self):
        self._search_skill = None

    def _get_search_skill(self):
        """Lazy-load WebSearchAgentSkill."""
        if self._search_skill is None:
            from .skills import WebSearchAgentSkill
            self._search_skill = WebSearchAgentSkill()
        return self._search_skill

    def needs_search(self, text: str, intent) -> bool:
        """Determine if the user message needs a web search."""
        text_lower = text.lower().strip()

        # Check for explicit skip keywords first
        if any(kw in text_lower for kw in self.SKIP_KEYWORDS):
            return False

        # Search trigger keywords override intent-based skipping
        if any(kw in text_lower for kw in self.SEARCH_TRIGGER_KEYWORDS):
            return True

        # If it looks like a question, search
        if text.rstrip().endswith("?") or text.rstrip().endswith("？"):
            return True

        # WEATHER / BOOK / SEARCH intents -> search for real-time info
        intent_value = intent.value if hasattr(intent, "value") else str(intent)
        search_intent_values = {"weather", "book_ticket", "book_hotel", "search"}
        if intent_value in search_intent_values:
            return True

        # Skip intents that are already fully handled (only if no trigger keyword matched)
        skip_intent_values = {
            "greeting", "add_task", "list_tasks", "complete_task",
            "show_calendar", "add_event", "daily_briefing", "reminder", "help",
        }
        if intent_value in skip_intent_values:
            return False

        return False

    def build_search_query(self, text: str, intent) -> str:
        """Build an optimized search query from user text."""
        import re
        from datetime import datetime

        intent_value = intent.value if hasattr(intent, "value") else str(intent)
        query = text

        # Remove common conversational prefixes
        prefixes_to_remove = [
            r"^(幫我|請幫我|可以幫我|能不能|可不可以|請問|想問|想請問)",
            r"^(查一下|搜尋|搜一下|找一下|查詢|幫我查)",
            r"^(告訴我|跟我說|讓我知道)",
            r"^(我需要知道|我想知道)",
        ]
        for pattern in prefixes_to_remove:
            query = re.sub(pattern, "", query).strip()

        # Remove filler words that don't help search
        filler_to_remove = [
            r"(現在|目前|當前)",
        ]
        for pattern in filler_to_remove:
            query = re.sub(pattern, "", query).strip()

        # Add context based on intent
        if intent_value == "weather" and "天氣" not in query:
            query = f"{query} 天氣"
        elif intent_value == "book_ticket":
            if "票價" not in query and "時刻" not in query:
                query = f"{query} 票價 時刻表"
        elif intent_value == "book_hotel":
            if "飯店" not in query and "住宿" not in query:
                query = f"{query} 飯店 推薦"

        return query.strip() or text

    async def search(self, query: str, max_results: int = 5) -> str:
        """
        Perform web search and return formatted results for LLM context.
        Returns formatted string, or empty string on failure.
        """
        try:
            skill = self._get_search_skill()
            result = await skill.execute(query=query)

            if "error" in result:
                logger.warning(f"Web search failed: {result['error']}")
                return ""

            results = result.get("results", [])

            # If DuckDuckGo Instant Answer API returns no results, try HTML fallback
            if not results:
                results = await self._fallback_search(query, max_results)

            if not results:
                return ""

            # Log search results for debugging
            for i, item in enumerate(results[:max_results], 1):
                logger.info(f"Search result {i}: {item.get('title', '')[:80]}")

            # Format results for LLM context
            lines = [f"## 網路搜尋結果（查詢：{query}）"]
            for i, item in enumerate(results[:max_results], 1):
                title = item.get("title", "")
                content = item.get("content", "")
                url = item.get("url", "")
                date = item.get("date", "")
                source = item.get("source", "")
                lines.append(f"{i}. **{title}**")
                if date:
                    lines.append(f"   日期: {date}")
                if content:
                    lines.append(f"   {content[:300]}")
                if source:
                    lines.append(f"   來源: {source} ({url})")
                elif url:
                    lines.append(f"   來源: {url}")

            lines.append(
                "\n⚠️ 重要：請嚴格根據以上搜尋結果回答用戶的問題，不要使用你訓練資料中的舊知識。"
                "如果搜尋結果不足以回答，請坦誠說明並建議用戶嘗試更具體的搜尋。"
            )

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return ""

    async def _fallback_search(self, query: str, max_results: int = 5) -> list[dict]:
        """Fallback: use duckduckgo-search text search."""
        try:
            import asyncio
            from ddgs import DDGS

            def _search():
                ddgs = DDGS()
                for region in ("tw-tzh", "us-en"):
                    try:
                        raw = ddgs.text(query, region=region, max_results=max_results)
                        if raw:
                            logger.info(f"Fallback DDGS text (region={region}) returned {len(raw)} results")
                            return raw
                    except Exception as e:
                        logger.warning(f"Fallback DDGS text (region={region}) failed: {e}")
                return []

            raw = await asyncio.to_thread(_search)
            return [
                {
                    "title": item.get("title", ""),
                    "content": item.get("body", ""),
                    "url": item.get("href", ""),
                }
                for item in raw
            ]

        except Exception as e:
            logger.warning(f"Fallback search failed: {e}")
            return []


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
    SEARCH = "search"                  # 網路搜尋
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
        AssistantIntent.SEARCH: [
            "搜尋", "查一下", "幫我查", "查詢", "找一下", "搜一下",
            "search", "google", "查找",
            "什麼是", "是什麼", "怎麼做", "為什麼",
            "最新", "新聞", "現在", "目前",
            "哪裡", "多少錢", "價格", "票價", "時刻表",
            "航班", "班機", "火車時刻", "高鐵時刻",
            "評價", "推薦", "比較",
            "匯率", "股價", "股票",
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
    Uses LLM for intelligent responses with secretary persona.
    Maintains conversation history with RAG for context continuity
    and continuous learning.
    """
    
    # Max conversation history to keep per user (in-memory)
    MAX_HISTORY = 10
    
    def __init__(self, secretary: "PersonalSecretary"):
        self.secretary = secretary
        self.nlu = AssistantNLU()
        self.web_search = WebSearchService()
        # In-memory conversation history (backup)
        self._conversation_history: dict[str, list[dict]] = {}
        # RAG instance (lazy loaded)
        self._rag = None
        self._rag_enabled = True
    
    async def _get_rag(self):
        """Lazy load ConversationRAG."""
        if self._rag is None and self._rag_enabled:
            try:
                from .conversation_rag import get_conversation_rag
                self._rag = get_conversation_rag()
                await self._rag.initialize()
                logger.info("ConversationRAG initialized for AssistantMode")
            except Exception as e:
                logger.warning(f"Failed to initialize ConversationRAG: {e}")
                self._rag_enabled = False
        return self._rag
    
    def _get_history(self, user_id: str) -> list[dict]:
        """Get conversation history for user (in-memory)."""
        if user_id not in self._conversation_history:
            self._conversation_history[user_id] = []
        return self._conversation_history[user_id]
    
    def _add_to_history(self, user_id: str, role: str, content: str) -> None:
        """Add message to in-memory conversation history."""
        history = self._get_history(user_id)
        history.append({"role": role, "content": content})
        
        # Keep only last MAX_HISTORY messages
        if len(history) > self.MAX_HISTORY * 2:  # *2 for user+assistant pairs
            self._conversation_history[user_id] = history[-self.MAX_HISTORY * 2:]
    
    async def _store_to_rag(self, user_id: str, role: str, content: str) -> None:
        """Store message to RAG for long-term memory."""
        rag = await self._get_rag()
        if rag:
            try:
                await rag.store_message(
                    user_id=user_id,
                    role=role,
                    content=content,
                    metadata={"source": "assistant_mode"}
                )
            except Exception as e:
                logger.error(f"Failed to store message to RAG: {e}")
    
    async def _get_rag_context(self, user_id: str, query: str) -> str:
        """Get relevant context from RAG."""
        rag = await self._get_rag()
        if not rag:
            return ""
        
        try:
            context = await rag.get_relevant_context(
                user_id=user_id,
                query=query,
                max_messages=5,
                include_patterns=True,
            )
            return context.summary
        except Exception as e:
            logger.error(f"Failed to get RAG context: {e}")
            return ""
    
    def clear_history(self, user_id: str) -> None:
        """Clear conversation history for user."""
        if user_id in self._conversation_history:
            self._conversation_history[user_id] = []
    
    async def process_message(self, user_id: str, text: str) -> str:
        """
        Process a message in assistant mode using LLM with conversation history.
        
        Uses RAG for:
        1. Storing all messages for long-term memory
        2. Retrieving relevant past conversations for context
        3. Learning user preferences and patterns
        """
        prefs = self.secretary.get_preferences(user_id)
        
        # Store user message to RAG (async, don't block)
        asyncio.create_task(self._store_to_rag(user_id, "user", text))
        
        # Add user message to in-memory history
        self._add_to_history(user_id, "user", text)
        
        # Process with LLM (includes conversation history + RAG context)
        response = await self._process_with_llm(user_id, text, prefs)
        
        # Store assistant response to RAG
        asyncio.create_task(self._store_to_rag(user_id, "assistant", response))
        
        # Add assistant response to in-memory history
        self._add_to_history(user_id, "assistant", response)
        
        return response
    
    async def _process_with_llm(self, user_id: str, text: str, prefs: UserPreferences) -> str:
        """Process message with LLM for intelligent response."""
        try:
            from .llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            # Recognize intent for search decision
            intent_result = self.nlu.recognize_intent(text)

            # Get context, RAG, and web search in parallel
            import time as time_module
            parallel_start = time_module.time()

            context_task = asyncio.create_task(self._build_context(user_id, text))
            rag_task = asyncio.create_task(self._get_rag_context(user_id, text))

            # Run web search in parallel if needed
            search_task = None
            if self.web_search.needs_search(text, intent_result.intent):
                search_query = self.web_search.build_search_query(text, intent_result.intent)
                search_task = asyncio.create_task(self.web_search.search(search_query))
                logger.info(f"Web search triggered for: {search_query}")

            # Gather all parallel tasks
            search_context = ""
            if search_task:
                context, rag_context, search_context = await asyncio.gather(
                    context_task, rag_task, search_task
                )
            else:
                context, rag_context = await asyncio.gather(context_task, rag_task)

            parallel_elapsed = time_module.time() - parallel_start
            logger.info(f"Context + RAG + Search parallel fetch took {parallel_elapsed:.2f}s")

            # Combine contexts
            full_context = context
            if rag_context:
                full_context += f"\n\n## 相關歷史對話\n{rag_context}"
            if search_context:
                full_context += f"\n\n{search_context}"
            
            # Get current persona template
            persona = prefs.get_current_persona()
            
            # Create secretary persona prompt based on template
            system_prompt = f"""你是一位名叫「{persona.name}」的專屬 AI 助手。

## 你的人設：{persona.description}

## 你的性格特點
- 說話風格：{persona.tone}
- 表情使用：{persona.emoji_style}
- 問候方式：{persona.greeting_style}
- 關心程度：{"非常關心用戶" if persona.care_level == "high" else "適度關心" if persona.care_level == "medium" else "簡潔直接"}
- 正式程度：{"正式禮貌" if persona.formality == "formal" else "輕鬆自然" if persona.formality == "casual" else "適中"}
- 使用繁體中文回覆

## 用戶資訊
- 用戶名稱：{prefs.name or '主人'}
- 當前時間：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}

## 用戶當前狀態
{full_context}

## 你的能力
1. **待辦管理**：新增、查詢、完成待辦事項
2. **行程管理**：查詢、新增日曆行程
3. **訂票協助**：提供機票、火車票、飯店預訂的建議和資訊
4. **日常對話**：回答問題、聊天、提供建議
5. **資訊查詢**：可即時搜尋網路取得天氣、航班、票價、新聞等最新資訊

## 回應規則
1. 理解用戶的實際需求，提供有用的回應
2. 如果需要更多資訊，禮貌地詢問
3. 提供具體、可行的建議
4. 回覆結尾署名「{persona.signature}」
5. 保持簡潔但完整（3-8句話）
6. 如果提供了網路搜尋結果，自然地將搜尋資訊融入回覆，不要直接列出原始搜尋格式

## 特別指示
- 如果有網路搜尋結果，優先參考搜尋結果回答，但仍用自己的話回答，保持秘書的語氣
- 如果搜尋結果和問題不完全相關，請誠實說明並提供你知道的資訊
- 如果用戶詢問機票/旅遊，提供實用的建議（最佳訂票時機、推薦航空公司、大致價格範圍等）
- 如果用戶想新增待辦，確認內容後幫他記錄（系統會自動執行）
- 如果用戶想新增行程到日曆，確認時間和標題後告訴用戶已加入（系統會自動加入日曆）
- 如果用戶問行程，查看他的日曆並回報
- 這是連續對話，請記住之前的對話內容，保持上下文連貫
- 如果用戶提到「剛才」「之前」「上面」等，請回顧對話歷史來理解
- 如果有相關歷史對話，請參考過去的對話來理解用戶的需求和偏好

## 執行動作
當用戶請求以下動作時，請在回覆中明確說明已執行：
- 「幫我記...」「提醒我...」→ 會自動新增待辦事項
- 「加入行事曆」「新增行程」「安排...」→ 會自動加入日曆
請在回覆中確認動作已完成，並說明事件/任務的具體內容
{f"- {persona.system_prompt_addon}" if persona.system_prompt_addon else ""}"""

            # Build messages with conversation history
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            # Add conversation history (excluding current message which was just added)
            history = self._get_history(user_id)
            # Don't include the last message (current user message) since we'll add it below
            for msg in history[:-1]:
                messages.append(msg)
            
            # Add current user message
            messages.append({"role": "user", "content": text})
            
            logger.info(f"Assistant mode: sending {len(messages)} messages to LLM (including {len(history)-1} history)")
            
            response = await manager.generate(messages)
            
            if response:
                # Check if we need to perform any actions
                await self._check_and_execute_actions(user_id, text, response)
                return response
                
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
        
        # Fallback to keyword-based handling
        return await self._fallback_handler(user_id, text)
    
    async def _build_context(self, user_id: str, user_query: str = "") -> str:
        """Build context string for LLM based on user query."""
        import time as time_module
        start_time = time_module.time()
        
        lines = []
        query_lower = user_query.lower()
        
        # Determine calendar scope based on user query
        calendar_scope = "today"
        scope_label = "今日"
        
        this_week_keywords = ["這週", "本週", "這星期", "本星期", "這禮拜"]
        next_week_keywords = ["下週", "下星期", "下禮拜", "next week"]
        month_keywords = ["這個月", "本月", "這月", "month"]
        
        if any(kw in query_lower for kw in next_week_keywords):
            calendar_scope = "next_week"
            scope_label = "下週"
        elif any(kw in query_lower for kw in this_week_keywords):
            calendar_scope = "week"
            scope_label = "本週"
        elif any(kw in query_lower for kw in month_keywords):
            calendar_scope = "month"
            scope_label = "本月"
        
        logger.debug(f"Building context with scope: {calendar_scope}")
        
        # Calculate date range for context
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if calendar_scope == "today":
            context_start = today
            context_end = today + timedelta(days=1)
        elif calendar_scope == "week":
            days_since_monday = today.weekday()
            context_start = today - timedelta(days=days_since_monday)
            context_end = context_start + timedelta(days=7)
        elif calendar_scope == "next_week":
            days_since_monday = today.weekday()
            next_monday = today + timedelta(days=(7 - days_since_monday))
            context_start = next_monday
            context_end = next_monday + timedelta(days=7)
        else:  # month
            context_start = today.replace(day=1)
            if today.month == 12:
                context_end = today.replace(year=today.year + 1, month=1, day=1)
            else:
                context_end = today.replace(month=today.month + 1, day=1)
        
        # Tasks - filter by scope if asking about specific time range
        tasks = self.secretary.get_tasks(user_id)
        pending_tasks = [t for t in tasks if not t.completed]
        
        # Separate recurring and one-time tasks
        recurring_tasks = [t for t in pending_tasks if t.recurring != RecurringType.NONE]
        one_time_tasks = [t for t in pending_tasks if t.recurring == RecurringType.NONE]
        
        logger.info(f"Tasks for {user_id}: total={len(tasks)}, pending={len(pending_tasks)}, recurring={len(recurring_tasks)}, one_time={len(one_time_tasks)}")
        
        # Filter one-time tasks by due date if asking about specific time
        if calendar_scope != "today":
            scope_tasks = []
            no_due_tasks = []
            for t in one_time_tasks:
                if t.due_date:
                    if context_start <= t.due_date < context_end:
                        scope_tasks.append(t)
                else:
                    no_due_tasks.append(t)
            # Show tasks in scope + tasks without due date
            filtered_tasks = scope_tasks + no_due_tasks[:2]  # Limit no-due tasks
        else:
            filtered_tasks = one_time_tasks
        
        if filtered_tasks:
            lines.append(f"📋 {scope_label}待辦（{len(filtered_tasks)} 項）：")
            for i, task in enumerate(filtered_tasks[:5], 1):
                due_info = ""
                if task.due_date:
                    weekday = ['一', '二', '三', '四', '五', '六', '日'][task.due_date.weekday()]
                    due_info = f" (截止: {task.due_date.strftime('%m/%d')}({weekday}))"
                lines.append(f"  {i}. ⬜ {task.title}{due_info}")
        else:
            lines.append(f"📋 {scope_label}待辦：無")
        
        # Show recurring tasks separately
        if recurring_tasks:
            recurring_type_names = {
                RecurringType.DAILY: "每日",
                RecurringType.WEEKLY: "每週",
                RecurringType.WEEKDAYS: "平日",
                RecurringType.MONTHLY: "每月",
            }
            lines.append(f"\n🔁 重複提醒（{len(recurring_tasks)} 項）：")
            for task in recurring_tasks[:5]:
                type_name = recurring_type_names.get(task.recurring, "")
                time_str = task.recurring_time.strftime("%H:%M") if task.recurring_time else ""
                lines.append(f"  • {task.title} ({type_name} {time_str})")
        
        # Calendar events - get appropriate scope
        cal_start = time_module.time()
        events = await self.secretary._get_calendar_events(user_id, scope=calendar_scope)
        cal_elapsed = time_module.time() - cal_start
        logger.info(f"Calendar query took {cal_elapsed:.2f}s, found {len(events)} events")
        
        if events:
            lines.append(f"\n📅 {scope_label}行程（{len(events)} 項）：")
            for event in events[:10]:  # Show more for week view
                date_str = event.get('date', '')
                time_str = event.get('time', '')
                location = event.get('location', '')
                loc_info = f" @ {location}" if location else ""
                lines.append(f"  • {date_str} {time_str} - {event.get('title', '')}{loc_info}")
        else:
            lines.append(f"\n📅 {scope_label}行程：無排程")
        
        # Add current date info
        now = datetime.now()
        weekday_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
        lines.insert(0, f"📆 今天是 {now.strftime('%Y年%m月%d日')} {weekday_names[now.weekday()]}\n")
        
        total_elapsed = time_module.time() - start_time
        logger.debug(f"Context build took {total_elapsed:.2f}s")
        
        return "\n".join(lines)
    
    async def _check_and_execute_actions(self, user_id: str, user_text: str, llm_response: str) -> None:
        """Check if any actions need to be executed based on conversation."""
        text_lower = user_text.lower()
        response_lower = llm_response.lower()
        
        # ---- Calendar event detection (check FIRST) ----
        # Keywords that explicitly indicate calendar/event intent
        calendar_explicit_keywords = [
            "行事曆", "日曆", "calendar", "apple calendar", "google calendar",
        ]
        
        event_keywords = [
            "加入行事曆", "新增行程", "加到日曆", "安排", "排個", "約", "預約", "行程加入",
            "記錄到行事曆", "加行事曆", "加日曆", "寫入行事曆", "記到行事曆",
            "新增到行事曆", "加入日曆", "添加行程", "行事曆新增", "日曆加入",
            "記錄在行事曆", "記在行事曆", "記錄在日曆", "記在日曆",
            "記錄在apple", "加到apple", "加入apple",
        ]
        
        # Patterns that suggest an event (date + activity)
        event_patterns = [
            "尾牙", "聚餐", "開會", "會議", "約會", "面試", "出差", "旅行",
            "生日", "派對", "宴會", "活動", "表演", "演唱會", "展覽",
            "看醫生", "看診", "體檢", "健檢", "牙醫", "回診",
            "諮商", "心理諮商", "諮詢", "復健", "治療", "門診",
            "上課", "培訓", "講座", "研討會", "工作坊", "課程",
            "入席", "報到", "集合", "出發",
            "測試", "發布", "上線", "部署", "Demo",
            "約吃飯", "約見面", "約碰面", "約喝咖啡",
            "搭飛機", "搭車", "搭高鐵", "搭火車",
            "婚禮", "喪禮", "典禮", "畢業", "頒獎",
        ]
        
        # Date patterns (check if message contains date-like info)
        import re
        date_pattern = re.compile(
            r'(\d{1,2}[/\-\.月]\d{1,2}|'  # 1/2, 1-2, 1.2, 1月2
            r'\d{1,2}號|\d{1,2}日|'  # 1號, 1日
            r'明天|後天|大後天|'  # tomorrow, day after
            r'下週|下禮拜|下星期|'  # next week
            r'這週|這禮拜|這星期|'  # this week
            r'週[一二三四五六日]|'  # 週一
            r'星期[一二三四五六日天]|'  # 星期一
            r'禮拜[一二三四五六日天]|'  # 禮拜一
            r'今天|今日)'  # today
        )
        has_date = bool(date_pattern.search(user_text))
        
        # Time patterns
        time_pattern = re.compile(r'(\d{1,2}[:\：點時～~]\d{0,2}|早上|上午|中午|下午|晚上|凌晨)')
        has_time = bool(time_pattern.search(user_text))
        
        # Check if assistant's response mentions recording/adding
        response_confirms = any(kw in response_lower for kw in ["記錄", "記下", "安排", "加入", "新增"])
        
        # Check if user explicitly mentions calendar
        mentions_calendar = any(kw in text_lower for kw in calendar_explicit_keywords)
        
        # Trigger event addition if:
        # 1. User explicitly mentions calendar (highest priority), OR
        # 2. User explicitly asks to add event with event_keywords, OR
        # 3. Message has date + time + event-like content, OR
        # 4. Message has date + time + calendar mention, OR
        # 5. Message has date + event pattern and assistant confirms
        should_add_event = (
            (mentions_calendar and has_date) or
            any(kw in text_lower for kw in event_keywords) or
            (has_date and has_time and any(p in text_lower for p in event_patterns)) or
            (has_date and has_time and mentions_calendar) or
            (has_date and any(p in text_lower for p in event_patterns) and response_confirms)
        )
        
        if should_add_event:
            logger.info(f"Detected event intent for user {user_id}: {user_text[:50]}...")
            await self._try_add_calendar_event(user_id, user_text, llm_response)
            # When calendar event is explicitly requested, skip task creation
            return
        
        # ---- Task detection (check AFTER calendar event) ----
        task_keywords = ["幫我記", "新增待辦", "加一個任務", "記一下", "別忘了", "記得", "提醒我", "每天提醒", "每日提醒"]
        recurring_keywords = ["每天", "每日", "daily", "每週", "每星期", "每禮拜", "weekly", "每月", "monthly", "平日", "工作日"]
        
        if any(kw in text_lower for kw in task_keywords):
            # Check if this is a recurring task
            is_recurring = any(kw in text_lower for kw in recurring_keywords)
            
            if is_recurring:
                # Use LLM to extract recurring task details
                await self._try_add_recurring_task(user_id, user_text, llm_response)
            else:
                # Simple task - use LLM to extract properly
                await self._try_add_task_with_llm(user_id, user_text, llm_response)
    
    async def _try_add_task_with_llm(self, user_id: str, user_text: str, llm_response: str) -> bool:
        """Use LLM to extract task details and add task."""
        logger.info(f"Extracting task details for user {user_id}")
        
        try:
            from .llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            extract_prompt = f"""從以下對話中提取待辦事項資訊，以 JSON 格式回傳：
{{
    "title": "待辦事項標題（簡潔明確）",
    "due_date": "YYYY-MM-DD 格式的截止日期，無截止日期則為 null",
    "priority": "high/medium/low",
    "has_valid_task": true/false
}}

用戶說：{user_text}
AI 回覆：{llm_response}

今天是 {datetime.now().strftime('%Y-%m-%d')}（{['週一','週二','週三','週四','週五','週六','週日'][datetime.now().weekday()]}）

規則：
- 標題應該是完整的事項描述，不要截斷
- 「禮拜三」「週三」等要轉換成實際日期
- 如果沒有明確截止日期，due_date 設為 null
- 如果無法確定任務內容，將 has_valid_task 設為 false
只回傳 JSON，不要其他文字。"""
            
            messages = [{"role": "user", "content": extract_prompt}]
            result = await manager.generate(messages)
            
            if not result:
                logger.warning("Failed to extract task details from LLM")
                return False
            
            import json
            import re
            
            json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON found in LLM response: {result}")
                return False
            
            task_data = json.loads(json_match.group())
            
            if not task_data.get("has_valid_task", False):
                logger.info("LLM determined no valid task to add")
                return False
            
            title = task_data.get("title", "")
            due_date_str = task_data.get("due_date")
            priority_str = task_data.get("priority", "medium")
            
            if not title:
                logger.warning("Missing title for task")
                return False
            
            # Parse due date
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                except ValueError:
                    pass
            
            # Parse priority
            try:
                priority = TaskPriority(priority_str)
            except ValueError:
                priority = TaskPriority.MEDIUM
            
            # Add task
            self.secretary.add_task(
                user_id=user_id,
                title=title,
                due_date=due_date,
                priority=priority
            )
            logger.info(f"Added task for user {user_id}: {title} (due: {due_date}, priority: {priority.value})")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting task: {e}")
            return False
    
    async def _try_add_recurring_task(self, user_id: str, user_text: str, llm_response: str) -> bool:
        """Use LLM to extract recurring task details and add task."""
        logger.info(f"Extracting recurring task details for user {user_id}")
        
        try:
            from .llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            extract_prompt = f"""從以下對話中提取重複提醒任務資訊，以 JSON 格式回傳：
{{
    "title": "提醒事項標題（簡潔明確）",
    "recurring_type": "daily/weekly/weekdays/monthly",
    "recurring_time": "HH:MM 格式的提醒時間（24小時制）",
    "recurring_days": [0,1,2,3,4,5,6] (週一到週日為0-6，僅 weekly 類型需要),
    "priority": "high/medium/low",
    "has_valid_task": true/false
}}

用戶說：{user_text}
AI 回覆：{llm_response}

規則：
- 「每天」「每日」= daily
- 「每週」「每星期」= weekly（需指定 recurring_days）
- 「平日」「工作日」= weekdays（週一到週五）
- 「每月」= monthly
- 「早上」= 08:00，「中午」= 12:00，「下午」= 14:00，「晚上」= 18:00
- 如果無法確定時間，預設 09:00
- 如果無法確定任務內容或重複規則，將 has_valid_task 設為 false
只回傳 JSON，不要其他文字。"""
            
            messages = [{"role": "user", "content": extract_prompt}]
            result = await manager.generate(messages)
            
            if not result:
                logger.warning("Failed to extract recurring task details from LLM")
                return False
            
            import json
            import re
            
            json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON found in LLM response: {result}")
                return False
            
            task_data = json.loads(json_match.group())
            
            if not task_data.get("has_valid_task", False):
                logger.info("LLM determined no valid recurring task to add")
                return False
            
            title = task_data.get("title", "")
            recurring_type_str = task_data.get("recurring_type", "daily")
            recurring_time_str = task_data.get("recurring_time", "09:00")
            recurring_days = task_data.get("recurring_days", [])
            priority_str = task_data.get("priority", "medium")
            
            if not title:
                logger.warning("Missing title for recurring task")
                return False
            
            # Parse recurring type
            try:
                recurring_type = RecurringType(recurring_type_str)
            except ValueError:
                recurring_type = RecurringType.DAILY
            
            # Parse recurring time
            try:
                hour, minute = map(int, recurring_time_str.split(":"))
                recurring_time = time(hour, minute)
            except (ValueError, TypeError):
                recurring_time = time(9, 0)
            
            # Parse priority
            try:
                priority = TaskPriority(priority_str)
            except ValueError:
                priority = TaskPriority.MEDIUM
            
            # Add recurring task
            self.secretary.add_recurring_task(
                user_id=user_id,
                title=title,
                recurring=recurring_type,
                recurring_time=recurring_time,
                recurring_days=recurring_days,
                priority=priority
            )
            logger.info(f"Added recurring task for user {user_id}: {title} ({recurring_type.value} at {recurring_time})")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting recurring task: {e}")
            return False
    
    async def _try_add_calendar_event(self, user_id: str, user_text: str, llm_response: str) -> bool:
        """Try to extract event details and add to calendar."""
        logger.info(f"Attempting to add calendar event for user {user_id}")
        
        try:
            # Use LLM to extract event details
            from .llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            extract_prompt = f"""從以下對話中提取日曆事件資訊，以 JSON 格式回傳：
{{
    "title": "事件標題",
    "date": "YYYY-MM-DD 格式的日期",
    "start_time": "HH:MM 格式的開始時間（24小時制），整日事件填 00:00",
    "end_time": "HH:MM 格式的結束時間（24小時制），整日事件填 23:59，如果沒有指定就根據 start_time 加 1 小時",
    "all_day": true/false（是否為整日事件）,
    "location": "地點（如果有）",
    "has_valid_event": true/false
}}

用戶說：{user_text}
AI 回覆：{llm_response}

今天是 {datetime.now().strftime('%Y-%m-%d')}（{['週一','週二','週三','週四','週五','週六','週日'][datetime.now().weekday()]}）

規則：
- 「整日」「全天」表示 all_day=true, start_time="00:00", end_time="23:59"
- 計算正確的日期：禮拜三、週三、星期三都要轉換成實際日期
- 2/12 表示 2 月 12 日，需轉為目前年份的 YYYY-MM-DD
- 19:00～19:50 表示 start_time="19:00", end_time="19:50"
- 如果只有開始時間沒有結束時間，end_time = start_time + 1 小時
- 如果無法確定日期或事件不清楚，將 has_valid_event 設為 false
只回傳 JSON，不要其他文字。"""
            
            messages = [{"role": "user", "content": extract_prompt}]
            result = await manager.generate(messages)
            
            if not result:
                logger.warning("Failed to extract event details from LLM")
                return False
            
            # Parse JSON
            import json
            import re
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON found in LLM response: {result}")
                return False
            
            event_data = json.loads(json_match.group())
            
            if not event_data.get("has_valid_event", False):
                logger.info("LLM determined no valid event to add")
                return False
            
            title = event_data.get("title", "")
            date_str = event_data.get("date", "")
            # Support both old format (time/duration_hours) and new format (start_time/end_time)
            start_time_str = event_data.get("start_time") or event_data.get("time", "09:00")
            end_time_str = event_data.get("end_time", "")
            duration = event_data.get("duration_hours", 1)
            location = event_data.get("location", "")
            all_day = event_data.get("all_day", False)
            
            logger.info(f"Extracted event: title={title}, date={date_str}, start={start_time_str}, end={end_time_str}, location={location}, all_day={all_day}")
            
            if not title or not date_str:
                logger.warning("Missing title or date for event")
                return False
            
            # Build start datetime
            try:
                start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            except ValueError:
                # If time parsing fails, default to 9:00
                start_dt = datetime.strptime(f"{date_str} 09:00", "%Y-%m-%d %H:%M")
            
            if all_day:
                # For all-day events, set to start of day
                start_dt = start_dt.replace(hour=0, minute=0, second=0)
                end_dt = start_dt + timedelta(days=1)
            elif end_time_str:
                # Use explicit end time if provided
                try:
                    end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
                    # Handle edge case: end time is before start time (should not happen)
                    if end_dt <= start_dt:
                        end_dt = start_dt + timedelta(hours=1)
                except ValueError:
                    end_dt = start_dt + timedelta(hours=duration if duration else 1)
            else:
                end_dt = start_dt + timedelta(hours=duration if duration else 1)
            
            logger.info(f"Event datetime: {start_dt} - {end_dt}, all_day={all_day}")
            
            # Try Google Calendar first
            try:
                from .google_calendar import get_google_calendar_manager
                gcal = get_google_calendar_manager()
                
                if gcal and gcal.is_authenticated:
                    event = await gcal.create_event(
                        title=title,
                        start=start_dt.isoformat(),
                        end=end_dt.isoformat(),
                        location=location,
                    )
                    
                    if event:
                        logger.info(f"Added Google Calendar event for user {user_id}: {title} at {start_dt}")
                        return True
            except Exception as e:
                logger.debug(f"Google Calendar failed: {e}")
            
            # Try Apple Calendar
            try:
                from .apple_calendar import get_apple_calendar
                apple = get_apple_calendar()
                
                if apple and apple.is_available():
                    logger.info(f"Creating Apple Calendar event: {title}, {start_dt}, all_day={all_day}")
                    event_id = apple.create_event(
                        title=title,
                        start_time=start_dt,
                        end_time=end_dt,
                        location=location,
                        all_day=all_day,
                    )
                    
                    if event_id:
                        logger.info(f"Added Apple Calendar event for user {user_id}: {title} at {start_dt}")
                        return True
                    else:
                        logger.warning(f"Apple Calendar create_event returned None for: {title}")
            except Exception as e:
                logger.error(f"Apple Calendar failed: {e}", exc_info=True)
            
            # Fallback: add as a task with date
            self.secretary.add_task(
                user_id,
                f"📅 {title}" + (f" @ {location}" if location else ""),
                due_date=start_dt,
            )
            logger.info(f"Added event as task for user {user_id}: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add calendar event: {e}")
            return False
    
    async def _fallback_handler(self, user_id: str, text: str) -> str:
        """Fallback handler when LLM is not available."""
        prefs = self.secretary.get_preferences(user_id)
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
            AssistantIntent.SEARCH: self._handle_search,
            AssistantIntent.CHAT: self._handle_chat,
        }
        
        handler = handlers.get(result.intent, self._handle_unknown)
        return await handler(user_id, result)
    
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
    
    async def _handle_search(self, user_id: str, result: IntentResult) -> str:
        """Handle search intent - perform web search and return results."""
        prefs = self.secretary.get_preferences(user_id)
        text = result.original_text or ""

        if not text:
            return f"請問您想查什麼呢？告訴我關鍵字，我馬上幫您搜尋！\n\n—— {prefs.secretary_name}"

        try:
            query = self.web_search.build_search_query(text, result.intent)
            search_result = await self.web_search.search(query)

            if search_result:
                return (
                    f"🔍 為您搜尋了「{query}」的相關資訊：\n\n"
                    f"{search_result}\n\n"
                    f"—— {prefs.secretary_name}"
                )
            else:
                return (
                    f"抱歉，目前搜尋不到「{query}」的相關結果，"
                    f"您可以換個關鍵字再試試看喔！\n\n"
                    f"—— {prefs.secretary_name}"
                )
        except Exception as e:
            logger.error(f"Search handler error: {e}")
            return (
                f"搜尋時遇到了一點問題，請稍後再試～\n\n"
                f"—— {prefs.secretary_name}"
            )

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
            
            # Build messages in OpenAI format
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": result.original_text},
            ]
            
            response = await manager.generate(messages)
            
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


# ============================================
# Recurring Task Scheduler
# ============================================

class RecurringTaskScheduler:
    """
    Scheduler for recurring task reminders.
    
    Checks all recurring tasks and sends reminders at the scheduled times.
    """
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._send_handlers: dict[str, Callable] = {}  # platform -> handler
        self._last_check: Optional[datetime] = None
        
        logger.info("RecurringTaskScheduler initialized")
    
    def register_handler(self, platform: str, handler: Callable) -> None:
        """Register a send handler for a platform."""
        self._send_handlers[platform] = handler
        logger.debug(f"Registered recurring task handler for {platform}")
    
    async def start(self) -> None:
        """Start the recurring task scheduler."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("RecurringTaskScheduler started")
    
    async def stop(self) -> None:
        """Stop the recurring task scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _run_loop(self) -> None:
        """Main scheduler loop - check every minute."""
        while self._running:
            try:
                now = datetime.now()
                
                # Only check once per minute
                if self._last_check and now.minute == self._last_check.minute:
                    await asyncio.sleep(30)
                    continue
                
                self._last_check = now
                
                # Check all users' recurring tasks
                await self._check_and_send_reminders()
                
                # Wait before next check
                await asyncio.sleep(30)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"RecurringTaskScheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_send_reminders(self) -> None:
        """Check all recurring tasks and send reminders."""
        secretary = get_secretary()
        
        for user_id, tasks in secretary._tasks.items():
            for task in tasks:
                if task.should_remind_now():
                    await self._send_reminder(user_id, task)
                    
                    # Update last reminded time
                    task.last_reminded = datetime.now()
                    secretary._save_data()
    
    async def _send_reminder(self, user_id: str, task: Task) -> None:
        """Send a reminder for a recurring task."""
        prefs = get_secretary().get_preferences(user_id)
        
        # Build reminder message
        recurring_type_names = {
            RecurringType.DAILY: "每日",
            RecurringType.WEEKLY: "每週",
            RecurringType.WEEKDAYS: "平日",
            RecurringType.MONTHLY: "每月",
        }
        type_name = recurring_type_names.get(task.recurring, "")
        
        message = f"""⏰ **{type_name}提醒**

📌 {task.title}

記得完成這件事喔！

—— {prefs.secretary_name}"""
        
        # Try to send via registered handlers
        for platform, handler in self._send_handlers.items():
            try:
                await handler(user_id, message)
                logger.info(f"Sent recurring reminder to {user_id} via {platform}: {task.title}")
                return
            except Exception as e:
                logger.warning(f"Failed to send recurring reminder via {platform}: {e}")
        
        logger.warning(f"Failed to send recurring reminder to {user_id}: no handler succeeded")


# ============================================
# Secretary Briefing Scheduler
# ============================================

class SecretaryBriefingScheduler:
    """
    Scheduler for automatic daily briefing.
    
    Reads from environment variables:
        SECRETARY_BRIEFING_ENABLED: Enable/disable automatic briefing (default: false)
        SECRETARY_BRIEFING_TIME: Time to send briefing in HH:MM format (default: 09:00)
        SECRETARY_BRIEFING_USERS: Comma-separated list of user IDs to send briefing to
    """
    
    # Briefing types based on time of day
    BRIEFING_TYPES = {
        "morning": {"start": 5, "end": 12, "name": "早報", "greeting": "早安"},
        "afternoon": {"start": 12, "end": 18, "name": "午報", "greeting": "午安"},
        "evening": {"start": 18, "end": 24, "name": "晚報", "greeting": "晚安"},
        "night": {"start": 0, "end": 5, "name": "夜報", "greeting": "夜深了"},
    }
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._send_handlers: dict[str, Callable] = {}  # platform -> handler
        self._sent_today: set[str] = set()  # Track sent briefings: "HH:MM_user_id"
        
        # Load settings from pydantic settings (which reads from .env)
        self.enabled = settings.secretary_briefing_enabled
        
        # Parse multiple times (comma-separated)
        time_str = settings.secretary_briefing_time
        self.briefing_times: list[time] = []
        for t in time_str.split(","):
            t = t.strip()
            if not t:
                continue
            try:
                hour, minute = map(int, t.split(":"))
                self.briefing_times.append(time(hour, minute))
            except ValueError:
                logger.warning(f"Invalid briefing time: {t}, skipping")
        
        if not self.briefing_times:
            self.briefing_times = [time(9, 0)]  # Default to 09:00
            logger.warning("No valid briefing times found, using default 09:00")
        
        # User IDs to send briefing to (from settings or from preferences)
        users_str = settings.secretary_briefing_users
        self.target_users = [u.strip() for u in users_str.split(",") if u.strip()]
        
        # Platforms to send briefing to (can select multiple)
        platforms_str = settings.secretary_briefing_platforms
        self.target_platforms = [p.strip().lower() for p in platforms_str.split(",") if p.strip()]
        if not self.target_platforms:
            self.target_platforms = ["telegram"]  # Default to Telegram
        
        times_str = ", ".join(t.strftime("%H:%M") for t in self.briefing_times)
        logger.info(f"SecretaryBriefingScheduler: enabled={self.enabled}, times=[{times_str}], users={self.target_users}, platforms={self.target_platforms}")
    
    def register_send_handler(self, platform: str, handler: Callable) -> None:
        """Register a send handler for a platform."""
        self._send_handlers[platform] = handler
        logger.debug(f"Registered briefing handler for {platform}")
    
    async def start(self) -> None:
        """Start the briefing scheduler."""
        if not self.enabled:
            logger.info("Secretary briefing scheduler is disabled")
            return
        
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        times_str = ", ".join(t.strftime("%H:%M") for t in self.briefing_times)
        logger.info(f"Secretary briefing scheduler started, will send at: {times_str}")
    
    async def stop(self) -> None:
        """Stop the briefing scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def _get_briefing_type(self, hour: int) -> dict:
        """Get briefing type based on hour of day."""
        for btype, config in self.BRIEFING_TYPES.items():
            if config["start"] <= hour < config["end"]:
                return {"type": btype, **config}
        return {"type": "morning", **self.BRIEFING_TYPES["morning"]}
    
    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        # Reset sent tracking at midnight
        last_date = datetime.now().date()
        
        while self._running:
            try:
                now = datetime.now()
                
                # Reset sent tracking at midnight
                if now.date() != last_date:
                    self._sent_today.clear()
                    last_date = now.date()
                
                # Check if current time matches any of the briefing times
                current_time_key = f"{now.hour:02d}:{now.minute:02d}"
                
                for briefing_time in self.briefing_times:
                    if now.hour == briefing_time.hour and now.minute == briefing_time.minute:
                        # Check if we already sent for this time today
                        if current_time_key not in self._sent_today:
                            await self._send_briefings(briefing_time)
                            self._sent_today.add(current_time_key)
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Secretary briefing scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _send_briefings(self, briefing_time: time) -> None:
        """Send briefings to all configured users."""
        secretary = get_secretary()
        
        # Get briefing type based on time
        briefing_type = self._get_briefing_type(briefing_time.hour)
        
        # Get users to send to
        users_to_notify = []
        
        if self.target_users:
            # Use explicitly configured users
            users_to_notify = self.target_users
        else:
            # Get all users with briefing enabled from preferences
            for user_id, prefs in secretary._preferences.items():
                if prefs.briefing_enabled:
                    users_to_notify.append(user_id)
        
        if not users_to_notify:
            logger.debug("No users to send briefing to")
            return
        
        logger.info(f"Sending {briefing_type['name']} to {len(users_to_notify)} users at {briefing_time.strftime('%H:%M')}")
        
        for user_id in users_to_notify:
            try:
                await self._send_briefing_to_user(user_id, secretary, briefing_type)
            except Exception as e:
                logger.error(f"Failed to send briefing to {user_id}: {e}")
    
    async def _send_briefing_to_user(self, user_id: str, secretary: PersonalSecretary, briefing_type: dict) -> None:
        """Send briefing to a specific user on configured platforms."""
        # Generate briefing with time-based greeting
        briefing = await secretary.daily_briefing(user_id, briefing_type=briefing_type)
        
        # Send to all configured platforms
        sent_platforms = []
        failed_platforms = []
        
        for platform in self.target_platforms:
            if platform not in self._send_handlers:
                logger.warning(f"Platform '{platform}' not registered, skipping")
                continue
            
            handler = self._send_handlers[platform]
            try:
                # The handler expects (chat_id, message)
                # For Telegram, chat_id is usually same as user_id for DMs
                await handler(user_id, briefing)
                logger.info(f"Sent briefing to {user_id} via {platform}")
                sent_platforms.append(platform)
            except Exception as e:
                logger.warning(f"Failed to send briefing via {platform}: {e}")
                failed_platforms.append(platform)
        
        if sent_platforms:
            logger.info(f"Briefing sent to {user_id} via: {', '.join(sent_platforms)}")
        else:
            logger.error(f"Could not send briefing to {user_id}: all platforms failed ({', '.join(failed_platforms)})")
    
    async def send_test_briefing(self, user_id: str) -> str:
        """Send a test briefing to a user (for debugging)."""
        secretary = get_secretary()
        return await secretary.daily_briefing(user_id)


# Global briefing scheduler instance
_briefing_scheduler: Optional[SecretaryBriefingScheduler] = None


def get_briefing_scheduler() -> SecretaryBriefingScheduler:
    """Get the global SecretaryBriefingScheduler instance."""
    global _briefing_scheduler
    if _briefing_scheduler is None:
        _briefing_scheduler = SecretaryBriefingScheduler()
    return _briefing_scheduler


# Global recurring task scheduler instance
_recurring_task_scheduler: Optional[RecurringTaskScheduler] = None


def get_recurring_task_scheduler() -> RecurringTaskScheduler:
    """Get the global RecurringTaskScheduler instance."""
    global _recurring_task_scheduler
    if _recurring_task_scheduler is None:
        _recurring_task_scheduler = RecurringTaskScheduler()
    return _recurring_task_scheduler


__all__ = [
    "PersonalSecretary",
    "SecretaryPersona",
    "Task",
    "TaskPriority",
    "RecurringType",
    "UserPreferences",
    "AssistantIntent",
    "AssistantNLU",
    "AssistantMode",
    "SecretaryBriefingScheduler",
    "RecurringTaskScheduler",
    "get_secretary",
    "get_assistant_mode",
    "get_briefing_scheduler",
    "get_recurring_task_scheduler",
]
