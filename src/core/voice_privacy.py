"""
Voice Privacy and Personalization for CursorBot v1.1

Provides:
- Personal vocabulary management
- Privacy controls
- Data retention policies
- User consent management

Usage:
    from src.core.voice_privacy import (
        PrivacyManager,
        VocabularyManager,
        ConsentManager,
    )
"""

import json
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import re

from ..utils.logger import logger


# ============================================
# Privacy Controls
# ============================================

class DataCategory(Enum):
    """Categories of user data."""
    VOICE_RECORDINGS = "voice_recordings"
    CONVERSATION_HISTORY = "conversation_history"
    COMMAND_HISTORY = "command_history"
    LOCATION_DATA = "location_data"
    USAGE_PATTERNS = "usage_patterns"
    PERSONAL_VOCABULARY = "personal_vocabulary"
    PREFERENCES = "preferences"
    CALENDAR_DATA = "calendar_data"
    CONTACTS = "contacts"


class RetentionPeriod(Enum):
    """Data retention periods."""
    SESSION_ONLY = "session"  # Delete on session end
    ONE_DAY = "1_day"
    ONE_WEEK = "1_week"
    ONE_MONTH = "1_month"
    ONE_YEAR = "1_year"
    FOREVER = "forever"
    
    def to_days(self) -> Optional[int]:
        mapping = {
            RetentionPeriod.SESSION_ONLY: 0,
            RetentionPeriod.ONE_DAY: 1,
            RetentionPeriod.ONE_WEEK: 7,
            RetentionPeriod.ONE_MONTH: 30,
            RetentionPeriod.ONE_YEAR: 365,
            RetentionPeriod.FOREVER: None,
        }
        return mapping.get(self)


@dataclass
class PrivacySettings:
    """User's privacy settings."""
    # What data to collect
    collect_voice: bool = False
    collect_history: bool = True
    collect_location: bool = False
    collect_usage: bool = True
    
    # Retention policies
    voice_retention: RetentionPeriod = RetentionPeriod.SESSION_ONLY
    history_retention: RetentionPeriod = RetentionPeriod.ONE_WEEK
    location_retention: RetentionPeriod = RetentionPeriod.SESSION_ONLY
    usage_retention: RetentionPeriod = RetentionPeriod.ONE_MONTH
    
    # Processing preferences
    allow_cloud_processing: bool = True
    allow_learning: bool = True
    anonymize_data: bool = True
    
    # Sharing
    share_analytics: bool = False


@dataclass
class ConsentRecord:
    """Record of user consent."""
    category: DataCategory
    granted: bool
    timestamp: datetime
    purpose: str
    expires: Optional[datetime] = None


