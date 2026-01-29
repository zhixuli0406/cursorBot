"""
Voice Dialogue Management for CursorBot v1.1

Provides advanced dialogue features:
- Context understanding (pronoun resolution)
- Dialogue correction
- Conversation summarization
- Multi-turn dialogue tracking

Usage:
    from src.core.voice_dialogue import (
        DialogueManager,
        ContextResolver,
        ConversationSummarizer,
    )
"""

import re
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

from ..utils.logger import logger


# ============================================
# Context Understanding (Pronoun Resolution)
# ============================================

class ReferenceType(Enum):
    """Types of references."""
    PRONOUN = "pronoun"  # it, this, that
    DEMONSTRATIVE = "demonstrative"  # this one, that file
    TEMPORAL = "temporal"  # just now, before
    ELLIPSIS = "ellipsis"  # (omitted subject)


@dataclass
class Reference:
    """A reference in text."""
    text: str
    ref_type: ReferenceType
    position: int
    resolved_to: Optional[str] = None


@dataclass
class DialogueContext:
    """Context for dialogue understanding."""
    # Recent entities mentioned
    entities: Dict[str, List[str]] = field(default_factory=dict)
    # Last mentioned items by category
    last_file: Optional[str] = None
    last_function: Optional[str] = None
    last_error: Optional[str] = None
    last_command: Optional[str] = None
    last_result: Optional[str] = None
    last_topic: Optional[str] = None
    # Conversation history
    recent_utterances: List[str] = field(default_factory=list)
    # Timestamp
    last_update: datetime = field(default_factory=datetime.now)


