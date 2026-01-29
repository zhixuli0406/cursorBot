"""
CursorBot v1.1 Voice Assistant

A Siri-like voice assistant with:
- Multi-keyword wake detection
- Offline speech recognition
- Natural language intent recognition
- Context-aware responses
- System integration
- Personalization

Usage:
    from src.core.voice_assistant import get_voice_assistant
    
    assistant = get_voice_assistant()
    await assistant.start()
    
    # Process audio continuously
    async for response in assistant.listen():
        print(f"User: {response.transcript}")
        print(f"Intent: {response.intent}")
        print(f"Response: {response.text}")
"""

import os
import asyncio
import json
import struct
import wave
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, AsyncGenerator
from collections import deque

from ..utils.logger import logger


# ============================================
# Enums
# ============================================

class AssistantState(Enum):
    """Voice assistant states."""
    IDLE = "idle"
    WAKE_LISTENING = "wake_listening"      # Listening for wake word
    COMMAND_LISTENING = "command_listening" # Listening for command after wake
    PROCESSING = "processing"               # Processing command
    SPEAKING = "speaking"                   # Playing response
    ERROR = "error"


class WakeEngine(Enum):
    """Wake word detection engines."""
    VOSK = "vosk"           # Vosk offline (free)
    PORCUPINE = "porcupine" # Picovoice Porcupine (accurate)
    WHISPER = "whisper"     # Whisper-based (flexible)
    CUSTOM = "custom"       # Custom model


class STTEngine(Enum):
    """Speech-to-text engines."""
    WHISPER_LOCAL = "whisper_local"   # Local Whisper
    WHISPER_API = "whisper_api"       # OpenAI Whisper API
    VOSK = "vosk"                     # Vosk offline
    GOOGLE = "google"                 # Google Cloud
    AZURE = "azure"                   # Azure Speech


class TTSEngine(Enum):
    """Text-to-speech engines."""
    ELEVENLABS = "elevenlabs"   # ElevenLabs (natural)
    OPENAI = "openai"           # OpenAI TTS
    EDGE = "edge"               # Edge TTS (free)
    PIPER = "piper"             # Piper offline
    SYSTEM = "system"           # System TTS


class IntentCategory(Enum):
    """Intent categories."""
    QUESTION = "question"         # Asking something
    COMMAND = "command"           # Execute action
    CONTROL = "control"           # System control
    SEARCH = "search"             # Search for info
    REMINDER = "reminder"         # Set reminder
    CALENDAR = "calendar"         # Calendar operations
    CODE = "code"                 # Code operations
    CHAT = "chat"                 # General chat
    UNKNOWN = "unknown"


# ============================================
# Data Classes
# ============================================

@dataclass
class VoiceAssistantConfig:
    """Voice assistant configuration."""
    
    # Wake word settings
    wake_enabled: bool = True
    wake_engine: WakeEngine = WakeEngine.VOSK
    wake_words: List[str] = field(default_factory=lambda: [
        "hey cursor",
        "ok cursor", 
        "嘿 cursor",
        "小助手",
    ])
    wake_sensitivity: float = 0.5
    wake_timeout: float = 10.0  # Seconds to listen after wake
    
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration: float = 0.1  # Seconds per chunk
    
    # Speech-to-text
    stt_engine: STTEngine = STTEngine.WHISPER_LOCAL
    stt_language: str = "zh"  # Primary language
    stt_languages: List[str] = field(default_factory=lambda: ["zh", "en", "ja"])
    
    # Text-to-speech
    tts_engine: TTSEngine = TTSEngine.EDGE
    tts_voice: str = "zh-TW-HsiaoChenNeural"  # Chinese Taiwan
    tts_speed: float = 1.0
    tts_enabled: bool = True
    
    # Voice activity detection
    vad_enabled: bool = True
    vad_threshold: float = 0.02
    vad_silence_duration: float = 1.5
    vad_min_speech: float = 0.3
    
    # Noise reduction
    noise_reduction: bool = True
    noise_threshold: float = 0.01
    
    # Feedback sounds
    sound_enabled: bool = True
    sound_wake: str = "sounds/wake.wav"
    sound_start: str = "sounds/start.wav"
    sound_end: str = "sounds/end.wav"
    sound_error: str = "sounds/error.wav"
    
    # Context & memory
    context_timeout: int = 300  # Seconds
    max_context_turns: int = 20
    remember_preferences: bool = True
    
    # Paths
    vosk_model_path: str = "models/vosk-model-small-cn"
    whisper_model: str = "base"
    porcupine_key: str = ""