class PrivacyManager:
    """
    Manages user privacy settings and data.
    
    Features:
    - Privacy settings management
    - Data retention enforcement
    - Data export
    - Data deletion
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._settings = PrivacySettings()
        self._data_path = Path.home() / ".cursorbot" / "privacy"
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load privacy settings from disk."""
        settings_file = self._data_path / f"{self.user_id}_settings.json"
        
        try:
            if settings_file.exists():
                with open(settings_file, "r") as f:
                    data = json.load(f)
                
                self._settings = PrivacySettings(
                    collect_voice=data.get("collect_voice", False),
                    collect_history=data.get("collect_history", True),
                    collect_location=data.get("collect_location", False),
                    collect_usage=data.get("collect_usage", True),
                    voice_retention=RetentionPeriod(data.get("voice_retention", "session")),
                    history_retention=RetentionPeriod(data.get("history_retention", "1_week")),
                    location_retention=RetentionPeriod(data.get("location_retention", "session")),
                    usage_retention=RetentionPeriod(data.get("usage_retention", "1_month")),
                    allow_cloud_processing=data.get("allow_cloud_processing", True),
                    allow_learning=data.get("allow_learning", True),
                    anonymize_data=data.get("anonymize_data", True),
                    share_analytics=data.get("share_analytics", False),
                )
        except Exception as e:
            logger.debug(f"Could not load privacy settings: {e}")
    
    def _save_settings(self) -> None:
        """Save privacy settings to disk."""
        settings_file = self._data_path / f"{self.user_id}_settings.json"
        
        try:
            data = {
                "collect_voice": self._settings.collect_voice,
                "collect_history": self._settings.collect_history,
                "collect_location": self._settings.collect_location,
                "collect_usage": self._settings.collect_usage,
                "voice_retention": self._settings.voice_retention.value,
                "history_retention": self._settings.history_retention.value,
                "location_retention": self._settings.location_retention.value,
                "usage_retention": self._settings.usage_retention.value,
                "allow_cloud_processing": self._settings.allow_cloud_processing,
                "allow_learning": self._settings.allow_learning,
                "anonymize_data": self._settings.anonymize_data,
                "share_analytics": self._settings.share_analytics,
            }
            
            with open(settings_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save privacy settings: {e}")
    
    @property
    def settings(self) -> PrivacySettings:
        return self._settings
    
    def update_settings(self, **kwargs) -> None:
        """Update privacy settings."""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        
        self._save_settings()
    
    def can_collect(self, category: DataCategory) -> bool:
        """Check if data collection is allowed for category."""
        mapping = {
            DataCategory.VOICE_RECORDINGS: self._settings.collect_voice,
            DataCategory.CONVERSATION_HISTORY: self._settings.collect_history,
            DataCategory.COMMAND_HISTORY: self._settings.collect_history,
            DataCategory.LOCATION_DATA: self._settings.collect_location,
            DataCategory.USAGE_PATTERNS: self._settings.collect_usage,
            DataCategory.PERSONAL_VOCABULARY: self._settings.allow_learning,
            DataCategory.PREFERENCES: True,  # Always allow
            DataCategory.CALENDAR_DATA: self._settings.collect_history,
            DataCategory.CONTACTS: False,  # Never collect by default
        }
        return mapping.get(category, False)
    
    def get_retention_days(self, category: DataCategory) -> Optional[int]:
        """Get retention period in days for category."""
        mapping = {
            DataCategory.VOICE_RECORDINGS: self._settings.voice_retention,
            DataCategory.CONVERSATION_HISTORY: self._settings.history_retention,
            DataCategory.COMMAND_HISTORY: self._settings.history_retention,
            DataCategory.LOCATION_DATA: self._settings.location_retention,
            DataCategory.USAGE_PATTERNS: self._settings.usage_retention,
        }
        
        period = mapping.get(category, RetentionPeriod.ONE_WEEK)
        return period.to_days()
    
    def anonymize(self, data: str) -> str:
        """Anonymize sensitive data."""
        if not self._settings.anonymize_data:
            return data
        
        # Patterns for sensitive data
        patterns = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
            (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD]"),
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]"),
            (r"/Users/[^/\s]+", "/Users/[USER]"),
        ]
        
        result = data
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def export_data(self) -> Dict[str, Any]:
        """Export all user data."""
        export = {
            "user_id": self.user_id,
            "exported_at": datetime.now().isoformat(),
            "settings": {
                "collect_voice": self._settings.collect_voice,
                "collect_history": self._settings.collect_history,
                "collect_location": self._settings.collect_location,
                "allow_learning": self._settings.allow_learning,
            },
            "data": {}
        }
        
        # Collect data from various sources
        data_dir = Path.home() / ".cursorbot"
        
        # Voice prints
        vp_dir = data_dir / "voiceprints"
        if vp_dir.exists():
            export["data"]["voice_prints"] = [
                f.name for f in vp_dir.glob(f"{self.user_id}*.json")
            ]
        
        # Learning data
        learn_file = data_dir / "learning" / f"{self.user_id}.json"
        if learn_file.exists():
            with open(learn_file, "r") as f:
                export["data"]["learning"] = json.load(f)
        
        return export
    
    def delete_all_data(self) -> bool:
        """Delete all user data (right to be forgotten)."""
        try:
            data_dir = Path.home() / ".cursorbot"
            
            # Delete user-specific files
            patterns = [
                f"voiceprints/{self.user_id}*.json",
                f"learning/{self.user_id}*.json",
                f"privacy/{self.user_id}*.json",
                f"vocabulary/{self.user_id}*.json",
            ]
            
            for pattern in patterns:
                for file in data_dir.glob(pattern):
                    file.unlink()
                    logger.info(f"Deleted: {file}")
            
            return True
        except Exception as e:
            logger.error(f"Delete data error: {e}")
            return False
    
    def get_privacy_summary(self) -> str:
        """Get human-readable privacy summary."""
        lines = [
            "隱私設定摘要：",
            f"- 語音收集：{'開啟' if self._settings.collect_voice else '關閉'}",
            f"- 歷史記錄：{'開啟' if self._settings.collect_history else '關閉'}",
            f"- 位置資料：{'開啟' if self._settings.collect_location else '關閉'}",
            f"- 使用分析：{'開啟' if self._settings.collect_usage else '關閉'}",
            f"- 雲端處理：{'允許' if self._settings.allow_cloud_processing else '僅本地'}",
            f"- 智慧學習：{'開啟' if self._settings.allow_learning else '關閉'}",
            f"- 資料匿名：{'開啟' if self._settings.anonymize_data else '關閉'}",
        ]
        return "\n".join(lines)