class ContextResolver:
    """
    Resolves pronouns and references in dialogue.
    
    Examples:
    - "打開它" -> "打開 main.py" (if main.py was last mentioned)
    - "再執行一次" -> repeat last command
    - "這個錯誤" -> refers to last error
    """
    
    # Pronoun patterns for Chinese/English
    PRONOUN_PATTERNS = {
        # Chinese pronouns
        "它": ["file", "function", "result"],
        "這個": ["file", "function", "error", "result"],
        "那個": ["file", "function", "error", "result"],
        "這": ["file", "function", "topic"],
        "那": ["file", "function", "topic"],
        "剛才的": ["command", "result", "file"],
        "剛剛的": ["command", "result", "file"],
        "上一個": ["file", "function", "command"],
        "前面的": ["file", "function", "topic"],
        # English pronouns
        "it": ["file", "function", "result"],
        "this": ["file", "function", "error", "result"],
        "that": ["file", "function", "error", "result"],
        "the last one": ["command", "result", "file"],
        "previous": ["file", "function", "command"],
    }
    
    # Entity extraction patterns
    ENTITY_PATTERNS = {
        "file": [
            r"(?:檔案|文件|file)\s*[「『]?([a-zA-Z0-9_\-\.\/]+)[」』]?",
            r"([a-zA-Z0-9_\-]+\.[a-zA-Z]{2,4})",
        ],
        "function": [
            r"(?:函數|方法|function|method)\s*[「『]?(\w+)[」』]?",
            r"(\w+)\s*\(\s*\)",
        ],
        "error": [
            r"(?:錯誤|error|exception):\s*(.+)",
            r"(Error|Exception|Failed):\s*(.+)",
        ],
        "command": [
            r"(?:執行|run|execute)\s+(.+)",
        ],
    }
    
    def __init__(self):
        self._context = DialogueContext()
        self._max_history = 10
    
    def update_context(self, utterance: str, result: Optional[str] = None) -> None:
        """Update context with new utterance and result."""
        # Add to recent utterances
        self._context.recent_utterances.append(utterance)
        if len(self._context.recent_utterances) > self._max_history:
            self._context.recent_utterances.pop(0)
        
        # Extract entities
        self._extract_entities(utterance)
        
        # Update last result
        if result:
            self._context.last_result = result
        
        self._context.last_update = datetime.now()
    
    def _extract_entities(self, text: str) -> None:
        """Extract entities from text and update context."""
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Get the first group if tuple
                    value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    
                    # Update context
                    if entity_type == "file":
                        self._context.last_file = value
                    elif entity_type == "function":
                        self._context.last_function = value
                    elif entity_type == "error":
                        self._context.last_error = value
                    elif entity_type == "command":
                        self._context.last_command = value
                    
                    # Add to entities list
                    if entity_type not in self._context.entities:
                        self._context.entities[entity_type] = []
                    self._context.entities[entity_type].insert(0, value)
                    # Keep only recent entities
                    self._context.entities[entity_type] = \
                        self._context.entities[entity_type][:5]
    
    def resolve(self, text: str) -> Tuple[str, List[Reference]]:
        """
        Resolve references in text.
        
        Args:
            text: Input text with references
            
        Returns:
            (resolved_text, list of references)
        """
        references = []
        resolved_text = text
        
        for pronoun, categories in self.PRONOUN_PATTERNS.items():
            if pronoun.lower() in text.lower():
                # Find replacement
                replacement = self._find_replacement(categories)
                
                if replacement:
                    ref = Reference(
                        text=pronoun,
                        ref_type=ReferenceType.PRONOUN,
                        position=text.lower().find(pronoun.lower()),
                        resolved_to=replacement
                    )
                    references.append(ref)
                    
                    # Replace in text
                    resolved_text = re.sub(
                        re.escape(pronoun),
                        replacement,
                        resolved_text,
                        count=1,
                        flags=re.IGNORECASE
                    )
        
        return resolved_text, references
    
    def _find_replacement(self, categories: List[str]) -> Optional[str]:
        """Find replacement based on category priority."""
        for category in categories:
            if category == "file" and self._context.last_file:
                return self._context.last_file
            elif category == "function" and self._context.last_function:
                return self._context.last_function
            elif category == "error" and self._context.last_error:
                return self._context.last_error
            elif category == "command" and self._context.last_command:
                return self._context.last_command
            elif category == "result" and self._context.last_result:
                return self._context.last_result
            elif category == "topic" and self._context.last_topic:
                return self._context.last_topic
        
        return None
    
    def set_topic(self, topic: str) -> None:
        """Set current conversation topic."""
        self._context.last_topic = topic
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context."""
        return {
            "last_file": self._context.last_file,
            "last_function": self._context.last_function,
            "last_error": self._context.last_error,
            "last_command": self._context.last_command,
            "recent_entities": dict(self._context.entities),
            "utterance_count": len(self._context.recent_utterances),
        }
    
    def clear(self) -> None:
        """Clear context."""
        self._context = DialogueContext()


# ============================================
# Dialogue Correction
# ============================================

class CorrectionType(Enum):
    """Types of dialogue corrections."""
    REPLACE = "replace"  # Replace previous
    MODIFY = "modify"  # Modify previous
    CANCEL = "cancel"  # Cancel previous


@dataclass
class Correction:
    """A dialogue correction."""
    correction_type: CorrectionType
    original: str
    corrected: str
    trigger_phrase: str


class DialogueCorrector:
    """
    Handles dialogue corrections.
    
    Examples:
    - "不對，我是說..." -> Replace previous
    - "改成..." -> Modify previous
    - "取消" -> Cancel previous
    """
    
    # Correction trigger patterns
    CORRECTION_PATTERNS = {
        CorrectionType.REPLACE: [
            r"不對[，,]?\s*我是說(.+)",
            r"不是[，,]?\s*是(.+)",
            r"我的意思是(.+)",
            r"應該是(.+)",
            r"no[,]?\s*i mean(.+)",
            r"actually[,]?\s*(.+)",
            r"i meant(.+)",
        ],
        CorrectionType.MODIFY: [
            r"改成(.+)",
            r"換成(.+)",
            r"改為(.+)",
            r"change to(.+)",
            r"make it(.+)",
        ],
        CorrectionType.CANCEL: [
            r"^(取消|算了|不要了)$",
            r"^(cancel|never\s*mind|forget\s*it)$",
        ],
    }
    
    def __init__(self):
        self._last_utterance: Optional[str] = None
        self._last_result: Optional[Any] = None
        self._history: List[Tuple[str, Any]] = []
        self._max_history = 5
    
    def record(self, utterance: str, result: Any = None) -> None:
        """Record an utterance and its result."""
        if self._last_utterance:
            self._history.append((self._last_utterance, self._last_result))
            if len(self._history) > self._max_history:
                self._history.pop(0)
        
        self._last_utterance = utterance
        self._last_result = result
    
    def detect_correction(self, text: str) -> Optional[Correction]:
        """
        Detect if text is a correction.
        
        Returns:
            Correction object if detected, None otherwise
        """
        text_lower = text.lower().strip()
        
        for corr_type, patterns in self.CORRECTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    corrected = match.group(1).strip() if match.lastindex else ""
                    
                    return Correction(
                        correction_type=corr_type,
                        original=self._last_utterance or "",
                        corrected=corrected,
                        trigger_phrase=match.group(0)
                    )
        
        return None
    
    def apply_correction(self, correction: Correction) -> Tuple[str, str]:
        """
        Apply a correction.
        
        Returns:
            (new_utterance, response_message)
        """
        if correction.correction_type == CorrectionType.CANCEL:
            self._last_utterance = None
            self._last_result = None
            return "", "好的，已取消"
        
        elif correction.correction_type == CorrectionType.REPLACE:
            new_utterance = correction.corrected
            self._last_utterance = new_utterance
            return new_utterance, f"好的，理解為：{new_utterance}"
        
        elif correction.correction_type == CorrectionType.MODIFY:
            # Try to intelligently modify
            if self._last_utterance:
                # Simple replacement for now
                new_utterance = correction.corrected
            else:
                new_utterance = correction.corrected
            
            self._last_utterance = new_utterance
            return new_utterance, f"好的，已修改為：{new_utterance}"
        
        return "", "無法處理修正"
    
    def get_last_utterance(self) -> Optional[str]:
        """Get last utterance."""
        return self._last_utterance
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return len(self._history) > 0
    
    def undo(self) -> Optional[Tuple[str, Any]]:
        """Undo last utterance."""
        if self._history:
            self._last_utterance, self._last_result = self._history.pop()
            return self._last_utterance, self._last_result
        return None


# ============================================
# Conversation Summarization
# ============================================

@dataclass
class ConversationTurn:
    """A turn in the conversation."""
    role: str  # user or assistant
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    """Summary of a conversation."""
    main_topics: List[str]
    key_points: List[str]
    action_items: List[str]
    turn_count: int
    duration_minutes: int
    summary_text: str


class ConversationSummarizer:
    """
    Summarizes long conversations.
    
    Features:
    - Topic extraction
    - Key point identification
    - Action item detection
    - Automatic summarization trigger
    """
    
    # Patterns for action items
    ACTION_PATTERNS = [
        r"(?:需要|要|必須|應該|記得|提醒).{2,30}",
        r"(?:todo|action|task):\s*.+",
        r"(?:請|幫我|幫忙).{2,30}",
    ]
    
    def __init__(self, summary_threshold: int = 20):
        self._turns: List[ConversationTurn] = []
        self._summary_threshold = summary_threshold
        self._summaries: List[ConversationSummary] = []
    
    def add_turn(self, role: str, content: str, metadata: Dict = None) -> None:
        """Add a conversation turn."""
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._turns.append(turn)
        
        # Check if summary is needed
        if len(self._turns) >= self._summary_threshold:
            # Auto-summarize in background
            asyncio.create_task(self._auto_summarize())
    
    async def _auto_summarize(self) -> None:
        """Automatically summarize when threshold is reached."""
        try:
            summary = await self.summarize()
            self._summaries.append(summary)
            
            # Keep recent turns, archive the rest
            self._turns = self._turns[-5:]
            
            logger.info(f"Auto-summarized conversation: {len(summary.key_points)} key points")
        except Exception as e:
            logger.error(f"Auto-summarize error: {e}")
    
    async def summarize(self, turns: List[ConversationTurn] = None) -> ConversationSummary:
        """
        Generate conversation summary.
        
        Args:
            turns: Turns to summarize (default: all turns)
            
        Returns:
            ConversationSummary
        """
        turns = turns or self._turns
        
        if not turns:
            return ConversationSummary(
                main_topics=[],
                key_points=[],
                action_items=[],
                turn_count=0,
                duration_minutes=0,
                summary_text="沒有對話內容"
            )
        
        # Calculate duration
        duration = 0
        if len(turns) >= 2:
            duration = int((turns[-1].timestamp - turns[0].timestamp).total_seconds() / 60)
        
        # Extract topics and key points
        main_topics = self._extract_topics(turns)
        key_points = self._extract_key_points(turns)
        action_items = self._extract_action_items(turns)
        
        # Generate summary text
        summary_text = await self._generate_summary_text(turns, main_topics)
        
        return ConversationSummary(
            main_topics=main_topics,
            key_points=key_points,
            action_items=action_items,
            turn_count=len(turns),
            duration_minutes=duration,
            summary_text=summary_text
        )
    
    def _extract_topics(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract main topics from conversation."""
        # Combine all content
        all_text = " ".join(t.content for t in turns)
        
        # Topic keywords (simplified extraction)
        topic_patterns = [
            r"關於(.{2,10})",
            r"(.{2,10})的問題",
            r"如何(.{2,10})",
            r"什麼是(.{2,10})",
        ]
        
        topics = []
        for pattern in topic_patterns:
            matches = re.findall(pattern, all_text)
            topics.extend(matches[:2])  # Limit per pattern
        
        # Deduplicate and limit
        unique_topics = list(dict.fromkeys(topics))[:5]
        
        return unique_topics if unique_topics else ["一般對話"]
    
    def _extract_key_points(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract key points from conversation."""
        key_points = []
        
        # Look for assistant responses with conclusions
        for turn in turns:
            if turn.role == "assistant":
                content = turn.content
                
                # Look for conclusion markers
                markers = ["總結", "結論", "簡單說", "所以", "因此", "summary", "conclusion"]
                for marker in markers:
                    if marker in content.lower():
                        # Extract the sentence containing the marker
                        sentences = re.split(r'[。！？.!?]', content)
                        for sent in sentences:
                            if marker in sent.lower() and len(sent) > 10:
                                key_points.append(sent.strip()[:100])
                                break
        
        return key_points[:5]
    
    def _extract_action_items(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract action items from conversation."""
        action_items = []
        
        all_text = " ".join(t.content for t in turns)
        
        for pattern in self.ACTION_PATTERNS:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            action_items.extend(matches[:3])
        
        return list(dict.fromkeys(action_items))[:5]
    
    async def _generate_summary_text(
        self,
        turns: List[ConversationTurn],
        topics: List[str]
    ) -> str:
        """Generate summary text using LLM."""
        if len(turns) < 3:
            return f"簡短對話，主題：{', '.join(topics) if topics else '無'}"
        
        try:
            from .llm_providers import get_llm_manager
            
            llm = get_llm_manager()
            
            # Prepare conversation text
            conv_text = "\n".join([
                f"{t.role}: {t.content[:100]}"
                for t in turns[-10:]  # Last 10 turns
            ])
            
            prompt = f"""請為以下對話生成簡潔摘要（繁體中文，50字以內）：

{conv_text}

摘要："""
            
            result = await llm.generate(prompt=prompt, max_tokens=100)
            return result.strip()
            
        except Exception as e:
            logger.debug(f"Summary generation error: {e}")
            
            # Fallback
            topic_str = "、".join(topics) if topics else "一般"
            return f"共 {len(turns)} 輪對話，主題：{topic_str}"
    
    def get_recent_turns(self, count: int = 5) -> List[ConversationTurn]:
        """Get recent conversation turns."""
        return self._turns[-count:]
    
    def get_all_summaries(self) -> List[ConversationSummary]:
        """Get all generated summaries."""
        return self._summaries
    
    def clear(self) -> None:
        """Clear conversation history."""
        self._turns = []


# ============================================
# Multi-Language Intent Support
# ============================================

class MultiLanguageIntent:
    """
    Handles multi-language mixed input.
    
    Supports Chinese/English/Japanese mixed commands.
    """
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "zh": r"[\u4e00-\u9fff]",
        "ja": r"[\u3040-\u309f\u30a0-\u30ff]",
        "ko": r"[\uac00-\ud7af]",
        "en": r"[a-zA-Z]{2,}",
    }
    
    # Intent mappings across languages
    INTENT_MAPPINGS = {
        "open": {
            "zh": ["打開", "開啟", "執行"],
            "en": ["open", "launch", "run", "execute"],
            "ja": ["開く", "起動"],
        },
        "close": {
            "zh": ["關閉", "關掉", "結束"],
            "en": ["close", "quit", "exit", "terminate"],
            "ja": ["閉じる", "終了"],
        },
        "search": {
            "zh": ["搜尋", "查找", "找"],
            "en": ["search", "find", "look for"],
            "ja": ["検索", "探す"],
        },
        "create": {
            "zh": ["新建", "創建", "建立"],
            "en": ["create", "new", "make"],
            "ja": ["作成", "新規"],
        },
        "delete": {
            "zh": ["刪除", "移除", "刪掉"],
            "en": ["delete", "remove", "erase"],
            "ja": ["削除", "消す"],
        },
        "help": {
            "zh": ["幫助", "說明", "怎麼"],
            "en": ["help", "how to", "what is"],
            "ja": ["ヘルプ", "助けて"],
        },
    }
    
    def __init__(self):
        self._compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile intent patterns."""
        for intent, lang_patterns in self.INTENT_MAPPINGS.items():
            all_patterns = []
            for patterns in lang_patterns.values():
                all_patterns.extend(patterns)
            
            # Create regex pattern
            pattern = r"(" + "|".join(re.escape(p) for p in all_patterns) + r")"
            self._compiled_patterns[intent] = re.compile(pattern, re.IGNORECASE)
    
    def detect_languages(self, text: str) -> List[str]:
        """Detect languages in text."""
        detected = []
        
        for lang, pattern in self.LANGUAGE_PATTERNS.items():
            if re.search(pattern, text):
                detected.append(lang)
        
        return detected
    
    def normalize_intent(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Normalize multi-language input to standard intent.
        
        Returns:
            (normalized_text, detected_intent)
        """
        # Detect intent
        detected_intent = None
        
        for intent, pattern in self._compiled_patterns.items():
            if pattern.search(text):
                detected_intent = intent
                break
        
        return text, detected_intent
    
    def translate_command(self, text: str, target_lang: str = "zh") -> str:
        """
        Translate command keywords to target language.
        
        Basic translation of common command words.
        """
        result = text
        
        for intent, lang_patterns in self.INTENT_MAPPINGS.items():
            target_word = lang_patterns.get(target_lang, [""])[0]
            
            for lang, patterns in lang_patterns.items():
                if lang == target_lang:
                    continue
                
                for pattern in patterns:
                    result = re.sub(
                        re.escape(pattern),
                        target_word,
                        result,
                        flags=re.IGNORECASE
                    )
        
        return result