@dataclass
class WakeEvent:
    """Wake word detection event."""
    wake_word: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    engine: str = ""


@dataclass 
class Utterance:
    """User's spoken input."""
    text: str
    language: str = "zh"
    confidence: float = 1.0
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    audio_data: Optional[bytes] = None


@dataclass
class Intent:
    """Recognized intent from utterance."""
    category: IntentCategory
    action: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""


@dataclass
class AssistantResponse:
    """Response from the assistant."""
    text: str
    audio: Optional[bytes] = None
    intent: Optional[Intent] = None
    utterance: Optional[Utterance] = None
    action_result: Any = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationTurn:
    """A turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[Intent] = None


# ============================================
# Wake Word Detector
# ============================================

class WakeWordDetector(ABC):
    """Abstract wake word detector."""
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the detector."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the detector."""
        pass
    
    @abstractmethod
    async def process(self, audio: bytes) -> Optional[WakeEvent]:
        """Process audio chunk for wake word."""
        pass


class VoskWakeDetector(WakeWordDetector):
    """Vosk-based wake word detector (offline)."""
    
    def __init__(self, config: VoiceAssistantConfig):
        self.config = config
        self._model = None
        self._recognizer = None
        self._running = False
    
    async def start(self) -> bool:
        try:
            from vosk import Model, KaldiRecognizer
            
            model_path = self.config.vosk_model_path
            if not os.path.exists(model_path):
                logger.warning(f"Vosk model not found: {model_path}")
                logger.info("Download from: https://alphacephei.com/vosk/models")
                return False
            
            self._model = Model(model_path)
            self._recognizer = KaldiRecognizer(
                self._model, 
                self.config.sample_rate
            )
            self._running = True
            logger.info("Vosk wake detector started")
            return True
            
        except ImportError:
            logger.error("vosk not installed: pip install vosk")
            return False
        except Exception as e:
            logger.error(f"Vosk init error: {e}")
            return False
    
    async def stop(self) -> None:
        self._running = False
        self._model = None
        self._recognizer = None
    
    async def process(self, audio: bytes) -> Optional[WakeEvent]:
        if not self._running or not self._recognizer:
            return None
        
        try:
            if self._recognizer.AcceptWaveform(audio):
                result = json.loads(self._recognizer.Result())
                text = result.get("text", "").lower().strip()
                
                if not text:
                    return None
                
                # Check for wake words
                for wake_word in self.config.wake_words:
                    wake_lower = wake_word.lower()
                    if wake_lower in text or self._fuzzy_match(text, wake_lower):
                        return WakeEvent(
                            wake_word=wake_word,
                            confidence=0.8,
                            engine="vosk"
                        )
            
            # Also check partial results for faster response
            partial = json.loads(self._recognizer.PartialResult())
            partial_text = partial.get("partial", "").lower()
            
            for wake_word in self.config.wake_words:
                wake_lower = wake_word.lower()
                if wake_lower in partial_text:
                    return WakeEvent(
                        wake_word=wake_word,
                        confidence=0.6,
                        engine="vosk"
                    )
                    
        except Exception as e:
            logger.error(f"Vosk process error: {e}")
        
        return None
    
    def _fuzzy_match(self, text: str, wake_word: str) -> bool:
        """Simple fuzzy matching for wake words."""
        # Split into words and check if main keywords present
        wake_parts = wake_word.split()
        text_parts = text.split()
        
        matches = sum(1 for wp in wake_parts if any(wp in tp for tp in text_parts))
        return matches >= len(wake_parts) * 0.7