# ============================================
# Personal Vocabulary
# ============================================

@dataclass
class VocabularyEntry:
    """A vocabulary entry."""
    term: str
    pronunciation: Optional[str] = None
    meaning: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    category: str = "general"
    frequency: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class VocabularyManager:
    """
    Manages user's personal vocabulary.
    
    Features:
    - Custom terms and pronunciations
    - Abbreviations and aliases
    - Technical jargon
    - Auto-learning from usage
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._entries: Dict[str, VocabularyEntry] = {}
        self._data_path = Path.home() / ".cursorbot" / "vocabulary"
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._load()
    
    def _load(self) -> None:
        """Load vocabulary from disk."""
        vocab_file = self._data_path / f"{self.user_id}.json"
        
        try:
            if vocab_file.exists():
                with open(vocab_file, "r") as f:
                    data = json.load(f)
                
                for term, entry_data in data.get("entries", {}).items():
                    self._entries[term.lower()] = VocabularyEntry(
                        term=entry_data["term"],
                        pronunciation=entry_data.get("pronunciation"),
                        meaning=entry_data.get("meaning"),
                        aliases=entry_data.get("aliases", []),
                        category=entry_data.get("category", "general"),
                        frequency=entry_data.get("frequency", 0),
                        created_at=datetime.fromisoformat(
                            entry_data.get("created_at", datetime.now().isoformat())
                        ),
                    )
        except Exception as e:
            logger.debug(f"Could not load vocabulary: {e}")
    
    def _save(self) -> None:
        """Save vocabulary to disk."""
        vocab_file = self._data_path / f"{self.user_id}.json"
        
        try:
            data = {
                "entries": {
                    term: {
                        "term": entry.term,
                        "pronunciation": entry.pronunciation,
                        "meaning": entry.meaning,
                        "aliases": entry.aliases,
                        "category": entry.category,
                        "frequency": entry.frequency,
                        "created_at": entry.created_at.isoformat(),
                    }
                    for term, entry in self._entries.items()
                }
            }
            
            with open(vocab_file, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Could not save vocabulary: {e}")
    
    def add(
        self,
        term: str,
        pronunciation: Optional[str] = None,
        meaning: Optional[str] = None,
        aliases: List[str] = None,
        category: str = "general"
    ) -> VocabularyEntry:
        """Add a vocabulary entry."""
        entry = VocabularyEntry(
            term=term,
            pronunciation=pronunciation,
            meaning=meaning,
            aliases=aliases or [],
            category=category,
        )
        
        self._entries[term.lower()] = entry
        
        # Also index by aliases
        for alias in entry.aliases:
            self._entries[alias.lower()] = entry
        
        self._save()
        return entry
    
    def get(self, term: str) -> Optional[VocabularyEntry]:
        """Get a vocabulary entry."""
        return self._entries.get(term.lower())
    
    def remove(self, term: str) -> bool:
        """Remove a vocabulary entry."""
        term_lower = term.lower()
        
        if term_lower in self._entries:
            entry = self._entries[term_lower]
            
            # Remove main entry and aliases
            del self._entries[term_lower]
            for alias in entry.aliases:
                if alias.lower() in self._entries:
                    del self._entries[alias.lower()]
            
            self._save()
            return True
        
        return False
    
    def record_usage(self, term: str) -> None:
        """Record term usage (for frequency tracking)."""
        term_lower = term.lower()
        
        if term_lower in self._entries:
            self._entries[term_lower].frequency += 1
            self._save()
    
    def expand_text(self, text: str) -> str:
        """Expand abbreviations and aliases in text."""
        result = text
        
        for entry in self._entries.values():
            # Expand aliases to main term
            for alias in entry.aliases:
                pattern = r"\b" + re.escape(alias) + r"\b"
                result = re.sub(pattern, entry.term, result, flags=re.IGNORECASE)
        
        return result
    
    def get_pronunciation(self, term: str) -> Optional[str]:
        """Get pronunciation for a term."""
        entry = self.get(term)
        return entry.pronunciation if entry else None
    
    def search(self, query: str) -> List[VocabularyEntry]:
        """Search vocabulary entries."""
        query_lower = query.lower()
        
        results = []
        seen = set()
        
        for entry in self._entries.values():
            if entry.term in seen:
                continue
            
            if (query_lower in entry.term.lower() or
                query_lower in (entry.meaning or "").lower() or
                any(query_lower in a.lower() for a in entry.aliases)):
                results.append(entry)
                seen.add(entry.term)
        
        return sorted(results, key=lambda e: e.frequency, reverse=True)
    
    def get_by_category(self, category: str) -> List[VocabularyEntry]:
        """Get entries by category."""
        seen = set()
        results = []
        
        for entry in self._entries.values():
            if entry.term in seen:
                continue
            
            if entry.category == category:
                results.append(entry)
                seen.add(entry.term)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vocabulary statistics."""
        unique_entries = set(e.term for e in self._entries.values())
        categories = {}
        
        for entry in self._entries.values():
            if entry.term in unique_entries:
                cat = entry.category
                categories[cat] = categories.get(cat, 0) + 1
                unique_entries.discard(entry.term)
        
        return {
            "total_entries": len(set(e.term for e in self._entries.values())),
            "total_aliases": sum(len(e.aliases) for e in self._entries.values()),
            "categories": categories,
            "most_used": sorted(
                self._entries.values(),
                key=lambda e: e.frequency,
                reverse=True
            )[:5],
        }
    
    def import_from_dict(self, data: Dict[str, str]) -> int:
        """Import vocabulary from a dictionary."""
        count = 0
        
        for term, meaning in data.items():
            self.add(term=term, meaning=meaning)
            count += 1
        
        return count
    
    def export_to_dict(self) -> Dict[str, Dict]:
        """Export vocabulary to dictionary."""
        seen = set()
        result = {}
        
        for entry in self._entries.values():
            if entry.term in seen:
                continue
            
            result[entry.term] = {
                "pronunciation": entry.pronunciation,
                "meaning": entry.meaning,
                "aliases": entry.aliases,
                "category": entry.category,
            }
            seen.add(entry.term)
        
        return result