# ============================================
# Integrated Dialogue Manager
# ============================================

class DialogueManager:
    """
    Central dialogue management.
    
    Integrates all dialogue features:
    - Context resolution
    - Correction handling
    - Summarization
    - Multi-language support
    """
    
    def __init__(self):
        self.context_resolver = ContextResolver()
        self.corrector = DialogueCorrector()
        self.summarizer = ConversationSummarizer()
        self.multi_lang = MultiLanguageIntent()
    
    async def process(self, utterance: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process an utterance through all dialogue features.
        
        Args:
            utterance: User's input
            
        Returns:
            (processed_utterance, metadata)
        """
        metadata = {
            "original": utterance,
            "languages": [],
            "corrections": None,
            "references": [],
            "intent": None,
        }
        
        # 1. Detect languages
        metadata["languages"] = self.multi_lang.detect_languages(utterance)
        
        # 2. Check for corrections
        correction = self.corrector.detect_correction(utterance)
        if correction:
            metadata["corrections"] = {
                "type": correction.correction_type.value,
                "original": correction.original,
            }
            
            if correction.correction_type == CorrectionType.CANCEL:
                return "", metadata
            
            utterance, _ = self.corrector.apply_correction(correction)
        
        # 3. Normalize multi-language intent
        utterance, intent = self.multi_lang.normalize_intent(utterance)
        metadata["intent"] = intent
        
        # 4. Resolve context references
        utterance, references = self.context_resolver.resolve(utterance)
        metadata["references"] = [
            {"text": r.text, "resolved_to": r.resolved_to}
            for r in references
        ]
        
        # 5. Update context
        self.context_resolver.update_context(utterance)
        
        # 6. Record for correction tracking
        self.corrector.record(utterance)
        
        # 7. Add to conversation
        self.summarizer.add_turn("user", utterance)
        
        return utterance, metadata
    
    def record_response(self, response: str) -> None:
        """Record assistant's response."""
        self.summarizer.add_turn("assistant", response)
        self.context_resolver.update_context(response, result=response)
    
    async def get_summary(self) -> ConversationSummary:
        """Get conversation summary."""
        return await self.summarizer.summarize()
    
    def get_context(self) -> Dict[str, Any]:
        """Get current dialogue context."""
        return self.context_resolver.get_context_summary()
    
    def clear(self) -> None:
        """Clear all dialogue state."""
        self.context_resolver.clear()
        self.summarizer.clear()


# ============================================
# Global Instance
# ============================================

_dialogue_manager: Optional[DialogueManager] = None


def get_dialogue_manager() -> DialogueManager:
    global _dialogue_manager
    if _dialogue_manager is None:
        _dialogue_manager = DialogueManager()
    return _dialogue_manager


__all__ = [
    # Context
    "ContextResolver",
    "DialogueContext",
    "Reference",
    "ReferenceType",
    # Correction
    "DialogueCorrector",
    "Correction",
    "CorrectionType",
    # Summary
    "ConversationSummarizer",
    "ConversationTurn",
    "ConversationSummary",
    # Multi-language
    "MultiLanguageIntent",
    # Manager
    "DialogueManager",
    "get_dialogue_manager",
]