class PorcupineWakeDetector(WakeWordDetector):
    """Porcupine wake word detector (accurate)."""
    
    def __init__(self, config: VoiceAssistantConfig):
        self.config = config
        self._porcupine = None
        self._running = False
    
    async def start(self) -> bool:
        try:
            import pvporcupine
            
            if not self.config.porcupine_key:
                logger.error("Porcupine access key not configured")
                return False
            
            # Use built-in keywords or custom
            self._porcupine = pvporcupine.create(
                access_key=self.config.porcupine_key,
                keywords=["hey google", "ok google"],  # Use similar built-in
                sensitivities=[self.config.wake_sensitivity] * 2
            )
            
            self._running = True
            logger.info("Porcupine wake detector started")
            return True
            
        except ImportError:
            logger.error("pvporcupine not installed: pip install pvporcupine")
            return False
        except Exception as e:
            logger.error(f"Porcupine init error: {e}")
            return False
    
    async def stop(self) -> None:
        if self._porcupine:
            self._porcupine.delete()
        self._porcupine = None
        self._running = False
    
    async def process(self, audio: bytes) -> Optional[WakeEvent]:
        if not self._running or not self._porcupine:
            return None
        
        try:
            # Convert bytes to int16 array
            pcm = struct.unpack_from(f"{len(audio) // 2}h", audio)
            
            # Ensure correct frame length
            frame_length = self._porcupine.frame_length
            if len(pcm) < frame_length:
                return None
            
            pcm = pcm[:frame_length]
            keyword_index = self._porcupine.process(pcm)
            
            if keyword_index >= 0:
                return WakeEvent(
                    wake_word=self.config.wake_words[0],
                    confidence=self.config.wake_sensitivity,
                    engine="porcupine"
                )
                
        except Exception as e:
            logger.error(f"Porcupine process error: {e}")
        
        return None


# ============================================
# Speech-to-Text
# ============================================

