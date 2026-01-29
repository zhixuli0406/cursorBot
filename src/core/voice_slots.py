"""
Slot Filling System for CursorBot v1.1

Provides multi-turn dialogue slot filling:
- Missing information detection
- Contextual prompting
- Entity validation
- Dialogue state tracking

Usage:
    from src.core.voice_slots import get_slot_manager
    
    manager = get_slot_manager()
    result = await manager.fill_slots(intent, utterance)
    
    if result.needs_more_info:
        prompt = result.prompt
        # Ask user for more info
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..utils.logger import logger
from .voice_assistant import Intent, IntentCategory, Utterance


# ============================================
# Enums
# ============================================

class SlotType(Enum):
    """Types of slots."""
    TEXT = "text"           # Free text
    NUMBER = "number"       # Numeric value
    DATE = "date"           # Date
    TIME = "time"           # Time
    DATETIME = "datetime"   # Date and time
    DURATION = "duration"   # Time duration
    LOCATION = "location"   # Place/location
    PERSON = "person"       # Person name
    FILE = "file"           # File path
    APP = "app"             # Application name
    URL = "url"             # Web URL
    EMAIL = "email"         # Email address
    PHONE = "phone"         # Phone number
    CHOICE = "choice"       # Multiple choice
    BOOLEAN = "boolean"     # Yes/No


class SlotStatus(Enum):
    """Slot filling status."""
    EMPTY = "empty"         # Not filled
    PARTIAL = "partial"     # Partially filled
    FILLED = "filled"       # Completely filled
    CONFIRMED = "confirmed" # User confirmed
    INVALID = "invalid"     # Invalid value


# ============================================
# Data Classes
# ============================================

@dataclass
class SlotDefinition:
    """Definition of a slot."""
    name: str
    type: SlotType
    required: bool = True
    default: Any = None
    prompt: str = ""  # Prompt to ask user
    validation: Optional[Callable] = None
    choices: List[str] = field(default_factory=list)  # For choice type
    examples: List[str] = field(default_factory=list)


@dataclass
class SlotValue:
    """Value of a filled slot."""
    slot: SlotDefinition
    value: Any = None
    raw_text: str = ""
    status: SlotStatus = SlotStatus.EMPTY
    confidence: float = 0.0


@dataclass
class SlotFillingResult:
    """Result of slot filling attempt."""
    intent: Intent
    slots: Dict[str, SlotValue]
    needs_more_info: bool = False
    missing_slots: List[str] = field(default_factory=list)
    prompt: str = ""
    is_complete: bool = False


@dataclass
class DialogueState:
    """Current dialogue state for slot filling."""
    intent: Optional[Intent] = None
    slots: Dict[str, SlotValue] = field(default_factory=dict)
    current_slot: Optional[str] = None
    turn_count: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)


# ============================================
# Slot Templates
# ============================================

# Define slot templates for different intents
INTENT_SLOT_TEMPLATES = {
    IntentCategory.REMINDER: [
        SlotDefinition(
            name="content",
            type=SlotType.TEXT,
            required=True,
            prompt="請問要提醒您什麼事情？",
            examples=["開會", "喝水", "回電話"]
        ),
        SlotDefinition(
            name="time",
            type=SlotType.DATETIME,
            required=False,
            prompt="什麼時候提醒您？",
            examples=["10分鐘後", "明天早上9點", "下午3點"]
        ),
    ],
    IntentCategory.CALENDAR: [
        SlotDefinition(
            name="action",
            type=SlotType.CHOICE,
            required=True,
            prompt="您想查詢還是新增行程？",
            choices=["查詢", "新增", "刪除", "修改"]
        ),
        SlotDefinition(
            name="date",
            type=SlotType.DATE,
            required=False,
            prompt="哪一天的行程？",
            examples=["今天", "明天", "下週一"]
        ),
        SlotDefinition(
            name="title",
            type=SlotType.TEXT,
            required=False,
            prompt="行程名稱是什麼？",
        ),
    ],
    IntentCategory.SEARCH: [
        SlotDefinition(
            name="query",
            type=SlotType.TEXT,
            required=True,
            prompt="請問您要搜尋什麼？",
        ),
        SlotDefinition(
            name="scope",
            type=SlotType.CHOICE,
            required=False,
            prompt="在哪裡搜尋？",
            choices=["網路", "檔案", "程式碼", "筆記"],
            default="網路"
        ),
    ],
    IntentCategory.CODE: [
        SlotDefinition(
            name="action",
            type=SlotType.CHOICE,
            required=True,
            prompt="您想執行什麼程式碼操作？",
            choices=["commit", "push", "pull", "test", "build", "run"]
        ),
        SlotDefinition(
            name="message",
            type=SlotType.TEXT,
            required=False,
            prompt="Commit 訊息是什麼？",
        ),
        SlotDefinition(
            name="file",
            type=SlotType.FILE,
            required=False,
            prompt="要操作哪個檔案？",
        ),
    ],
    IntentCategory.COMMAND: [
        SlotDefinition(
            name="target",
            type=SlotType.APP,
            required=True,
            prompt="要操作哪個應用程式？",
        ),
        SlotDefinition(
            name="action",
            type=SlotType.CHOICE,
            required=False,
            prompt="要執行什麼操作？",
            choices=["打開", "關閉", "最小化", "最大化"],
            default="打開"
        ),
    ],
}


# ============================================
# Entity Extractors
# ============================================

class EntityExtractor:
    """Extract entities from text."""
    
    @staticmethod
    def extract_datetime(text: str) -> Optional[datetime]:
        """Extract datetime from text."""
        now = datetime.now()
        text_lower = text.lower()
        
        # Relative time patterns
        patterns = [
            # Minutes
            (r"(\d+)\s*分鐘後", lambda m: now + timedelta(minutes=int(m.group(1)))),
            (r"(\d+)\s*minutes?", lambda m: now + timedelta(minutes=int(m.group(1)))),
            # Hours
            (r"(\d+)\s*小時後", lambda m: now + timedelta(hours=int(m.group(1)))),
            (r"(\d+)\s*hours?", lambda m: now + timedelta(hours=int(m.group(1)))),
            # Days
            (r"(\d+)\s*天後", lambda m: now + timedelta(days=int(m.group(1)))),
            (r"(\d+)\s*days?", lambda m: now + timedelta(days=int(m.group(1)))),
        ]
        
        for pattern, handler in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return handler(match)
        
        # Named times
        if "明天" in text or "tomorrow" in text_lower:
            result = now + timedelta(days=1)
            # Extract time if present
            time_match = re.search(r"(\d{1,2})[：:點](\d{0,2})?", text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                result = result.replace(hour=hour, minute=minute, second=0)
            else:
                result = result.replace(hour=9, minute=0, second=0)
            return result
        
        if "後天" in text:
            result = now + timedelta(days=2)
            result = result.replace(hour=9, minute=0, second=0)
            return result
        
        # Time of day
        time_keywords = {
            "早上": 8, "上午": 9, "中午": 12,
            "下午": 14, "傍晚": 17, "晚上": 20,
            "morning": 8, "noon": 12, "afternoon": 14, "evening": 20
        }
        
        for keyword, hour in time_keywords.items():
            if keyword in text_lower:
                result = now.replace(hour=hour, minute=0, second=0)
                if result < now:
                    result += timedelta(days=1)
                return result
        
        # Specific time
        time_match = re.search(r"(\d{1,2})[：:點](\d{0,2})?", text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            result = now.replace(hour=hour, minute=minute, second=0)
            if result < now:
                result += timedelta(days=1)
            return result
        
        return None
    
    @staticmethod
    def extract_date(text: str) -> Optional[datetime]:
        """Extract date from text."""
        now = datetime.now()
        text_lower = text.lower()
        
        if "今天" in text or "today" in text_lower:
            return now.replace(hour=0, minute=0, second=0)
        if "明天" in text or "tomorrow" in text_lower:
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        if "後天" in text:
            return (now + timedelta(days=2)).replace(hour=0, minute=0, second=0)
        
        # Weekdays
        weekday_map = {
            "週一": 0, "週二": 1, "週三": 2, "週四": 3,
            "週五": 4, "週六": 5, "週日": 6,
            "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3,
            "星期五": 4, "星期六": 5, "星期日": 6,
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        for name, weekday in weekday_map.items():
            if name in text_lower:
                days_ahead = weekday - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0)
        
        return None
    
    @staticmethod
    def extract_duration(text: str) -> Optional[timedelta]:
        """Extract duration from text."""
        text_lower = text.lower()
        
        patterns = [
            (r"(\d+)\s*分鐘|(\d+)\s*minutes?", lambda m: timedelta(minutes=int(m.group(1) or m.group(2)))),
            (r"(\d+)\s*小時|(\d+)\s*hours?", lambda m: timedelta(hours=int(m.group(1) or m.group(2)))),
            (r"(\d+)\s*天|(\d+)\s*days?", lambda m: timedelta(days=int(m.group(1) or m.group(2)))),
        ]
        
        for pattern, handler in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return handler(match)
        
        return None
    
    @staticmethod
    def extract_number(text: str) -> Optional[float]:
        """Extract number from text."""
        # Chinese number words
        cn_numbers = {
            "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "百": 100, "千": 1000, "萬": 10000
        }
        
        # Try numeric
        match = re.search(r"[-+]?\d*\.?\d+", text)
        if match:
            return float(match.group())
        
        # Try Chinese numbers (simplified)
        for cn, num in cn_numbers.items():
            if cn in text:
                return float(num)
        
        return None
    
    @staticmethod
    def extract_app_name(text: str) -> Optional[str]:
        """Extract application name from text."""
        app_patterns = [
            r"(?:打開|開啟|啟動|open|launch)\s+(\w+)",
            r"(?:關閉|close|quit)\s+(\w+)",
        ]
        
        for pattern in app_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None


# ============================================
# Slot Filling Manager
# ============================================

class SlotFillingManager:
    """
    Manages slot filling for multi-turn dialogue.
    
    Tracks dialogue state, extracts entities, and prompts
    for missing information.
    """
    
    def __init__(self):
        self._states: Dict[str, DialogueState] = {}  # user_id -> state
        self._extractor = EntityExtractor()
    
    def get_slot_template(self, intent: Intent) -> List[SlotDefinition]:
        """Get slot template for intent."""
        return INTENT_SLOT_TEMPLATES.get(intent.category, [])
    
    async def fill_slots(
        self,
        intent: Intent,
        utterance: Utterance,
        user_id: str = "default"
    ) -> SlotFillingResult:
        """
        Attempt to fill slots from utterance.
        
        Args:
            intent: Recognized intent
            utterance: User's input
            user_id: User identifier for state tracking
            
        Returns:
            SlotFillingResult with filled slots and prompts
        """
        # Get or create dialogue state
        state = self._get_or_create_state(user_id, intent)
        
        # Get slot template
        template = self.get_slot_template(intent)
        if not template:
            # No slots needed for this intent
            return SlotFillingResult(
                intent=intent,
                slots={},
                is_complete=True
            )
        
        # Initialize slots if new dialogue
        if not state.slots:
            for slot_def in template:
                state.slots[slot_def.name] = SlotValue(
                    slot=slot_def,
                    status=SlotStatus.EMPTY
                )
        
        # Extract entities from utterance
        text = utterance.text
        
        for slot_name, slot_value in state.slots.items():
            if slot_value.status in (SlotStatus.FILLED, SlotStatus.CONFIRMED):
                continue
            
            slot_def = slot_value.slot
            extracted = self._extract_slot_value(text, slot_def)
            
            if extracted is not None:
                slot_value.value = extracted
                slot_value.raw_text = text
                slot_value.status = SlotStatus.FILLED
                slot_value.confidence = 0.8
        
        # Also check entities from intent
        if intent.entities:
            for entity_name, entity_value in intent.entities.items():
                if entity_name in state.slots:
                    slot_value = state.slots[entity_name]
                    if slot_value.status == SlotStatus.EMPTY:
                        slot_value.value = entity_value
                        slot_value.status = SlotStatus.FILLED
        
        # Update state
        state.turn_count += 1
        state.last_update = datetime.now()
        
        # Check for missing required slots
        missing_slots = []
        for slot_name, slot_value in state.slots.items():
            if slot_value.slot.required and slot_value.status == SlotStatus.EMPTY:
                missing_slots.append(slot_name)
        
        # Generate prompt if needed
        prompt = ""
        if missing_slots:
            next_slot = missing_slots[0]
            state.current_slot = next_slot
            slot_def = state.slots[next_slot].slot
            prompt = slot_def.prompt
            
            if slot_def.examples:
                examples = "、".join(slot_def.examples[:3])
                prompt += f"（例如：{examples}）"
        
        is_complete = len(missing_slots) == 0
        
        # Clear state if complete
        if is_complete:
            self._clear_state(user_id)
        
        return SlotFillingResult(
            intent=intent,
            slots=state.slots,
            needs_more_info=not is_complete,
            missing_slots=missing_slots,
            prompt=prompt,
            is_complete=is_complete
        )
    
    def _extract_slot_value(self, text: str, slot_def: SlotDefinition) -> Any:
        """Extract value for a specific slot type."""
        if slot_def.type == SlotType.DATETIME:
            return self._extractor.extract_datetime(text)
        elif slot_def.type == SlotType.DATE:
            return self._extractor.extract_date(text)
        elif slot_def.type == SlotType.DURATION:
            return self._extractor.extract_duration(text)
        elif slot_def.type == SlotType.NUMBER:
            return self._extractor.extract_number(text)
        elif slot_def.type == SlotType.APP:
            return self._extractor.extract_app_name(text)
        elif slot_def.type == SlotType.CHOICE:
            # Check if text contains any choice
            for choice in slot_def.choices:
                if choice.lower() in text.lower():
                    return choice
            return None
        elif slot_def.type == SlotType.BOOLEAN:
            yes_patterns = ["是", "對", "好", "確定", "yes", "ok", "sure"]
            no_patterns = ["不", "否", "取消", "no", "cancel"]
            text_lower = text.lower()
            for p in yes_patterns:
                if p in text_lower:
                    return True
            for p in no_patterns:
                if p in text_lower:
                    return False
            return None
        elif slot_def.type == SlotType.TEXT:
            # For text slots, try to extract meaningful content
            # Remove common prefixes
            prefixes = [
                r"^提醒我",
                r"^記住",
                r"^幫我",
                r"^請",
            ]
            result = text
            for prefix in prefixes:
                result = re.sub(prefix, "", result)
            return result.strip() if result.strip() else None
        
        return None
    
    def _get_or_create_state(self, user_id: str, intent: Intent) -> DialogueState:
        """Get or create dialogue state for user."""
        # Check if we have an ongoing dialogue
        if user_id in self._states:
            state = self._states[user_id]
            # Check if same intent and not expired
            if (state.intent and 
                state.intent.category == intent.category and
                (datetime.now() - state.last_update).seconds < 300):
                return state
        
        # Create new state
        state = DialogueState(intent=intent)
        self._states[user_id] = state
        return state
    
    def _clear_state(self, user_id: str) -> None:
        """Clear dialogue state for user."""
        if user_id in self._states:
            del self._states[user_id]
    
    def get_filled_values(self, result: SlotFillingResult) -> Dict[str, Any]:
        """Extract filled values from result."""
        values = {}
        for slot_name, slot_value in result.slots.items():
            if slot_value.status in (SlotStatus.FILLED, SlotStatus.CONFIRMED):
                values[slot_name] = slot_value.value
            elif slot_value.slot.default is not None:
                values[slot_name] = slot_value.slot.default
        return values
    
    def cancel_dialogue(self, user_id: str) -> None:
        """Cancel ongoing dialogue."""
        self._clear_state(user_id)


# ============================================
# Global Instance
# ============================================

_slot_manager: Optional[SlotFillingManager] = None


def get_slot_manager() -> SlotFillingManager:
    """Get or create the global slot manager."""
    global _slot_manager
    if _slot_manager is None:
        _slot_manager = SlotFillingManager()
    return _slot_manager


__all__ = [
    "SlotType",
    "SlotStatus",
    "SlotDefinition",
    "SlotValue",
    "SlotFillingResult",
    "DialogueState",
    "SlotFillingManager",
    "EntityExtractor",
    "get_slot_manager",
]
