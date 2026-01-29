"""
Voice Learning & Personalization for CursorBot v1.1

Provides personalization features:
- User preference learning
- Usage pattern recognition
- Command frequency tracking
- Response style adaptation
- Contextual shortcuts
- Voice recognition adaptation

Usage:
    from src.core.voice_learning import get_learning_engine
    
    engine = get_learning_engine()
    await engine.record_interaction(utterance, response)
    suggestions = engine.get_personalized_suggestions()
"""

import json
import os
import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib

from ..utils.logger import logger
from .voice_assistant import Intent, IntentCategory, Utterance


# ============================================
# Data Classes
# ============================================

@dataclass
class UserProfile:
    """User profile for personalization."""
    user_id: str = "default"
    name: str = ""
    preferred_language: str = "zh-TW"
    preferred_voice: str = "zh-TW-HsiaoChenNeural"
    response_style: str = "friendly"
    
    # Learned patterns
    common_commands: Dict[str, int] = field(default_factory=dict)
    common_queries: Dict[str, int] = field(default_factory=dict)
    time_patterns: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Preferences
    shortcuts: Dict[str, str] = field(default_factory=dict)
    blocked_commands: List[str] = field(default_factory=list)
    
    # Statistics
    total_interactions: int = 0
    first_interaction: Optional[datetime] = None
    last_interaction: Optional[datetime] = None


@dataclass
class InteractionRecord:
    """Record of a single interaction."""
    timestamp: datetime
    utterance: str
    intent: Optional[str] = None
    response: str = ""
    command_executed: bool = False
    success: bool = True
    duration: float = 0.0
    time_of_day: str = ""
    day_of_week: int = 0


@dataclass
class LearnedPattern:
    """A learned usage pattern."""
    pattern_type: str  # "time_based", "context_based", "sequence"
    description: str
    trigger: Dict[str, Any]
    suggestion: str
    confidence: float = 0.0
    occurrences: int = 0


# ============================================
# Learning Engine
# ============================================