class SpeechToText:
    """Multi-engine speech-to-text."""
    
    def __init__(self, config: VoiceAssistantConfig):
        self.config = config
        self._engine = None
        self._model = None
    
    async def start(self) -> bool:
        """Initialize STT engine."""
        engine = self.config.stt_engine
        
        if engine == STTEngine.WHISPER_LOCAL:
            return await self._init_whisper_local()
        elif engine == STTEngine.VOSK:
            return await self._init_vosk()
        elif engine == STTEngine.WHISPER_API:
            return await self._init_whisper_api()
        
        return False
    
    async def _init_whisper_local(self) -> bool:
        """Initialize local Whisper."""
        try:
            import whisper
            self._model = whisper.load_model(self.config.whisper_model)
            self._engine = "whisper_local"
            logger.info(f"Whisper model loaded: {self.config.whisper_model}")
            return True
        except ImportError:
            logger.error("whisper not installed: pip install openai-whisper")
            return False
        except Exception as e:
            logger.error(f"Whisper init error: {e}")
            return False
    
    async def _init_vosk(self) -> bool:
        """Initialize Vosk STT."""
        try:
            from vosk import Model, KaldiRecognizer
            
            model_path = self.config.vosk_model_path
            if not os.path.exists(model_path):
                return False
            
            self._model = {
                "model": Model(model_path),
            }
            self._model["recognizer"] = KaldiRecognizer(
                self._model["model"], 
                self.config.sample_rate
            )
            self._engine = "vosk"
            return True
            
        except Exception as e:
            logger.error(f"Vosk STT init error: {e}")
            return False
    
    async def _init_whisper_api(self) -> bool:
        """Initialize OpenAI Whisper API."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set for Whisper API")
            return False
        
        self._engine = "whisper_api"
        return True
    
    async def transcribe(self, audio: bytes) -> Optional[Utterance]:
        """Transcribe audio to text."""
        if not self._engine:
            return None
        
        try:
            if self._engine == "whisper_local":
                return await self._transcribe_whisper_local(audio)
            elif self._engine == "vosk":
                return await self._transcribe_vosk(audio)
            elif self._engine == "whisper_api":
                return await self._transcribe_whisper_api(audio)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        
        return None
    
    async def _transcribe_whisper_local(self, audio: bytes) -> Optional[Utterance]:
        """Transcribe with local Whisper."""
        import numpy as np
        
        # Convert bytes to numpy array
        audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Transcribe
        result = self._model.transcribe(
            audio_np,
            language=self.config.stt_language,
            fp16=False
        )
        
        text = result.get("text", "").strip()
        if not text:
            return None
        
        return Utterance(
            text=text,
            language=result.get("language", self.config.stt_language),
            confidence=1.0
        )
    
    async def _transcribe_vosk(self, audio: bytes) -> Optional[Utterance]:
        """Transcribe with Vosk."""
        recognizer = self._model["recognizer"]
        
        if recognizer.AcceptWaveform(audio):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").strip()
            
            if text:
                return Utterance(
                    text=text,
                    language=self.config.stt_language,
                    confidence=0.9
                )
        
        return None
    
    async def _transcribe_whisper_api(self, audio: bytes) -> Optional[Utterance]:
        """Transcribe with OpenAI Whisper API."""
        import httpx
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            with wave.open(f.name, "wb") as wav:
                wav.setnchannels(self.config.channels)
                wav.setsampwidth(2)
                wav.setframerate(self.config.sample_rate)
                wav.writeframes(audio)
            
            temp_path = f.name
        
        try:
            async with httpx.AsyncClient() as client:
                with open(temp_path, "rb") as audio_file:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                        files={"file": ("audio.wav", audio_file, "audio/wav")},
                        data={"model": "whisper-1"}
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "").strip()
                    if text:
                        return Utterance(text=text, language="auto")
        finally:
            os.unlink(temp_path)
        
        return None


# ============================================
# Text-to-Speech
# ============================================

class TextToSpeech:
    """Multi-engine text-to-speech."""
    
    def __init__(self, config: VoiceAssistantConfig):
        self.config = config
        self._engine = None
    
    async def start(self) -> bool:
        """Initialize TTS engine."""
        engine = self.config.tts_engine
        
        if engine == TTSEngine.EDGE:
            return await self._init_edge()
        elif engine == TTSEngine.ELEVENLABS:
            return await self._init_elevenlabs()
        elif engine == TTSEngine.OPENAI:
            return await self._init_openai()
        elif engine == TTSEngine.PIPER:
            return await self._init_piper()
        
        return False
    
    async def _init_edge(self) -> bool:
        """Initialize Edge TTS (free)."""
        try:
            import edge_tts
            self._engine = "edge"
            logger.info("Edge TTS initialized")
            return True
        except ImportError:
            logger.error("edge-tts not installed: pip install edge-tts")
            return False
    
    async def _init_elevenlabs(self) -> bool:
        """Initialize ElevenLabs TTS."""
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            logger.warning("ELEVENLABS_API_KEY not set")
            return False
        
        self._engine = "elevenlabs"
        return True
    
    async def _init_openai(self) -> bool:
        """Initialize OpenAI TTS."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return False
        
        self._engine = "openai"
        return True
    
    async def _init_piper(self) -> bool:
        """Initialize Piper TTS (offline)."""
        # Piper requires additional setup
        self._engine = "piper"
        return True
    
    async def speak(self, text: str) -> Optional[bytes]:
        """Convert text to speech."""
        if not self._engine or not self.config.tts_enabled:
            return None
        
        try:
            if self._engine == "edge":
                return await self._speak_edge(text)
            elif self._engine == "elevenlabs":
                return await self._speak_elevenlabs(text)
            elif self._engine == "openai":
                return await self._speak_openai(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
        
        return None
    
    async def _speak_edge(self, text: str) -> Optional[bytes]:
        """Generate speech with Edge TTS."""
        import edge_tts
        
        communicate = edge_tts.Communicate(text, self.config.tts_voice)
        
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        
        return bytes(audio_data) if audio_data else None
    
    async def _speak_elevenlabs(self, text: str) -> Optional[bytes]:
        """Generate speech with ElevenLabs."""
        import httpx
        
        api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2"
                }
            )
            
            if response.status_code == 200:
                return response.content
        
        return None
    
    async def _speak_openai(self, text: str) -> Optional[bytes]:
        """Generate speech with OpenAI TTS."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",
                    "voice": "nova",
                    "input": text
                }
            )
            
            if response.status_code == 200:
                return response.content
        
        return None


# ============================================
# Intent Recognition
# ============================================

class IntentRecognizer:
    """Natural language intent recognition."""
    
    # Intent patterns (simple rule-based for now)
    PATTERNS = {
        IntentCategory.COMMAND: [
            r"執行|run|execute|開啟|打開|open|啟動|start",
            r"建立|create|新增|add|生成|generate",
            r"刪除|delete|移除|remove|關閉|close",
        ],
        IntentCategory.QUESTION: [
            r"什麼|what|是什麼|怎麼|how|為什麼|why|哪|where|when|誰|who",
            r"可以|能不能|是否|有沒有|是不是",
        ],
        IntentCategory.CONTROL: [
            r"音量|volume|亮度|brightness|靜音|mute",
            r"暫停|pause|停止|stop|繼續|resume|播放|play",
        ],
        IntentCategory.SEARCH: [
            r"搜尋|search|找|find|查|lookup|google",
        ],
        IntentCategory.REMINDER: [
            r"提醒|remind|記住|remember|待辦|todo",
        ],
        IntentCategory.CALENDAR: [
            r"行程|schedule|會議|meeting|日曆|calendar|預約|appointment",
        ],
        IntentCategory.CODE: [
            r"程式|code|git|commit|push|pull|build|test|debug",
            r"函數|function|class|method|variable|檔案|file",
        ],
    }
    
    def __init__(self, config: VoiceAssistantConfig):
        self.config = config
        self._llm = None
    
    async def start(self) -> bool:
        """Initialize intent recognizer."""
        # Can use LLM for better intent recognition
        return True
    
    async def recognize(self, text: str) -> Intent:
        """Recognize intent from text."""
        import re
        
        text_lower = text.lower()
        
        # Try pattern matching first
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return Intent(
                        category=category,
                        raw_text=text,
                        confidence=0.8
                    )
        
        # Default to chat
        return Intent(
            category=IntentCategory.CHAT,
            raw_text=text,
            confidence=0.5
        )
    
    async def extract_entities(self, text: str, intent: Intent) -> Dict[str, Any]:
        """Extract entities from text based on intent."""
        entities = {}
        
        # Extract time expressions
        import re
        time_patterns = [
            (r"(\d+)\s*分鐘|(\d+)\s*minutes?", "duration_minutes"),
            (r"(\d+)\s*小時|(\d+)\s*hours?", "duration_hours"),
            (r"明天|tomorrow", "date_tomorrow"),
            (r"今天|today", "date_today"),
            (r"(\d{1,2})[：:點](\d{0,2})", "time"),
        ]
        
        for pattern, entity_type in time_patterns:
            match = re.search(pattern, text)
            if match:
                entities[entity_type] = match.group(0)
        
        return entities


# ============================================
# Audio Processing
# ============================================

class AudioProcessor:
    """Audio processing utilities."""
    
    def __init__(self, config: VoiceAssistantConfig):
        self.config = config
        self._noise_profile = None
    
    def detect_speech(self, audio: bytes) -> bool:
        """Detect if audio contains speech (VAD)."""
        if not self.config.vad_enabled:
            return True
        
        # Convert to samples
        samples = struct.unpack(f"{len(audio) // 2}h", audio)
        if not samples:
            return False
        
        # Calculate RMS energy
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        normalized_rms = rms / 32767.0
        
        return normalized_rms > self.config.vad_threshold
    
    def reduce_noise(self, audio: bytes) -> bytes:
        """Apply noise reduction."""
        if not self.config.noise_reduction:
            return audio
        
        # Simple noise gate
        samples = list(struct.unpack(f"{len(audio) // 2}h", audio))
        threshold = int(self.config.noise_threshold * 32767)
        
        for i, s in enumerate(samples):
            if abs(s) < threshold:
                samples[i] = 0
        
        return struct.pack(f"{len(samples)}h", *samples)
    
    def normalize_volume(self, audio: bytes, target_rms: float = 0.1) -> bytes:
        """Normalize audio volume."""
        samples = list(struct.unpack(f"{len(audio) // 2}h", audio))
        if not samples:
            return audio
        
        # Calculate current RMS
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        if rms == 0:
            return audio
        
        # Calculate gain
        current_rms = rms / 32767.0
        gain = target_rms / current_rms
        gain = min(gain, 3.0)  # Limit gain
        
        # Apply gain
        samples = [int(max(-32768, min(32767, s * gain))) for s in samples]
        
        return struct.pack(f"{len(samples)}h", *samples)


# ============================================
# Sound Effects
# ============================================

class SoundEffects:
    """Manage feedback sounds."""
    
    def __init__(self, config: VoiceAssistantConfig):
        self.config = config
        self._sounds: Dict[str, bytes] = {}
    
    async def load(self) -> None:
        """Load sound effects."""
        if not self.config.sound_enabled:
            return
        
        # Generate simple beep sounds if files don't exist
        sound_files = {
            "wake": self.config.sound_wake,
            "start": self.config.sound_start,
            "end": self.config.sound_end,
            "error": self.config.sound_error,
        }
        
        for name, path in sound_files.items():
            if os.path.exists(path):
                with open(path, "rb") as f:
                    self._sounds[name] = f.read()
            else:
                # Generate simple tone
                self._sounds[name] = self._generate_tone(
                    frequency=880 if name == "wake" else 440,
                    duration=0.2
                )
    
    def _generate_tone(self, frequency: int = 440, duration: float = 0.2) -> bytes:
        """Generate a simple tone."""
        import math
        
        sample_rate = 16000
        num_samples = int(sample_rate * duration)
        samples = []
        
        for i in range(num_samples):
            t = i / sample_rate
            # Fade in/out
            envelope = min(1.0, i / 100) * min(1.0, (num_samples - i) / 100)
            value = int(16000 * envelope * math.sin(2 * math.pi * frequency * t))
            samples.append(value)
        
        return struct.pack(f"{len(samples)}h", *samples)
    
    async def play(self, sound_name: str) -> None:
        """Play a sound effect."""
        if not self.config.sound_enabled:
            return
        
        audio_data = self._sounds.get(sound_name)
        if audio_data:
            # Platform-specific playback would go here
            logger.debug(f"Playing sound: {sound_name}")


# ============================================
# Main Voice Assistant
# ============================================

class VoiceAssistant:
    """
    CursorBot v1.1 Voice Assistant
    
    A Siri-like voice assistant that integrates:
    - Wake word detection
    - Speech recognition  
    - Intent understanding
    - Context-aware responses
    - Text-to-speech output
    """
    
    def __init__(self, config: VoiceAssistantConfig = None):
        self.config = config or VoiceAssistantConfig()
        
        self._state = AssistantState.IDLE
        self._running = False
        
        # Components
        self._wake_detector: Optional[WakeWordDetector] = None
        self._stt: Optional[SpeechToText] = None
        self._tts: Optional[TextToSpeech] = None
        self._intent: Optional[IntentRecognizer] = None
        self._audio: Optional[AudioProcessor] = None
        self._sounds: Optional[SoundEffects] = None
        
        # Audio buffer
        self._audio_buffer = bytearray()
        self._speech_start: Optional[datetime] = None
        self._last_speech: Optional[datetime] = None
        self._wake_time: Optional[datetime] = None
        
        # Conversation
        self._conversation: deque[ConversationTurn] = deque(
            maxlen=self.config.max_context_turns
        )
        self._last_activity = datetime.now()
        
        # Handlers
        self._response_handlers: List[Callable] = []
        self._wake_handlers: List[Callable] = []
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """Start the voice assistant."""
        if self._running:
            return True
        
        logger.info("Starting voice assistant...")
        
        try:
            # Initialize components
            self._audio = AudioProcessor(self.config)
            self._sounds = SoundEffects(self.config)
            await self._sounds.load()
            
            # Initialize wake word detector
            if self.config.wake_enabled:
                if self.config.wake_engine == WakeEngine.VOSK:
                    self._wake_detector = VoskWakeDetector(self.config)
                elif self.config.wake_engine == WakeEngine.PORCUPINE:
                    self._wake_detector = PorcupineWakeDetector(self.config)
                
                if self._wake_detector:
                    if not await self._wake_detector.start():
                        logger.warning("Wake detector not available")
            
            # Initialize STT
            self._stt = SpeechToText(self.config)
            if not await self._stt.start():
                logger.warning("STT not available")
            
            # Initialize TTS
            self._tts = TextToSpeech(self.config)
            if not await self._tts.start():
                logger.warning("TTS not available")
            
            # Initialize intent recognizer
            self._intent = IntentRecognizer(self.config)
            await self._intent.start()
            
            self._running = True
            self._state = AssistantState.WAKE_LISTENING if self.config.wake_enabled else AssistantState.COMMAND_LISTENING
            
            logger.info(f"Voice assistant started (state: {self._state.value})")
            return True
            
        except Exception as e:
            logger.error(f"Voice assistant start error: {e}")
            self._state = AssistantState.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop the voice assistant."""
        self._running = False
        self._state = AssistantState.IDLE
        
        if self._wake_detector:
            await self._wake_detector.stop()
        
        self._audio_buffer.clear()
        logger.info("Voice assistant stopped")
    
    # ============================================
    # Audio Processing
    # ============================================
    
    async def process_audio(self, audio: bytes) -> Optional[AssistantResponse]:
        """
        Process audio chunk.
        
        Args:
            audio: Raw audio bytes (16-bit PCM, 16kHz mono)
            
        Returns:
            AssistantResponse if processing complete
        """
        if not self._running:
            return None
        
        self._last_activity = datetime.now()
        
        # Apply noise reduction
        if self._audio:
            audio = self._audio.reduce_noise(audio)
        
        # State machine
        if self._state == AssistantState.WAKE_LISTENING:
            return await self._handle_wake_listening(audio)
        elif self._state == AssistantState.COMMAND_LISTENING:
            return await self._handle_command_listening(audio)
        
        return None
    
    async def _handle_wake_listening(self, audio: bytes) -> Optional[AssistantResponse]:
        """Handle wake word detection state."""
        if not self._wake_detector:
            self._state = AssistantState.COMMAND_LISTENING
            return None
        
        # Detect wake word
        event = await self._wake_detector.process(audio)
        
        if event:
            logger.info(f"Wake word detected: {event.wake_word}")
            
            # Play wake sound
            await self._sounds.play("wake")
            
            # Notify handlers
            for handler in self._wake_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Wake handler error: {e}")
            
            # Transition to command listening
            self._state = AssistantState.COMMAND_LISTENING
            self._wake_time = datetime.now()
            self._audio_buffer.clear()
            
            await self._sounds.play("start")
        
        return None
    
    async def _handle_command_listening(self, audio: bytes) -> Optional[AssistantResponse]:
        """Handle command listening state."""
        # Check wake timeout
        if self._wake_time and self.config.wake_enabled:
            elapsed = (datetime.now() - self._wake_time).total_seconds()
            if elapsed > self.config.wake_timeout:
                logger.debug("Wake timeout, returning to wake listening")
                self._state = AssistantState.WAKE_LISTENING
                self._wake_time = None
                self._audio_buffer.clear()
                await self._sounds.play("end")
                return None
        
        # Voice activity detection
        is_speech = self._audio.detect_speech(audio) if self._audio else True
        
        if is_speech:
            if not self._speech_start:
                self._speech_start = datetime.now()
            
            self._last_speech = datetime.now()
            self._audio_buffer.extend(audio)
        
        elif self._speech_start:
            # Check for end of utterance
            silence_duration = (datetime.now() - self._last_speech).total_seconds()
            
            if silence_duration >= self.config.vad_silence_duration:
                speech_duration = (self._last_speech - self._speech_start).total_seconds()
                
                if speech_duration >= self.config.vad_min_speech:
                    # Process complete utterance
                    return await self._process_utterance()
                else:
                    # Too short, discard
                    self._reset_audio_state()
        
        return None
    
    async def _process_utterance(self) -> Optional[AssistantResponse]:
        """Process complete utterance."""
        audio_data = bytes(self._audio_buffer)
        self._reset_audio_state()
        
        self._state = AssistantState.PROCESSING
        await self._sounds.play("end")
        
        try:
            # Transcribe
            utterance = await self._stt.transcribe(audio_data) if self._stt else None
            
            if not utterance or not utterance.text:
                self._state = AssistantState.WAKE_LISTENING if self.config.wake_enabled else AssistantState.COMMAND_LISTENING
                return None
            
            logger.info(f"Transcribed: {utterance.text}")
            utterance.audio_data = audio_data
            
            # Recognize intent
            intent = await self._intent.recognize(utterance.text) if self._intent else None
            if intent:
                intent.entities = await self._intent.extract_entities(utterance.text, intent)
            
            # Add to conversation
            self._conversation.append(ConversationTurn(
                role="user",
                content=utterance.text,
                intent=intent
            ))
            
            # Generate response (to be implemented with LLM)
            response_text = await self._generate_response(utterance, intent)
            
            # Add assistant response to conversation
            self._conversation.append(ConversationTurn(
                role="assistant",
                content=response_text
            ))
            
            # TTS
            self._state = AssistantState.SPEAKING
            audio_response = await self._tts.speak(response_text) if self._tts else None
            
            response = AssistantResponse(
                text=response_text,
                audio=audio_response,
                intent=intent,
                utterance=utterance
            )
            
            # Notify handlers
            for handler in self._response_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(response)
                    else:
                        handler(response)
                except Exception as e:
                    logger.error(f"Response handler error: {e}")
            
            # Return to listening
            self._state = AssistantState.WAKE_LISTENING if self.config.wake_enabled else AssistantState.COMMAND_LISTENING
            self._wake_time = None  # Reset wake timeout
            
            return response
            
        except Exception as e:
            logger.error(f"Utterance processing error: {e}")
            self._state = AssistantState.WAKE_LISTENING if self.config.wake_enabled else AssistantState.COMMAND_LISTENING
            await self._sounds.play("error")
            return None
    
    def _reset_audio_state(self) -> None:
        """Reset audio state."""
        self._audio_buffer.clear()
        self._speech_start = None
        self._last_speech = None
    
    async def _generate_response(self, utterance: Utterance, intent: Optional[Intent]) -> str:
        """Generate response using LLM."""
        # This will be connected to the LLM provider
        # For now, return a simple acknowledgment
        
        if intent:
            if intent.category == IntentCategory.QUESTION:
                return f"讓我查一下關於「{utterance.text}」的資訊..."
            elif intent.category == IntentCategory.COMMAND:
                return f"好的，我來執行您的指令..."
            elif intent.category == IntentCategory.CODE:
                return f"了解，我會處理這個程式相關的請求..."
            elif intent.category == IntentCategory.REMINDER:
                return f"好的，我會幫您記住這件事..."
            elif intent.category == IntentCategory.CALENDAR:
                return f"讓我查看您的行程..."
        
        return f"我聽到您說：{utterance.text}"
    
    # ============================================
    # Event Handlers
    # ============================================
    
    def on_wake(self, handler: Callable) -> None:
        """Register wake event handler."""
        self._wake_handlers.append(handler)
    
    def on_response(self, handler: Callable) -> None:
        """Register response handler."""
        self._response_handlers.append(handler)
    
    # ============================================
    # Conversation
    # ============================================
    
    def get_context(self) -> List[Dict[str, str]]:
        """Get conversation context for LLM."""
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self._conversation
        ]
    
    def clear_context(self) -> None:
        """Clear conversation context."""
        self._conversation.clear()
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def state(self) -> AssistantState:
        """Get current state."""
        return self._state
    
    @property
    def is_listening(self) -> bool:
        """Check if actively listening."""
        return self._state in (AssistantState.WAKE_LISTENING, AssistantState.COMMAND_LISTENING)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get assistant statistics."""
        return {
            "state": self._state.value,
            "running": self._running,
            "wake_enabled": self.config.wake_enabled,
            "wake_engine": self.config.wake_engine.value,
            "stt_engine": self.config.stt_engine.value,
            "tts_engine": self.config.tts_engine.value,
            "conversation_turns": len(self._conversation),
            "wake_words": self.config.wake_words,
        }


# ============================================
# Global Instance
# ============================================

_voice_assistant: Optional[VoiceAssistant] = None


def get_voice_assistant(config: VoiceAssistantConfig = None) -> VoiceAssistant:
    """Get or create the global voice assistant instance."""
    global _voice_assistant
    if _voice_assistant is None:
        _voice_assistant = VoiceAssistant(config)
    return _voice_assistant


def reset_voice_assistant() -> None:
    """Reset the global voice assistant instance."""
    global _voice_assistant
    _voice_assistant = None


__all__ = [
    # Enums
    "AssistantState",
    "WakeEngine",
    "STTEngine", 
    "TTSEngine",
    "IntentCategory",
    # Data classes
    "VoiceAssistantConfig",
    "WakeEvent",
    "Utterance",
    "Intent",
    "AssistantResponse",
    "ConversationTurn",
    # Main class
    "VoiceAssistant",
    "get_voice_assistant",
    "reset_voice_assistant",
]
