"""
Talk Mode (Continuous Conversation) for CursorBot

Provides:
- Continuous voice conversation mode
- Push-to-talk (PTT) support
- Voice activity detection (VAD)
- Real-time speech-to-text
- Text-to-speech responses
- Conversation context preservation

Usage:
    from src.core.talk_mode import get_talk_mode_manager
    
    talk = get_talk_mode_manager()
    
    # Start talk mode
    await talk.start()
    
    # Process audio
    await talk.process_audio(audio_data)
    
    # Stop talk mode
    await talk.stop()
"""

import os
import asyncio
import struct
import wave
import tempfile
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from collections import deque

from ..utils.logger import logger


class TalkModeState(Enum):
    """Talk mode states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    PAUSED = "paused"
    ERROR = "error"


class ActivationMode(Enum):
    """How talk mode is activated."""
    VOICE_WAKE = "voice_wake"  # Wake word detection
    PTT = "ptt"  # Push-to-talk
    VAD = "vad"  # Voice activity detection
    CONTINUOUS = "continuous"  # Always listening


@dataclass
class TalkConfig:
    """Talk mode configuration."""
    activation_mode: ActivationMode = ActivationMode.VAD
    
    # Audio settings
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    
    # Voice activity detection
    vad_threshold: float = 0.02  # Energy threshold
    vad_silence_duration: float = 1.5  # Seconds of silence to end utterance
    vad_min_speech_duration: float = 0.3  # Minimum speech duration
    
    # Speech recognition
    stt_provider: str = "whisper"  # whisper, google, azure, vosk
    stt_language: str = "en"
    
    # Text-to-speech
    tts_provider: str = "elevenlabs"  # elevenlabs, google, azure, edge
    tts_voice: str = "Rachel"
    tts_speed: float = 1.0
    
    # Conversation
    conversation_timeout: int = 300  # Seconds before context reset
    max_conversation_turns: int = 50
    
    # Wake word (if using voice wake)
    wake_words: list[str] = field(default_factory=lambda: ["hey cursor", "ok cursor"])


@dataclass
class Utterance:
    """Represents a spoken utterance."""
    text: str
    audio_data: bytes
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0
    confidence: float = 1.0
    is_final: bool = True


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    audio_duration: float = 0.0


class TalkModeManager:
    """
    Manages continuous conversation (talk mode).
    
    Provides seamless voice interaction with:
    - Speech-to-text transcription
    - LLM response generation
    - Text-to-speech output
    """
    
    def __init__(self, config: TalkConfig = None):
        """
        Initialize talk mode manager.
        
        Args:
            config: Talk mode configuration
        """
        self.config = config or TalkConfig()
        
        self._state = TalkModeState.IDLE
        self._running = False
        
        # Audio buffers
        self._audio_buffer = bytearray()
        self._speech_start_time: Optional[datetime] = None
        self._last_speech_time: Optional[datetime] = None
        
        # Conversation history
        self._conversation: deque[ConversationTurn] = deque(
            maxlen=self.config.max_conversation_turns
        )
        self._last_activity = datetime.now()
        
        # Handlers
        self._transcription_handlers: list[Callable] = []
        self._response_handlers: list[Callable] = []
        
        # Components
        self._stt = None
        self._tts = None
        self._llm = None
    
    # ============================================
    # Lifecycle
    # ============================================
    
    async def start(self) -> bool:
        """
        Start talk mode.
        
        Returns:
            True if started successfully
        """
        if self._running:
            return True
        
        try:
            # Initialize STT
            self._stt = await self._init_stt()
            if not self._stt:
                logger.warning("STT not available, talk mode limited")
            
            # Initialize TTS
            self._tts = await self._init_tts()
            if not self._tts:
                logger.warning("TTS not available, no voice output")
            
            self._running = True
            self._state = TalkModeState.LISTENING
            self._last_activity = datetime.now()
            
            logger.info(f"Talk mode started ({self.config.activation_mode.value})")
            return True
            
        except Exception as e:
            logger.error(f"Talk mode start error: {e}")
            self._state = TalkModeState.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop talk mode."""
        self._running = False
        self._state = TalkModeState.IDLE
        self._audio_buffer.clear()
        
        logger.info("Talk mode stopped")
    
    async def pause(self) -> None:
        """Pause talk mode (keep context)."""
        if self._running:
            self._state = TalkModeState.PAUSED
            logger.debug("Talk mode paused")
    
    async def resume(self) -> None:
        """Resume talk mode."""
        if self._running and self._state == TalkModeState.PAUSED:
            self._state = TalkModeState.LISTENING
            logger.debug("Talk mode resumed")
    
    # ============================================
    # Speech-to-Text
    # ============================================
    
    async def _init_stt(self) -> Optional[Any]:
        """Initialize speech-to-text provider."""
        provider = self.config.stt_provider.lower()
        
        if provider == "whisper":
            return await self._init_whisper_stt()
        elif provider == "vosk":
            return await self._init_vosk_stt()
        elif provider == "google":
            return await self._init_google_stt()
        
        return None
    
    async def _init_whisper_stt(self) -> Optional[Any]:
        """Initialize Whisper STT."""
        try:
            import whisper
            model = whisper.load_model("base")
            return {"type": "whisper", "model": model}
        except ImportError:
            logger.debug("whisper not installed")
            return None
    
    async def _init_vosk_stt(self) -> Optional[Any]:
        """Initialize Vosk STT."""
        try:
            from vosk import Model, KaldiRecognizer
            
            model_path = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-en")
            if not os.path.exists(model_path):
                return None
            
            model = Model(model_path)
            recognizer = KaldiRecognizer(model, self.config.sample_rate)
            
            return {"type": "vosk", "model": model, "recognizer": recognizer}
        except ImportError:
            return None
    
    async def _init_google_stt(self) -> Optional[Any]:
        """Initialize Google Cloud STT."""
        try:
            from google.cloud import speech
            
            client = speech.SpeechClient()
            return {"type": "google", "client": client}
        except Exception:
            return None
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            
        Returns:
            Transcribed text or None
        """
        if not self._stt:
            return None
        
        try:
            stt_type = self._stt.get("type")
            
            if stt_type == "whisper":
                return await self._transcribe_whisper(audio_data)
            elif stt_type == "vosk":
                return await self._transcribe_vosk(audio_data)
            elif stt_type == "google":
                return await self._transcribe_google(audio_data)
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        
        return None
    
    async def _transcribe_whisper(self, audio_data: bytes) -> Optional[str]:
        """Transcribe with Whisper."""
        model = self._stt["model"]
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            with wave.open(f.name, "wb") as wav:
                wav.setnchannels(self.config.channels)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(self.config.sample_rate)
                wav.writeframes(audio_data)
            
            # Transcribe
            result = model.transcribe(
                f.name,
                language=self.config.stt_language,
            )
            
            # Cleanup
            os.unlink(f.name)
            
            return result.get("text", "").strip()
    
    async def _transcribe_vosk(self, audio_data: bytes) -> Optional[str]:
        """Transcribe with Vosk."""
        import json
        
        recognizer = self._stt["recognizer"]
        
        if recognizer.AcceptWaveform(audio_data):
            result = json.loads(recognizer.Result())
            return result.get("text", "").strip()
        
        return None
    
    async def _transcribe_google(self, audio_data: bytes) -> Optional[str]:
        """Transcribe with Google Cloud."""
        from google.cloud import speech
        
        client = self._stt["client"]
        
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.config.sample_rate,
            language_code=self.config.stt_language,
        )
        
        response = client.recognize(config=config, audio=audio)
        
        if response.results:
            return response.results[0].alternatives[0].transcript
        
        return None
    
    # ============================================
    # Text-to-Speech
    # ============================================
    
    async def _init_tts(self) -> Optional[Any]:
        """Initialize text-to-speech provider."""
        provider = self.config.tts_provider.lower()
        
        if provider == "elevenlabs":
            return await self._init_elevenlabs_tts()
        elif provider == "edge":
            return await self._init_edge_tts()
        elif provider == "google":
            return await self._init_google_tts()
        
        return None
    
    async def _init_elevenlabs_tts(self) -> Optional[Any]:
        """Initialize ElevenLabs TTS."""
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return None
        
        return {
            "type": "elevenlabs",
            "api_key": api_key,
            "voice": self.config.tts_voice,
        }
    
    async def _init_edge_tts(self) -> Optional[Any]:
        """Initialize Edge TTS (free)."""
        try:
            import edge_tts
            return {"type": "edge"}
        except ImportError:
            return None
    
    async def _init_google_tts(self) -> Optional[Any]:
        """Initialize Google Cloud TTS."""
        try:
            from google.cloud import texttospeech
            client = texttospeech.TextToSpeechClient()
            return {"type": "google", "client": client}
        except Exception:
            return None
    
    async def speak(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech.
        
        Args:
            text: Text to speak
            
        Returns:
            Audio bytes or None
        """
        if not self._tts:
            return None
        
        try:
            self._state = TalkModeState.SPEAKING
            
            tts_type = self._tts.get("type")
            
            if tts_type == "elevenlabs":
                audio = await self._speak_elevenlabs(text)
            elif tts_type == "edge":
                audio = await self._speak_edge(text)
            elif tts_type == "google":
                audio = await self._speak_google(text)
            else:
                audio = None
            
            self._state = TalkModeState.LISTENING
            return audio
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            self._state = TalkModeState.LISTENING
            return None
    
    async def _speak_elevenlabs(self, text: str) -> Optional[bytes]:
        """Generate speech with ElevenLabs."""
        import httpx
        
        api_key = self._tts["api_key"]
        voice = self._tts["voice"]
        
        # Get voice ID (simplified - in production, cache this)
        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel default
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                },
            )
            
            if response.status_code == 200:
                return response.content
        
        return None
    
    async def _speak_edge(self, text: str) -> Optional[bytes]:
        """Generate speech with Edge TTS."""
        import edge_tts
        
        voice = "en-US-AriaNeural"
        communicate = edge_tts.Communicate(text, voice)
        
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        
        return bytes(audio_data)
    
    async def _speak_google(self, text: str) -> Optional[bytes]:
        """Generate speech with Google Cloud TTS."""
        from google.cloud import texttospeech
        
        client = self._tts["client"]
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        
        return response.audio_content
    
    # ============================================
    # Audio Processing
    # ============================================
    
    async def process_audio(self, audio_data: bytes) -> Optional[Utterance]:
        """
        Process incoming audio chunk.
        
        Uses VAD to detect speech and triggers transcription
        when utterance is complete.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            
        Returns:
            Utterance if speech detected and transcribed
        """
        if not self._running or self._state == TalkModeState.PAUSED:
            return None
        
        self._last_activity = datetime.now()
        
        # Voice activity detection
        is_speech = self._detect_speech(audio_data)
        
        if is_speech:
            # Start of speech
            if not self._speech_start_time:
                self._speech_start_time = datetime.now()
            
            self._last_speech_time = datetime.now()
            self._audio_buffer.extend(audio_data)
            
        elif self._speech_start_time:
            # Silence after speech
            silence_duration = (datetime.now() - self._last_speech_time).total_seconds()
            
            if silence_duration >= self.config.vad_silence_duration:
                # End of utterance
                speech_duration = (self._last_speech_time - self._speech_start_time).total_seconds()
                
                if speech_duration >= self.config.vad_min_speech_duration:
                    # Transcribe
                    audio = bytes(self._audio_buffer)
                    self._audio_buffer.clear()
                    self._speech_start_time = None
                    
                    self._state = TalkModeState.PROCESSING
                    text = await self.transcribe(audio)
                    self._state = TalkModeState.LISTENING
                    
                    if text:
                        utterance = Utterance(
                            text=text,
                            audio_data=audio,
                            duration=speech_duration,
                        )
                        
                        # Notify handlers
                        await self._handle_utterance(utterance)
                        
                        return utterance
                else:
                    # Too short, discard
                    self._audio_buffer.clear()
                    self._speech_start_time = None
        
        return None
    
    def _detect_speech(self, audio_data: bytes) -> bool:
        """
        Detect if audio contains speech using energy-based VAD.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            True if speech detected
        """
        # Convert to samples
        samples = struct.unpack(f"{len(audio_data) // 2}h", audio_data)
        
        # Calculate RMS energy
        if not samples:
            return False
        
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        
        # Normalize (16-bit audio max is 32767)
        normalized_rms = rms / 32767.0
        
        return normalized_rms > self.config.vad_threshold
    
    # ============================================
    # Conversation
    # ============================================
    
    async def _handle_utterance(self, utterance: Utterance) -> None:
        """Handle a transcribed utterance."""
        # Add to conversation
        self._conversation.append(ConversationTurn(
            role="user",
            content=utterance.text,
            audio_duration=utterance.duration,
        ))
        
        # Notify handlers
        for handler in self._transcription_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(utterance)
                else:
                    handler(utterance)
            except Exception as e:
                logger.error(f"Transcription handler error: {e}")
    
    async def respond(self, text: str) -> Optional[bytes]:
        """
        Generate and speak a response.
        
        Args:
            text: Response text
            
        Returns:
            Audio bytes if TTS available
        """
        # Add to conversation
        self._conversation.append(ConversationTurn(
            role="assistant",
            content=text,
        ))
        
        # Speak
        audio = await self.speak(text)
        
        # Notify handlers
        for handler in self._response_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(text, audio)
                else:
                    handler(text, audio)
            except Exception as e:
                logger.error(f"Response handler error: {e}")
        
        return audio
    
    def get_conversation_context(self) -> list[dict]:
        """Get conversation history for LLM context."""
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self._conversation
        ]
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self._conversation.clear()
        logger.debug("Conversation cleared")
    
    # ============================================
    # Event Handlers
    # ============================================
    
    def on_transcription(self, handler: Callable) -> None:
        """Register a transcription handler."""
        self._transcription_handlers.append(handler)
    
    def on_response(self, handler: Callable) -> None:
        """Register a response handler."""
        self._response_handlers.append(handler)
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def state(self) -> TalkModeState:
        """Get current state."""
        return self._state
    
    @property
    def is_active(self) -> bool:
        """Check if talk mode is active."""
        return self._running and self._state != TalkModeState.PAUSED
    
    def get_stats(self) -> dict:
        """Get talk mode statistics."""
        return {
            "state": self._state.value,
            "running": self._running,
            "activation_mode": self.config.activation_mode.value,
            "conversation_turns": len(self._conversation),
            "stt_provider": self.config.stt_provider,
            "tts_provider": self.config.tts_provider,
            "has_stt": self._stt is not None,
            "has_tts": self._tts is not None,
        }


# ============================================
# Global Instance
# ============================================

_talk_mode_manager: Optional[TalkModeManager] = None


def get_talk_mode_manager() -> TalkModeManager:
    """Get the global talk mode manager instance."""
    global _talk_mode_manager
    if _talk_mode_manager is None:
        _talk_mode_manager = TalkModeManager()
    return _talk_mode_manager


__all__ = [
    "TalkModeState",
    "ActivationMode",
    "TalkConfig",
    "Utterance",
    "ConversationTurn",
    "TalkModeManager",
    "get_talk_mode_manager",
]
