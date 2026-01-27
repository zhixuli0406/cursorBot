"""
Voice Wake System for CursorBot

Provides:
- Wake word detection
- Voice activity detection
- Continuous listening mode
- Audio stream processing
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from ..utils.logger import logger


class WakeWordEngine(Enum):
    """Supported wake word engines."""
    PORCUPINE = "porcupine"  # Picovoice Porcupine
    SNOWBOY = "snowboy"      # Snowboy (deprecated but still works)
    VOSK = "vosk"            # Vosk offline
    CUSTOM = "custom"        # Custom keyword spotting


class ListeningState(Enum):
    """Voice listening states."""
    IDLE = "idle"
    LISTENING = "listening"
    WAKE_DETECTED = "wake_detected"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class WakeConfig:
    """Voice wake configuration."""
    engine: WakeWordEngine = WakeWordEngine.VOSK
    wake_words: list[str] = field(default_factory=lambda: ["hey cursor", "ok cursor"])
    sensitivity: float = 0.5  # 0.0 to 1.0
    timeout_seconds: int = 10  # After wake, listen for this long
    sample_rate: int = 16000
    chunk_size: int = 1024
    
    # Engine-specific
    porcupine_access_key: str = ""
    vosk_model_path: str = ""


@dataclass
class WakeEvent:
    """Wake word detection event."""
    wake_word: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    audio_data: bytes = b""


class VoiceWakeManager:
    """
    Manages voice wake word detection.
    """
    
    def __init__(self, config: WakeConfig = None):
        self.config = config or WakeConfig()
        self._state = ListeningState.IDLE
        self._wake_handlers: list[Callable] = []
        self._running = False
        self._detector = None
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """
        Start voice wake detection.
        
        Returns:
            True if started successfully
        """
        if self._running:
            return True
        
        try:
            # Initialize detector based on engine
            if self.config.engine == WakeWordEngine.VOSK:
                self._detector = await self._init_vosk()
            elif self.config.engine == WakeWordEngine.PORCUPINE:
                self._detector = await self._init_porcupine()
            else:
                logger.warning(f"Unsupported engine: {self.config.engine}")
                return False
            
            self._running = True
            self._state = ListeningState.LISTENING
            logger.info(f"Voice wake started with {self.config.engine.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Voice wake start error: {e}")
            self._state = ListeningState.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop voice wake detection."""
        self._running = False
        self._state = ListeningState.IDLE
        self._detector = None
        logger.info("Voice wake stopped")
    
    # ============================================
    # Engine Initialization
    # ============================================
    
    async def _init_vosk(self):
        """Initialize Vosk engine."""
        try:
            from vosk import Model, KaldiRecognizer
            import json
            
            model_path = self.config.vosk_model_path or "models/vosk-model-small-en"
            
            # Check if model exists
            import os
            if not os.path.exists(model_path):
                logger.warning(f"Vosk model not found at {model_path}")
                logger.info("Download from: https://alphacephei.com/vosk/models")
                return None
            
            model = Model(model_path)
            recognizer = KaldiRecognizer(model, self.config.sample_rate)
            
            return {
                "model": model,
                "recognizer": recognizer,
            }
            
        except ImportError:
            logger.error("vosk not installed. Run: pip install vosk")
            return None
        except Exception as e:
            logger.error(f"Vosk init error: {e}")
            return None
    
    async def _init_porcupine(self):
        """Initialize Porcupine engine."""
        try:
            import pvporcupine
            
            if not self.config.porcupine_access_key:
                logger.error("Porcupine access key not configured")
                return None
            
            # Create porcupine instance
            porcupine = pvporcupine.create(
                access_key=self.config.porcupine_access_key,
                keywords=self.config.wake_words,
                sensitivities=[self.config.sensitivity] * len(self.config.wake_words),
            )
            
            return {
                "porcupine": porcupine,
            }
            
        except ImportError:
            logger.error("pvporcupine not installed. Run: pip install pvporcupine")
            return None
        except Exception as e:
            logger.error(f"Porcupine init error: {e}")
            return None
    
    # ============================================
    # Audio Processing
    # ============================================
    
    async def process_audio(self, audio_data: bytes) -> Optional[WakeEvent]:
        """
        Process audio chunk for wake word detection.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM)
        
        Returns:
            WakeEvent if wake word detected, None otherwise
        """
        if not self._running or not self._detector:
            return None
        
        try:
            if self.config.engine == WakeWordEngine.VOSK:
                return await self._process_vosk(audio_data)
            elif self.config.engine == WakeWordEngine.PORCUPINE:
                return await self._process_porcupine(audio_data)
            
        except Exception as e:
            logger.error(f"Audio process error: {e}")
        
        return None
    
    async def _process_vosk(self, audio_data: bytes) -> Optional[WakeEvent]:
        """Process audio with Vosk."""
        import json
        
        recognizer = self._detector["recognizer"]
        
        if recognizer.AcceptWaveform(audio_data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").lower()
            
            # Check for wake words
            for wake_word in self.config.wake_words:
                if wake_word.lower() in text:
                    event = WakeEvent(
                        wake_word=wake_word,
                        confidence=0.8,  # Vosk doesn't provide confidence
                        audio_data=audio_data,
                    )
                    await self._trigger_wake(event)
                    return event
        
        return None
    
    async def _process_porcupine(self, audio_data: bytes) -> Optional[WakeEvent]:
        """Process audio with Porcupine."""
        import struct
        
        porcupine = self._detector["porcupine"]
        
        # Convert bytes to int16 array
        pcm = struct.unpack_from(f"{len(audio_data) // 2}h", audio_data)
        
        # Process frame
        keyword_index = porcupine.process(pcm)
        
        if keyword_index >= 0:
            wake_word = self.config.wake_words[keyword_index]
            event = WakeEvent(
                wake_word=wake_word,
                confidence=self.config.sensitivity,
                audio_data=audio_data,
            )
            await self._trigger_wake(event)
            return event
        
        return None
    
    # ============================================
    # Event Handling
    # ============================================
    
    def on_wake(self, handler: Callable) -> None:
        """Register a wake event handler."""
        self._wake_handlers.append(handler)
    
    async def _trigger_wake(self, event: WakeEvent) -> None:
        """Trigger wake event handlers."""
        self._state = ListeningState.WAKE_DETECTED
        
        for handler in self._wake_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Wake handler error: {e}")
        
        self._state = ListeningState.LISTENING
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def state(self) -> ListeningState:
        """Get current listening state."""
        return self._state
    
    @property
    def is_listening(self) -> bool:
        """Check if actively listening."""
        return self._running and self._state == ListeningState.LISTENING
    
    def get_stats(self) -> dict:
        """Get voice wake statistics."""
        return {
            "state": self._state.value,
            "running": self._running,
            "engine": self.config.engine.value,
            "wake_words": self.config.wake_words,
            "handlers": len(self._wake_handlers),
        }


# ============================================
# Global Instance
# ============================================

_voice_wake_manager: Optional[VoiceWakeManager] = None


def get_voice_wake_manager() -> VoiceWakeManager:
    """Get the global voice wake manager instance."""
    global _voice_wake_manager
    if _voice_wake_manager is None:
        _voice_wake_manager = VoiceWakeManager()
    return _voice_wake_manager


__all__ = [
    "WakeWordEngine",
    "ListeningState",
    "WakeConfig",
    "WakeEvent",
    "VoiceWakeManager",
    "get_voice_wake_manager",
]
