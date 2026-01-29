"""
Advanced Voice Features for CursorBot v1.1

Provides advanced voice capabilities:
- Voice print recognition (speaker identification)
- Emotion-aware TTS
- Voice interruption handling
- Meeting assistant
- IDE voice navigation
- Offline TTS (Piper)
- Multi-language response

Usage:
    from src.core.voice_advanced import (
        VoicePrintManager,
        EmotionTTS,
        MeetingAssistant,
        VoiceNavigator,
    )
"""

import os
import asyncio
import hashlib
import json
import struct
import wave
import tempfile
import subprocess
import platform
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import math

from ..utils.logger import logger


# ============================================
# Voice Print Recognition
# ============================================

class VoicePrintStatus(Enum):
    """Voice print status."""
    NOT_ENROLLED = "not_enrolled"
    ENROLLED = "enrolled"
    VERIFIED = "verified"
    REJECTED = "rejected"


@dataclass
class VoicePrint:
    """User voice print data."""
    user_id: str
    name: str
    features: List[float] = field(default_factory=list)
    samples_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_verified: Optional[datetime] = None


@dataclass
class VoicePrintConfig:
    """Voice print configuration."""
    min_samples: int = 3  # Minimum samples for enrollment
    similarity_threshold: float = 0.7  # Threshold for verification
    sample_duration: float = 3.0  # Seconds per sample
    feature_size: int = 128  # Feature vector size