# ============================================
# Consent Management
# ============================================

class ConsentManager:
    """
    Manages user consent for various features.
    
    Ensures GDPR/privacy compliance.
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._consents: Dict[DataCategory, ConsentRecord] = {}
        self._data_path = Path.home() / ".cursorbot" / "consent"
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._load()
    
    def _load(self) -> None:
        """Load consent records."""
        consent_file = self._data_path / f"{self.user_id}.json"
        
        try:
            if consent_file.exists():
                with open(consent_file, "r") as f:
                    data = json.load(f)
                
                for cat_str, record_data in data.items():
                    cat = DataCategory(cat_str)
                    expires = None
                    if record_data.get("expires"):
                        expires = datetime.fromisoformat(record_data["expires"])
                    
                    self._consents[cat] = ConsentRecord(
                        category=cat,
                        granted=record_data["granted"],
                        timestamp=datetime.fromisoformat(record_data["timestamp"]),
                        purpose=record_data["purpose"],
                        expires=expires,
                    )
        except Exception as e:
            logger.debug(f"Could not load consent: {e}")
    
    def _save(self) -> None:
        """Save consent records."""
        consent_file = self._data_path / f"{self.user_id}.json"
        
        try:
            data = {
                cat.value: {
                    "granted": record.granted,
                    "timestamp": record.timestamp.isoformat(),
                    "purpose": record.purpose,
                    "expires": record.expires.isoformat() if record.expires else None,
                }
                for cat, record in self._consents.items()
            }
            
            with open(consent_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save consent: {e}")
    
    def request_consent(
        self,
        category: DataCategory,
        purpose: str,
        expires_days: Optional[int] = None
    ) -> str:
        """
        Generate a consent request message.
        
        Returns message to show user.
        """
        category_names = {
            DataCategory.VOICE_RECORDINGS: "語音錄音",
            DataCategory.CONVERSATION_HISTORY: "對話記錄",
            DataCategory.COMMAND_HISTORY: "指令歷史",
            DataCategory.LOCATION_DATA: "位置資料",
            DataCategory.USAGE_PATTERNS: "使用模式",
            DataCategory.PERSONAL_VOCABULARY: "個人詞彙",
            DataCategory.PREFERENCES: "偏好設定",
            DataCategory.CALENDAR_DATA: "日曆資料",
            DataCategory.CONTACTS: "聯絡人",
        }
        
        name = category_names.get(category, category.value)
        
        message = f"是否允許收集「{name}」？\n"
        message += f"用途：{purpose}\n"
        
        if expires_days:
            message += f"有效期：{expires_days} 天\n"
        
        message += "回覆「同意」或「拒絕」"
        
        return message
    
    def grant(
        self,
        category: DataCategory,
        purpose: str,
        expires_days: Optional[int] = None
    ) -> None:
        """Grant consent for a category."""
        expires = None
        if expires_days:
            expires = datetime.now() + timedelta(days=expires_days)
        
        self._consents[category] = ConsentRecord(
            category=category,
            granted=True,
            timestamp=datetime.now(),
            purpose=purpose,
            expires=expires,
        )
        
        self._save()
    
    def revoke(self, category: DataCategory) -> None:
        """Revoke consent for a category."""
        if category in self._consents:
            self._consents[category].granted = False
            self._consents[category].timestamp = datetime.now()
            self._save()
    
    def check(self, category: DataCategory) -> bool:
        """Check if consent is granted and valid."""
        if category not in self._consents:
            return False
        
        record = self._consents[category]
        
        if not record.granted:
            return False
        
        # Check expiration
        if record.expires and datetime.now() > record.expires:
            record.granted = False
            self._save()
            return False
        
        return True
    
    def get_all_consents(self) -> List[ConsentRecord]:
        """Get all consent records."""
        return list(self._consents.values())
    
    def get_summary(self) -> str:
        """Get human-readable consent summary."""
        lines = ["資料使用同意狀態："]
        
        for cat in DataCategory:
            record = self._consents.get(cat)
            
            if record:
                status = "已同意" if record.granted else "已拒絕"
                if record.expires:
                    status += f" (至 {record.expires.strftime('%Y-%m-%d')})"
            else:
                status = "未詢問"
            
            lines.append(f"- {cat.value}: {status}")
        
        return "\n".join(lines)


# ============================================
# Global Instances
# ============================================

_privacy_manager: Optional[PrivacyManager] = None
_vocabulary_manager: Optional[VocabularyManager] = None
_consent_manager: Optional[ConsentManager] = None


def get_privacy_manager(user_id: str = "default") -> PrivacyManager:
    global _privacy_manager
    if _privacy_manager is None or _privacy_manager.user_id != user_id:
        _privacy_manager = PrivacyManager(user_id)
    return _privacy_manager


def get_vocabulary_manager(user_id: str = "default") -> VocabularyManager:
    global _vocabulary_manager
    if _vocabulary_manager is None or _vocabulary_manager.user_id != user_id:
        _vocabulary_manager = VocabularyManager(user_id)
    return _vocabulary_manager


def get_consent_manager(user_id: str = "default") -> ConsentManager:
    global _consent_manager
    if _consent_manager is None or _consent_manager.user_id != user_id:
        _consent_manager = ConsentManager(user_id)
    return _consent_manager


__all__ = [
    # Privacy
    "PrivacyManager",
    "PrivacySettings",
    "DataCategory",
    "RetentionPeriod",
    "get_privacy_manager",
    # Vocabulary
    "VocabularyManager",
    "VocabularyEntry",
    "get_vocabulary_manager",
    # Consent
    "ConsentManager",
    "ConsentRecord",
    "get_consent_manager",
]