class VoiceLearningEngine:
    """
    Learning engine for voice assistant personalization.
    
    Tracks user behavior, learns patterns, and provides
    personalized suggestions and adaptations.
    """
    
    def __init__(self, user_id: str = "default"):
        self._user_id = user_id
        self._profile = UserProfile(user_id=user_id)
        self._history: List[InteractionRecord] = []
        self._patterns: List[LearnedPattern] = []
        
        # Data paths
        self._data_dir = Path.home() / ".cursorbot" / "learning"
        self._profile_path = self._data_dir / f"profile_{user_id}.json"
        self._history_path = self._data_dir / f"history_{user_id}.json"
        
        # Load existing data
        self._load_data()
    
    # ============================================
    # Data Persistence
    # ============================================
    
    def _load_data(self) -> None:
        """Load saved profile and history."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            
            # Load profile
            if self._profile_path.exists():
                with open(self._profile_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._profile = UserProfile(**data)
            
            # Load history (last 1000 entries)
            if self._history_path.exists():
                with open(self._history_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                    self._history = [
                        InteractionRecord(
                            timestamp=datetime.fromisoformat(r["timestamp"]),
                            **{k: v for k, v in r.items() if k != "timestamp"}
                        )
                        for r in records[-1000:]
                    ]
            
            logger.debug(f"Loaded learning data for user {self._user_id}")
            
        except Exception as e:
            logger.error(f"Error loading learning data: {e}")
    
    def _save_data(self) -> None:
        """Save profile and history."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save profile
            profile_data = {
                "user_id": self._profile.user_id,
                "name": self._profile.name,
                "preferred_language": self._profile.preferred_language,
                "preferred_voice": self._profile.preferred_voice,
                "response_style": self._profile.response_style,
                "common_commands": self._profile.common_commands,
                "common_queries": self._profile.common_queries,
                "time_patterns": self._profile.time_patterns,
                "shortcuts": self._profile.shortcuts,
                "blocked_commands": self._profile.blocked_commands,
                "total_interactions": self._profile.total_interactions,
                "first_interaction": self._profile.first_interaction.isoformat() if self._profile.first_interaction else None,
                "last_interaction": self._profile.last_interaction.isoformat() if self._profile.last_interaction else None,
            }
            
            with open(self._profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=2)
            
            # Save history (last 1000)
            history_data = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "utterance": r.utterance,
                    "intent": r.intent,
                    "response": r.response,
                    "command_executed": r.command_executed,
                    "success": r.success,
                    "duration": r.duration,
                    "time_of_day": r.time_of_day,
                    "day_of_week": r.day_of_week,
                }
                for r in self._history[-1000:]
            ]
            
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving learning data: {e}")
    
    # ============================================
    # Interaction Recording
    # ============================================
    
    async def record_interaction(
        self,
        utterance: Utterance,
        intent: Optional[Intent],
        response: str,
        command_executed: bool = False,
        success: bool = True,
        duration: float = 0.0
    ) -> None:
        """
        Record an interaction for learning.
        
        Args:
            utterance: User's spoken input
            intent: Recognized intent
            response: Assistant's response
            command_executed: Whether a command was executed
            success: Whether the interaction was successful
            duration: Duration of the interaction
        """
        now = datetime.now()
        
        # Determine time of day
        hour = now.hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        # Create record
        record = InteractionRecord(
            timestamp=now,
            utterance=utterance.text,
            intent=intent.category.value if intent else None,
            response=response,
            command_executed=command_executed,
            success=success,
            duration=duration,
            time_of_day=time_of_day,
            day_of_week=now.weekday()
        )
        
        self._history.append(record)
        
        # Update profile
        self._profile.total_interactions += 1
        self._profile.last_interaction = now
        
        if not self._profile.first_interaction:
            self._profile.first_interaction = now
        
        # Track common patterns
        self._update_patterns(utterance.text, intent, time_of_day)
        
        # Save periodically
        if self._profile.total_interactions % 10 == 0:
            self._save_data()
    
    def _update_patterns(
        self,
        text: str,
        intent: Optional[Intent],
        time_of_day: str
    ) -> None:
        """Update usage patterns."""
        # Normalize text for comparison
        normalized = text.lower().strip()
        
        # Track command frequency
        if intent and intent.category != IntentCategory.CHAT:
            cmd_key = f"{intent.category.value}:{normalized[:50]}"
            self._profile.common_commands[cmd_key] = (
                self._profile.common_commands.get(cmd_key, 0) + 1
            )
        else:
            # Track common queries
            query_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
            self._profile.common_queries[query_hash] = (
                self._profile.common_queries.get(query_hash, 0) + 1
            )
        
        # Track time-based patterns
        if time_of_day not in self._profile.time_patterns:
            self._profile.time_patterns[time_of_day] = {}
        
        intent_type = intent.category.value if intent else "chat"
        self._profile.time_patterns[time_of_day][intent_type] = (
            self._profile.time_patterns[time_of_day].get(intent_type, 0) + 1
        )
    
    # ============================================
    # Pattern Analysis
    # ============================================
    
    def analyze_patterns(self) -> List[LearnedPattern]:
        """Analyze interaction history for patterns."""
        patterns = []
        
        # Time-based patterns
        patterns.extend(self._analyze_time_patterns())
        
        # Command frequency patterns
        patterns.extend(self._analyze_command_patterns())
        
        # Sequence patterns
        patterns.extend(self._analyze_sequence_patterns())
        
        self._patterns = patterns
        return patterns
    
    def _analyze_time_patterns(self) -> List[LearnedPattern]:
        """Analyze time-based usage patterns."""
        patterns = []
        
        for time_of_day, intents in self._profile.time_patterns.items():
            total = sum(intents.values())
            if total < 5:  # Need minimum data
                continue
            
            for intent_type, count in intents.items():
                frequency = count / total
                if frequency > 0.3:  # >30% usage
                    patterns.append(LearnedPattern(
                        pattern_type="time_based",
                        description=f"You often use {intent_type} commands in the {time_of_day}",
                        trigger={"time_of_day": time_of_day},
                        suggestion=f"常用的{intent_type}功能",
                        confidence=frequency,
                        occurrences=count
                    ))
        
        return patterns
    
    def _analyze_command_patterns(self) -> List[LearnedPattern]:
        """Analyze frequently used commands."""
        patterns = []
        
        # Get top commands
        sorted_commands = sorted(
            self._profile.common_commands.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for cmd_key, count in sorted_commands:
            if count >= 3:
                parts = cmd_key.split(":", 1)
                intent_type = parts[0]
                command_text = parts[1] if len(parts) > 1 else cmd_key
                
                patterns.append(LearnedPattern(
                    pattern_type="frequency",
                    description=f"Frequently used: {command_text}",
                    trigger={"command": command_text},
                    suggestion=command_text,
                    confidence=min(count / 20, 1.0),
                    occurrences=count
                ))
        
        return patterns
    
    def _analyze_sequence_patterns(self) -> List[LearnedPattern]:
        """Analyze command sequences."""
        patterns = []
        
        if len(self._history) < 10:
            return patterns
        
        # Find common sequences (pairs)
        sequences = Counter()
        for i in range(len(self._history) - 1):
            curr = self._history[i]
            next_rec = self._history[i + 1]
            
            # Only consider sequences within 5 minutes
            time_diff = (next_rec.timestamp - curr.timestamp).total_seconds()
            if time_diff <= 300 and curr.intent and next_rec.intent:
                seq_key = f"{curr.intent}->{next_rec.intent}"
                sequences[seq_key] += 1
        
        # Add patterns for common sequences
        for seq_key, count in sequences.most_common(5):
            if count >= 3:
                intents = seq_key.split("->")
                patterns.append(LearnedPattern(
                    pattern_type="sequence",
                    description=f"Often follow {intents[0]} with {intents[1]}",
                    trigger={"previous_intent": intents[0]},
                    suggestion=f"接下來可能需要 {intents[1]}",
                    confidence=count / len(self._history),
                    occurrences=count
                ))
        
        return patterns
    
    # ============================================
    # Personalized Suggestions
    # ============================================
    
    def get_personalized_suggestions(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Get personalized suggestions based on context and history.
        
        Args:
            context: Current context (time_of_day, recent_intent, etc.)
            
        Returns:
            List of suggested commands/queries
        """
        suggestions = []
        
        # Re-analyze patterns if needed
        if not self._patterns:
            self.analyze_patterns()
        
        context = context or {}
        time_of_day = context.get("time_of_day")
        recent_intent = context.get("recent_intent")
        
        # Time-based suggestions
        if time_of_day:
            for pattern in self._patterns:
                if (pattern.pattern_type == "time_based" and 
                    pattern.trigger.get("time_of_day") == time_of_day):
                    suggestions.append(pattern.suggestion)
        
        # Sequence-based suggestions
        if recent_intent:
            for pattern in self._patterns:
                if (pattern.pattern_type == "sequence" and
                    pattern.trigger.get("previous_intent") == recent_intent):
                    suggestions.append(pattern.suggestion)
        
        # Frequency-based suggestions
        for pattern in self._patterns:
            if pattern.pattern_type == "frequency" and pattern.confidence > 0.5:
                suggestions.append(pattern.suggestion)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
        
        return unique_suggestions[:5]  # Return top 5
    
    # ============================================
    # Shortcuts
    # ============================================
    
    def add_shortcut(self, trigger: str, command: str) -> None:
        """
        Add a voice shortcut.
        
        Args:
            trigger: Short trigger phrase
            command: Full command to execute
        """
        self._profile.shortcuts[trigger.lower()] = command
        self._save_data()
    
    def remove_shortcut(self, trigger: str) -> bool:
        """Remove a shortcut."""
        trigger_lower = trigger.lower()
        if trigger_lower in self._profile.shortcuts:
            del self._profile.shortcuts[trigger_lower]
            self._save_data()
            return True
        return False
    
    def get_shortcut(self, trigger: str) -> Optional[str]:
        """Get command for a shortcut trigger."""
        return self._profile.shortcuts.get(trigger.lower())
    
    def expand_shortcuts(self, text: str) -> str:
        """Expand shortcuts in text."""
        text_lower = text.lower()
        for trigger, command in self._profile.shortcuts.items():
            if trigger in text_lower:
                return command
        return text
    
    # ============================================
    # Profile Management
    # ============================================
    
    def update_preference(self, key: str, value: Any) -> None:
        """Update a user preference."""
        if hasattr(self._profile, key):
            setattr(self._profile, key, value)
            self._save_data()
    
    def get_profile(self) -> UserProfile:
        """Get current user profile."""
        return self._profile
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_interactions": self._profile.total_interactions,
            "first_interaction": self._profile.first_interaction.isoformat() if self._profile.first_interaction else None,
            "last_interaction": self._profile.last_interaction.isoformat() if self._profile.last_interaction else None,
            "most_used_commands": sorted(
                self._profile.common_commands.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "time_patterns": self._profile.time_patterns,
            "shortcuts_count": len(self._profile.shortcuts),
            "patterns_learned": len(self._patterns),
        }
    
    def reset_learning(self) -> None:
        """Reset all learned data."""
        self._profile = UserProfile(user_id=self._user_id)
        self._history.clear()
        self._patterns.clear()
        
        # Delete files
        if self._profile_path.exists():
            self._profile_path.unlink()
        if self._history_path.exists():
            self._history_path.unlink()
        
        logger.info("Learning data reset")


# ============================================
# Adaptive Response System
# ============================================

class AdaptiveResponseSystem:
    """
    System for adapting responses based on user preferences.
    
    Adjusts:
    - Response length
    - Formality level
    - Detail level
    - Language style
    """
    
    def __init__(self, learning_engine: VoiceLearningEngine):
        self._engine = learning_engine
        self._response_feedback: Dict[str, List[bool]] = defaultdict(list)
    
    def record_feedback(self, response_id: str, positive: bool) -> None:
        """Record user feedback on a response."""
        self._response_feedback[response_id].append(positive)
    
    def adapt_response(self, response: str, context: Dict[str, Any] = None) -> str:
        """
        Adapt response based on user preferences.
        
        Args:
            response: Original response
            context: Current context
            
        Returns:
            Adapted response
        """
        profile = self._engine.get_profile()
        
        # Adapt based on style preference
        if profile.response_style == "concise":
            response = self._make_concise(response)
        elif profile.response_style == "detailed":
            response = self._add_detail(response)
        
        return response
    
    def _make_concise(self, response: str) -> str:
        """Make response more concise."""
        # Remove filler phrases
        fillers = ["我覺得", "我認為", "其實", "基本上", "說實話"]
        for filler in fillers:
            response = response.replace(filler, "")
        
        # Truncate if too long
        if len(response) > 100:
            sentences = response.split("。")
            if sentences:
                response = sentences[0] + "。"
        
        return response.strip()
    
    def _add_detail(self, response: str) -> str:
        """Add more detail to response."""
        # This would typically use LLM to expand
        return response


# ============================================
# Global Instance
# ============================================

_learning_engines: Dict[str, VoiceLearningEngine] = {}


def get_learning_engine(user_id: str = "default") -> VoiceLearningEngine:
    """Get or create a learning engine for a user."""
    global _learning_engines
    if user_id not in _learning_engines:
        _learning_engines[user_id] = VoiceLearningEngine(user_id)
    return _learning_engines[user_id]


__all__ = [
    "UserProfile",
    "InteractionRecord",
    "LearnedPattern",
    "VoiceLearningEngine",
    "AdaptiveResponseSystem",
    "get_learning_engine",
]