class VoicePrintManager:
    """
    Manages voice print enrollment and verification.
    
    Uses audio features to identify speakers.
    """
    
    def __init__(self, config: VoicePrintConfig = None):
        self.config = config or VoicePrintConfig()
        self._voice_prints: Dict[str, VoicePrint] = {}
        self._data_path = Path.home() / ".cursorbot" / "voiceprints"
        self._load_voice_prints()
    
    def _load_voice_prints(self) -> None:
        """Load saved voice prints."""
        try:
            self._data_path.mkdir(parents=True, exist_ok=True)
            
            for file in self._data_path.glob("*.json"):
                with open(file, "r") as f:
                    data = json.load(f)
                    vp = VoicePrint(
                        user_id=data["user_id"],
                        name=data["name"],
                        features=data["features"],
                        samples_count=data["samples_count"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                    )
                    self._voice_prints[vp.user_id] = vp
        except Exception as e:
            logger.debug(f"Could not load voice prints: {e}")
    
    def _save_voice_print(self, vp: VoicePrint) -> None:
        """Save a voice print."""
        try:
            self._data_path.mkdir(parents=True, exist_ok=True)
            
            data = {
                "user_id": vp.user_id,
                "name": vp.name,
                "features": vp.features,
                "samples_count": vp.samples_count,
                "created_at": vp.created_at.isoformat(),
            }
            
            with open(self._data_path / f"{vp.user_id}.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Could not save voice print: {e}")
    
    def extract_features(self, audio_data: bytes) -> List[float]:
        """
        Extract voice features from audio.
        
        Uses simple MFCC-like features for speaker identification.
        """
        # Convert bytes to samples
        samples = struct.unpack(f"{len(audio_data) // 2}h", audio_data)
        
        if len(samples) < 1000:
            return []
        
        # Normalize
        max_val = max(abs(s) for s in samples) or 1
        normalized = [s / max_val for s in samples]
        
        # Extract basic features
        features = []
        
        # Frame-based features
        frame_size = len(normalized) // 16
        for i in range(16):
            frame = normalized[i * frame_size:(i + 1) * frame_size]
            if not frame:
                continue
            
            # Energy
            energy = sum(s * s for s in frame) / len(frame)
            features.append(energy)
            
            # Zero crossing rate
            zcr = sum(1 for j in range(1, len(frame)) if frame[j] * frame[j-1] < 0)
            features.append(zcr / len(frame))
            
            # Spectral centroid (simplified)
            if len(frame) > 0:
                centroid = sum(abs(s) * i for i, s in enumerate(frame)) / (sum(abs(s) for s in frame) or 1)
                features.append(centroid / len(frame))
            
            # Peak amplitude
            peak = max(abs(s) for s in frame)
            features.append(peak)
        
        # Statistical features
        features.extend([
            sum(normalized) / len(normalized),  # Mean
            max(normalized) - min(normalized),   # Range
            sum((s - features[-2]) ** 2 for s in normalized) / len(normalized),  # Variance
        ])
        
        # Pad or truncate to fixed size
        if len(features) < self.config.feature_size:
            features.extend([0] * (self.config.feature_size - len(features)))
        else:
            features = features[:self.config.feature_size]
        
        return features
    
    def compute_similarity(self, features1: List[float], features2: List[float]) -> float:
        """Compute cosine similarity between feature vectors."""
        if not features1 or not features2 or len(features1) != len(features2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(features1, features2))
        norm1 = math.sqrt(sum(a * a for a in features1))
        norm2 = math.sqrt(sum(b * b for b in features2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def enroll(self, user_id: str, name: str, audio_samples: List[bytes]) -> Tuple[bool, str]:
        """
        Enroll a new user's voice print.
        
        Args:
            user_id: User identifier
            name: User name
            audio_samples: List of audio samples
            
        Returns:
            (success, message)
        """
        if len(audio_samples) < self.config.min_samples:
            return False, f"需要至少 {self.config.min_samples} 個語音樣本"
        
        # Extract features from all samples
        all_features = []
        for sample in audio_samples:
            features = self.extract_features(sample)
            if features:
                all_features.append(features)
        
        if len(all_features) < self.config.min_samples:
            return False, "語音樣本品質不足，請重新錄製"
        
        # Average features
        avg_features = []
        for i in range(self.config.feature_size):
            avg = sum(f[i] for f in all_features) / len(all_features)
            avg_features.append(avg)
        
        # Create voice print
        vp = VoicePrint(
            user_id=user_id,
            name=name,
            features=avg_features,
            samples_count=len(all_features),
        )
        
        self._voice_prints[user_id] = vp
        self._save_voice_print(vp)
        
        return True, f"成功註冊 {name} 的聲紋"
    
    async def verify(self, audio_data: bytes) -> Tuple[Optional[str], float]:
        """
        Verify speaker from audio.
        
        Args:
            audio_data: Audio sample
            
        Returns:
            (user_id or None, similarity score)
        """
        features = self.extract_features(audio_data)
        if not features:
            return None, 0.0
        
        best_match = None
        best_similarity = 0.0
        
        for user_id, vp in self._voice_prints.items():
            similarity = self.compute_similarity(features, vp.features)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = user_id
        
        if best_similarity >= self.config.similarity_threshold:
            if best_match and best_match in self._voice_prints:
                self._voice_prints[best_match].last_verified = datetime.now()
            return best_match, best_similarity
        
        return None, best_similarity
    
    def get_enrolled_users(self) -> List[Dict[str, Any]]:
        """Get list of enrolled users."""
        return [
            {
                "user_id": vp.user_id,
                "name": vp.name,
                "samples_count": vp.samples_count,
                "created_at": vp.created_at.isoformat(),
            }
            for vp in self._voice_prints.values()
        ]
    
    def remove_user(self, user_id: str) -> bool:
        """Remove a user's voice print."""
        if user_id in self._voice_prints:
            del self._voice_prints[user_id]
            
            # Delete file
            file_path = self._data_path / f"{user_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            return True
        return False


# ============================================
# Emotion-Aware TTS
# ============================================

class Emotion(Enum):
    """Speech emotions."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    CALM = "calm"
    SERIOUS = "serious"
    QUESTIONING = "questioning"


@dataclass
class EmotionTTSConfig:
    """Emotion TTS configuration."""
    default_emotion: Emotion = Emotion.NEUTRAL
    detect_from_text: bool = True
    voice_style_mapping: Dict[str, str] = field(default_factory=dict)


class EmotionTTS:
    """
    Emotion-aware text-to-speech.
    
    Adjusts voice style based on content emotion.
    """
    
    # Emotion patterns for detection
    EMOTION_PATTERNS = {
        Emotion.HAPPY: [
            r"太好了|太棒了|好開心|恭喜|成功|wonderful|great|awesome|yay",
            r"！+|!+",
        ],
        Emotion.SAD: [
            r"抱歉|對不起|遺憾|失敗|sorry|unfortunately|sadly",
            r"無法|不能|找不到",
        ],
        Emotion.EXCITED: [
            r"驚喜|驚人|不可思議|amazing|incredible|wow",
        ],
        Emotion.SERIOUS: [
            r"注意|警告|重要|小心|warning|important|critical",
        ],
        Emotion.QUESTIONING: [
            r"嗎？|呢？|\?",
            r"是否|是不是|能不能",
        ],
    }
    
    # Voice style mapping for Edge TTS
    EDGE_VOICE_STYLES = {
        Emotion.NEUTRAL: "",
        Emotion.HAPPY: "cheerful",
        Emotion.SAD: "sad",
        Emotion.EXCITED: "excited",
        Emotion.CALM: "calm",
        Emotion.SERIOUS: "serious",
        Emotion.QUESTIONING: "",
    }
    
    def __init__(self, config: EmotionTTSConfig = None):
        self.config = config or EmotionTTSConfig()
    
    def detect_emotion(self, text: str) -> Emotion:
        """Detect emotion from text content."""
        text_lower = text.lower()
        
        emotion_scores = {}
        
        for emotion, patterns in self.EMOTION_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches
            emotion_scores[emotion] = score
        
        if max(emotion_scores.values()) > 0:
            return max(emotion_scores, key=emotion_scores.get)
        
        return self.config.default_emotion
    
    async def speak(
        self,
        text: str,
        voice: str = "zh-TW-HsiaoChenNeural",
        emotion: Optional[Emotion] = None
    ) -> Optional[bytes]:
        """
        Generate emotion-aware speech.
        
        Args:
            text: Text to speak
            voice: Voice name
            emotion: Emotion (auto-detected if not provided)
            
        Returns:
            Audio bytes
        """
        # Detect emotion if not provided
        if emotion is None and self.config.detect_from_text:
            emotion = self.detect_emotion(text)
        
        emotion = emotion or Emotion.NEUTRAL
        
        try:
            import edge_tts
            
            # Get voice style
            style = self.EDGE_VOICE_STYLES.get(emotion, "")
            
            # Create communicate with style
            if style and "Neural" in voice:
                # Edge TTS supports styles for some voices
                ssml = f"""
                <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
                       xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-TW">
                    <voice name="{voice}">
                        <mstts:express-as style="{style}">
                            {text}
                        </mstts:express-as>
                    </voice>
                </speak>
                """
                # For SSML support, we'd need to use the API differently
                # Fall back to regular speech for now
            
            communicate = edge_tts.Communicate(text, voice)
            
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
            
            return bytes(audio_data) if audio_data else None
            
        except Exception as e:
            logger.error(f"Emotion TTS error: {e}")
            return None
    
    def get_emotion_response_prefix(self, emotion: Emotion) -> str:
        """Get appropriate prefix for emotion."""
        prefixes = {
            Emotion.HAPPY: "",
            Emotion.SAD: "",
            Emotion.EXCITED: "",
            Emotion.SERIOUS: "請注意，",
            Emotion.QUESTIONING: "",
            Emotion.NEUTRAL: "",
        }
        return prefixes.get(emotion, "")


# ============================================
# Voice Interruption Handler
# ============================================

class InterruptionType(Enum):
    """Types of voice interruption."""
    WAKE_WORD = "wake_word"
    LOUD_SPEECH = "loud_speech"
    KEYWORD = "keyword"


@dataclass
class InterruptionConfig:
    """Interruption configuration."""
    enabled: bool = True
    keywords: List[str] = field(default_factory=lambda: ["停", "stop", "等等", "wait"])
    energy_threshold: float = 0.3  # Above this, consider as interruption
    cooldown_seconds: float = 0.5  # Minimum time between interruptions


class VoiceInterruptionHandler:
    """
    Handles voice interruptions during TTS playback.
    
    Allows user to interrupt ongoing speech.
    """
    
    def __init__(self, config: InterruptionConfig = None):
        self.config = config or InterruptionConfig()
        self._is_speaking = False
        self._last_interruption = datetime.min
        self._interrupt_callbacks: List[Callable] = []
    
    def on_interrupt(self, callback: Callable) -> None:
        """Register interruption callback."""
        self._interrupt_callbacks.append(callback)
    
    def set_speaking(self, is_speaking: bool) -> None:
        """Set speaking state."""
        self._is_speaking = is_speaking
    
    async def check_interruption(self, audio_data: bytes) -> Optional[InterruptionType]:
        """
        Check if audio contains an interruption.
        
        Args:
            audio_data: Audio chunk to analyze
            
        Returns:
            InterruptionType if detected, None otherwise
        """
        if not self.config.enabled or not self._is_speaking:
            return None
        
        # Check cooldown
        if (datetime.now() - self._last_interruption).total_seconds() < self.config.cooldown_seconds:
            return None
        
        # Check energy level
        samples = struct.unpack(f"{len(audio_data) // 2}h", audio_data)
        if samples:
            rms = math.sqrt(sum(s * s for s in samples) / len(samples))
            normalized_rms = rms / 32767.0
            
            if normalized_rms > self.config.energy_threshold:
                self._last_interruption = datetime.now()
                await self._trigger_interruption(InterruptionType.LOUD_SPEECH)
                return InterruptionType.LOUD_SPEECH
        
        return None
    
    async def _trigger_interruption(self, interrupt_type: InterruptionType) -> None:
        """Trigger interruption callbacks."""
        for callback in self._interrupt_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(interrupt_type)
                else:
                    callback(interrupt_type)
            except Exception as e:
                logger.error(f"Interruption callback error: {e}")


# ============================================
# Meeting Assistant
# ============================================

@dataclass
class MeetingNote:
    """A note from the meeting."""
    timestamp: datetime
    content: str
    speaker: Optional[str] = None
    is_action_item: bool = False


@dataclass
class MeetingSummary:
    """Meeting summary."""
    title: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    participants: List[str]
    notes: List[MeetingNote]
    action_items: List[str]
    summary_text: str


class MeetingAssistant:
    """
    AI-powered meeting assistant.
    
    Features:
    - Meeting recording
    - Real-time transcription
    - Action item extraction
    - Summary generation
    """
    
    def __init__(self):
        self._is_recording = False
        self._start_time: Optional[datetime] = None
        self._notes: List[MeetingNote] = []
        self._audio_buffer = bytearray()
        self._participants: List[str] = []
        self._title = ""
    
    async def start_meeting(self, title: str = "Meeting") -> str:
        """Start a new meeting recording."""
        if self._is_recording:
            return "已經有會議正在進行中"
        
        self._is_recording = True
        self._start_time = datetime.now()
        self._notes = []
        self._audio_buffer = bytearray()
        self._participants = []
        self._title = title
        
        return f"開始記錄會議：{title}"
    
    async def stop_meeting(self) -> MeetingSummary:
        """Stop meeting and generate summary."""
        if not self._is_recording:
            return None
        
        self._is_recording = False
        end_time = datetime.now()
        
        # Generate summary
        summary = await self._generate_summary(end_time)
        
        return summary
    
    async def add_note(self, content: str, speaker: Optional[str] = None) -> None:
        """Add a note to the meeting."""
        if not self._is_recording:
            return
        
        # Check if it's an action item
        is_action = any(k in content.lower() for k in [
            "action item", "todo", "待辦", "需要", "記得", "提醒"
        ])
        
        note = MeetingNote(
            timestamp=datetime.now(),
            content=content,
            speaker=speaker,
            is_action_item=is_action
        )
        
        self._notes.append(note)
        
        if speaker and speaker not in self._participants:
            self._participants.append(speaker)
    
    async def process_transcription(self, text: str, speaker: Optional[str] = None) -> None:
        """Process a transcription chunk."""
        await self.add_note(text, speaker)
    
    async def _generate_summary(self, end_time: datetime) -> MeetingSummary:
        """Generate meeting summary using LLM."""
        duration = int((end_time - self._start_time).total_seconds() / 60)
        
        # Extract action items
        action_items = [
            note.content for note in self._notes
            if note.is_action_item
        ]
        
        # Generate summary text
        summary_text = await self._create_summary_text()
        
        return MeetingSummary(
            title=self._title,
            start_time=self._start_time,
            end_time=end_time,
            duration_minutes=duration,
            participants=self._participants,
            notes=self._notes,
            action_items=action_items,
            summary_text=summary_text
        )
    
    async def _create_summary_text(self) -> str:
        """Create summary text using LLM."""
        if not self._notes:
            return "會議沒有記錄內容"
        
        # Prepare notes text
        notes_text = "\n".join([
            f"[{note.timestamp.strftime('%H:%M')}] {note.speaker or '未知'}: {note.content}"
            for note in self._notes[:50]  # Limit to avoid token overflow
        ])
        
        try:
            from .llm_providers import get_llm_manager
            
            llm = get_llm_manager()
            
            prompt = f"""請為以下會議內容生成簡潔的摘要（繁體中文，100字以內）：

會議：{self._title}
時長：約 {len(self._notes)} 條記錄

內容：
{notes_text}

摘要："""
            
            result = await llm.generate(prompt=prompt, max_tokens=200)
            return result.strip()
            
        except Exception as e:
            logger.debug(f"Summary generation error: {e}")
            
            # Fallback: simple summary
            return f"會議 \"{self._title}\" 共 {len(self._notes)} 條記錄，{len(self._participants)} 位參與者"
    
    def get_action_items(self) -> List[str]:
        """Get current action items."""
        return [
            note.content for note in self._notes
            if note.is_action_item
        ]
    
    @property
    def is_recording(self) -> bool:
        return self._is_recording


# ============================================
# IDE Voice Navigation
# ============================================

class NavigationTarget(Enum):
    """Navigation targets."""
    LINE = "line"
    FUNCTION = "function"
    CLASS = "class"
    FILE = "file"
    DEFINITION = "definition"
    REFERENCE = "reference"
    ERROR = "error"
    BOOKMARK = "bookmark"


@dataclass
class NavigationCommand:
    """Navigation command."""
    target: NavigationTarget
    value: Optional[str] = None
    line_number: Optional[int] = None


class VoiceNavigator:
    """
    Voice-controlled IDE navigation.
    
    Commands:
    - "跳到第 50 行" -> Go to line 50
    - "找函數 main" -> Find function main
    - "下一個錯誤" -> Go to next error
    - "返回" -> Go back
    """
    
    NAVIGATION_PATTERNS = {
        NavigationTarget.LINE: [
            r"跳到第?\s*(\d+)\s*行",
            r"go to line\s*(\d+)",
            r"第\s*(\d+)\s*行",
        ],
        NavigationTarget.FUNCTION: [
            r"找?函數\s*(\w+)",
            r"find function\s*(\w+)",
            r"跳到函數\s*(\w+)",
        ],
        NavigationTarget.CLASS: [
            r"找?類別?\s*(\w+)",
            r"find class\s*(\w+)",
        ],
        NavigationTarget.FILE: [
            r"打開檔案\s*(.+)",
            r"open file\s*(.+)",
        ],
        NavigationTarget.ERROR: [
            r"下一個錯誤",
            r"next error",
            r"上一個錯誤",
            r"previous error",
        ],
        NavigationTarget.DEFINITION: [
            r"跳到定義",
            r"go to definition",
        ],
    }
    
    def __init__(self):
        self._history: List[NavigationCommand] = []
        self._system = platform.system()
    
    def parse_command(self, text: str) -> Optional[NavigationCommand]:
        """Parse navigation command from text."""
        text_lower = text.lower()
        
        for target, patterns in self.NAVIGATION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    value = match.group(1) if match.lastindex else None
                    line_number = int(value) if value and value.isdigit() else None
                    
                    return NavigationCommand(
                        target=target,
                        value=value,
                        line_number=line_number
                    )
        
        return None
    
    async def execute(self, command: NavigationCommand) -> str:
        """Execute navigation command."""
        self._history.append(command)
        
        if command.target == NavigationTarget.LINE:
            return await self._go_to_line(command.line_number)
        elif command.target == NavigationTarget.FUNCTION:
            return await self._find_symbol(command.value, "function")
        elif command.target == NavigationTarget.CLASS:
            return await self._find_symbol(command.value, "class")
        elif command.target == NavigationTarget.FILE:
            return await self._open_file(command.value)
        elif command.target == NavigationTarget.ERROR:
            return await self._go_to_error()
        elif command.target == NavigationTarget.DEFINITION:
            return await self._go_to_definition()
        
        return "無法識別的導航指令"
    
    async def _go_to_line(self, line: Optional[int]) -> str:
        """Go to specific line in editor."""
        if not line:
            return "請指定行號"
        
        # Use VS Code / Cursor command
        cmd = f"code --goto :{line}"
        
        try:
            await asyncio.create_subprocess_shell(cmd)
            return f"已跳到第 {line} 行"
        except Exception as e:
            logger.debug(f"Navigation error: {e}")
            return f"無法跳到第 {line} 行"
    
    async def _find_symbol(self, name: Optional[str], symbol_type: str) -> str:
        """Find and go to symbol."""
        if not name:
            return f"請指定{symbol_type}名稱"
        
        # This would integrate with LSP or use grep
        # For now, return guidance
        return f"請使用 Cmd+Shift+O 搜尋 {symbol_type} \"{name}\""
    
    async def _open_file(self, filename: Optional[str]) -> str:
        """Open a file."""
        if not filename:
            return "請指定檔案名稱"
        
        cmd = f"code {filename}"
        
        try:
            await asyncio.create_subprocess_shell(cmd)
            return f"已打開 {filename}"
        except Exception as e:
            return f"無法打開 {filename}"
    
    async def _go_to_error(self) -> str:
        """Go to next/previous error."""
        # This would use editor API
        return "請使用 F8 跳到下一個錯誤，Shift+F8 跳到上一個"
    
    async def _go_to_definition(self) -> str:
        """Go to symbol definition."""
        return "請使用 F12 或 Cmd+Click 跳到定義"
    
    async def go_back(self) -> str:
        """Go back in navigation history."""
        if len(self._history) > 1:
            self._history.pop()
            # Would trigger editor back command
            return "已返回"
        return "沒有更多歷史記錄"


# ============================================
# Offline TTS (Piper)
# ============================================

class OfflineTTS:
    """
    Offline text-to-speech using Piper or eSpeak.
    
    Works without internet connection.
    """
    
    def __init__(self, voice_model: str = "zh_CN-huayan-medium"):
        self._voice_model = voice_model
        self._piper_path = self._find_piper()
        self._espeak_available = self._check_espeak()
    
    def _find_piper(self) -> Optional[str]:
        """Find Piper executable."""
        # Check common locations
        locations = [
            "/usr/local/bin/piper",
            "/usr/bin/piper",
            str(Path.home() / ".local/bin/piper"),
            "piper",
        ]
        
        for loc in locations:
            if os.path.exists(loc) or self._command_exists(loc):
                return loc
        
        return None
    
    def _check_espeak(self) -> bool:
        """Check if eSpeak is available."""
        return self._command_exists("espeak") or self._command_exists("espeak-ng")
    
    def _command_exists(self, cmd: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run(
                ["which", cmd],
                capture_output=True,
                check=True
            )
            return True
        except Exception:
            return False
    
    async def speak(self, text: str) -> Optional[bytes]:
        """
        Generate speech using offline TTS.
        
        Tries Piper first, falls back to eSpeak.
        """
        if self._piper_path:
            return await self._speak_piper(text)
        elif self._espeak_available:
            return await self._speak_espeak(text)
        
        logger.warning("No offline TTS available")
        return None
    
    async def _speak_piper(self, text: str) -> Optional[bytes]:
        """Generate speech using Piper."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name
            
            # Run Piper
            process = await asyncio.create_subprocess_exec(
                self._piper_path,
                "--model", self._voice_model,
                "--output_file", output_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate(text.encode("utf-8"))
            
            if process.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio_data = f.read()
                os.unlink(output_path)
                return audio_data
                
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
        
        return None
    
    async def _speak_espeak(self, text: str) -> Optional[bytes]:
        """Generate speech using eSpeak."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name
            
            espeak_cmd = "espeak-ng" if self._command_exists("espeak-ng") else "espeak"
            
            # Run eSpeak
            process = await asyncio.create_subprocess_exec(
                espeak_cmd,
                "-v", "zh",  # Chinese voice
                "-w", output_path,
                text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio_data = f.read()
                os.unlink(output_path)
                return audio_data
                
        except Exception as e:
            logger.error(f"eSpeak TTS error: {e}")
        
        return None
    
    @property
    def is_available(self) -> bool:
        return self._piper_path is not None or self._espeak_available


# ============================================
# Multi-Language Response
# ============================================

class MultiLanguageResponder:
    """
    Generates responses in multiple languages.
    
    Auto-detects user language and responds accordingly.
    """
    
    LANGUAGE_PATTERNS = {
        "zh-TW": [r"[\u4e00-\u9fff]", r"嗎|呢|吧|喔|哦"],
        "zh-CN": [r"[\u4e00-\u9fff]", r"吗|呢|吧"],
        "en": [r"[a-zA-Z]{3,}", r"\b(the|is|are|what|how|why)\b"],
        "ja": [r"[\u3040-\u309f\u30a0-\u30ff]", r"です|ます|ください"],
        "ko": [r"[\uac00-\ud7af]", r"습니다|세요|니다"],
    }
    
    VOICE_MAP = {
        "zh-TW": "zh-TW-HsiaoChenNeural",
        "zh-CN": "zh-CN-XiaoxiaoNeural",
        "en": "en-US-AriaNeural",
        "ja": "ja-JP-NanamiNeural",
        "ko": "ko-KR-SunHiNeural",
    }
    
    def __init__(self, default_language: str = "zh-TW"):
        self._default_language = default_language
        self._user_languages: Dict[str, str] = {}
    
    def detect_language(self, text: str) -> str:
        """Detect language from text."""
        scores = {}
        
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text))
                score += matches
            scores[lang] = score
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return self._default_language
    
    def set_user_language(self, user_id: str, language: str) -> None:
        """Set preferred language for a user."""
        self._user_languages[user_id] = language
    
    def get_user_language(self, user_id: str) -> str:
        """Get user's preferred language."""
        return self._user_languages.get(user_id, self._default_language)
    
    def get_voice_for_language(self, language: str) -> str:
        """Get appropriate voice for language."""
        return self.VOICE_MAP.get(language, self.VOICE_MAP["en"])
    
    async def respond(
        self,
        text: str,
        user_id: str = "default",
        auto_detect: bool = True
    ) -> Tuple[str, str]:
        """
        Generate response in appropriate language.
        
        Returns:
            (response_text, voice_name)
        """
        # Detect or get user language
        if auto_detect:
            language = self.detect_language(text)
        else:
            language = self.get_user_language(user_id)
        
        voice = self.get_voice_for_language(language)
        
        return text, voice


# ============================================
# Smart Home Integration
# ============================================

class SmartHomeProtocol(Enum):
    """Smart home protocols."""
    HOMEKIT = "homekit"
    GOOGLE_HOME = "google_home"
    ALEXA = "alexa"
    XIAOMI = "xiaomi"
    TUYA = "tuya"
    MQTT = "mqtt"


@dataclass
class SmartDevice:
    """Smart home device."""
    id: str
    name: str
    type: str  # light, switch, thermostat, etc.
    protocol: SmartHomeProtocol
    state: Dict[str, Any] = field(default_factory=dict)


class SmartHomeHandler:
    """
    Smart home voice control.
    
    Supports multiple protocols.
    """
    
    DEVICE_PATTERNS = {
        "light": ["燈", "light", "照明"],
        "switch": ["開關", "switch", "插座"],
        "thermostat": ["空調", "冷氣", "暖氣", "thermostat", "AC"],
        "fan": ["風扇", "fan"],
        "lock": ["門鎖", "lock"],
        "camera": ["攝影機", "相機", "camera"],
    }
    
    ACTION_PATTERNS = {
        "on": ["打開", "開", "turn on", "on", "啟動"],
        "off": ["關閉", "關", "turn off", "off", "停止"],
        "dim": ["調暗", "降低", "dim"],
        "bright": ["調亮", "提高", "bright"],
        "set": ["設定", "調到", "set"],
    }
    
    def __init__(self):
        self._devices: Dict[str, SmartDevice] = {}
        self._protocols: Dict[SmartHomeProtocol, Any] = {}
    
    def register_device(self, device: SmartDevice) -> None:
        """Register a smart device."""
        self._devices[device.id] = device
    
    def parse_command(self, text: str) -> Optional[Tuple[str, str, Dict]]:
        """
        Parse smart home command from text.
        
        Returns:
            (action, device_type, params) or None
        """
        text_lower = text.lower()
        
        # Find action
        action = None
        for act, patterns in self.ACTION_PATTERNS.items():
            if any(p in text_lower for p in patterns):
                action = act
                break
        
        if not action:
            return None
        
        # Find device type
        device_type = None
        for dtype, patterns in self.DEVICE_PATTERNS.items():
            if any(p in text_lower for p in patterns):
                device_type = dtype
                break
        
        if not device_type:
            return None
        
        # Extract parameters (e.g., brightness level, temperature)
        params = {}
        
        # Extract percentage
        pct_match = re.search(r"(\d+)\s*[%％]", text)
        if pct_match:
            params["level"] = int(pct_match.group(1))
        
        # Extract temperature
        temp_match = re.search(r"(\d+)\s*度", text)
        if temp_match:
            params["temperature"] = int(temp_match.group(1))
        
        return (action, device_type, params)
    
    async def execute(self, action: str, device_type: str, params: Dict) -> str:
        """Execute smart home command."""
        # Find matching devices
        matching_devices = [
            d for d in self._devices.values()
            if d.type == device_type
        ]
        
        if not matching_devices:
            return f"找不到 {device_type} 設備"
        
        # Execute on all matching devices
        results = []
        for device in matching_devices:
            result = await self._execute_device(device, action, params)
            results.append(f"{device.name}: {result}")
        
        return "；".join(results)
    
    async def _execute_device(
        self,
        device: SmartDevice,
        action: str,
        params: Dict
    ) -> str:
        """Execute action on a specific device."""
        # This would integrate with actual smart home APIs
        # For now, simulate the action
        
        if action == "on":
            device.state["power"] = True
            return "已開啟"
        elif action == "off":
            device.state["power"] = False
            return "已關閉"
        elif action in ("dim", "bright", "set"):
            level = params.get("level", 50)
            device.state["level"] = level
            return f"已調整到 {level}%"
        
        return "操作完成"
    
    def get_devices(self) -> List[Dict]:
        """Get list of registered devices."""
        return [
            {
                "id": d.id,
                "name": d.name,
                "type": d.type,
                "protocol": d.protocol.value,
                "state": d.state,
            }
            for d in self._devices.values()
        ]


# ============================================
# Global Instances
# ============================================

_voice_print_manager: Optional[VoicePrintManager] = None
_meeting_assistant: Optional[MeetingAssistant] = None
_voice_navigator: Optional[VoiceNavigator] = None
_smart_home_handler: Optional[SmartHomeHandler] = None


def get_voice_print_manager() -> VoicePrintManager:
    global _voice_print_manager
    if _voice_print_manager is None:
        _voice_print_manager = VoicePrintManager()
    return _voice_print_manager


def get_meeting_assistant() -> MeetingAssistant:
    global _meeting_assistant
    if _meeting_assistant is None:
        _meeting_assistant = MeetingAssistant()
    return _meeting_assistant


def get_voice_navigator() -> VoiceNavigator:
    global _voice_navigator
    if _voice_navigator is None:
        _voice_navigator = VoiceNavigator()
    return _voice_navigator


def get_smart_home_handler() -> SmartHomeHandler:
    global _smart_home_handler
    if _smart_home_handler is None:
        _smart_home_handler = SmartHomeHandler()
    return _smart_home_handler


__all__ = [
    # Voice Print
    "VoicePrintManager",
    "VoicePrint",
    "VoicePrintConfig",
    "VoicePrintStatus",
    "get_voice_print_manager",
    # Emotion TTS
    "EmotionTTS",
    "EmotionTTSConfig",
    "Emotion",
    # Interruption
    "VoiceInterruptionHandler",
    "InterruptionConfig",
    "InterruptionType",
    # Meeting
    "MeetingAssistant",
    "MeetingNote",
    "MeetingSummary",
    "get_meeting_assistant",
    # Navigation
    "VoiceNavigator",
    "NavigationCommand",
    "NavigationTarget",
    "get_voice_navigator",
    # Offline TTS
    "OfflineTTS",
    # Multi-language
    "MultiLanguageResponder",
    # Smart Home
    "SmartHomeHandler",
    "SmartDevice",
    "SmartHomeProtocol",
    "get_smart_home_handler",
]
