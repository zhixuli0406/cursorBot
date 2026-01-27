"""
Discord Voice Channel Integration for CursorBot

Provides:
- Voice channel joining/leaving
- Real-time voice listening
- Speech-to-text transcription
- Voice activity detection
"""

import asyncio
import io
import wave
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class VoiceState(Enum):
    """Voice connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LISTENING = "listening"
    PROCESSING = "processing"


@dataclass
class VoiceConfig:
    """Discord voice configuration."""
    # Audio settings
    sample_rate: int = 48000  # Discord uses 48kHz
    channels: int = 2  # Stereo
    sample_width: int = 2  # 16-bit
    
    # Listening settings
    silence_threshold: float = 500  # RMS threshold for silence
    silence_duration: float = 1.5  # Seconds of silence to end utterance
    min_speech_duration: float = 0.5  # Minimum speech to process
    max_speech_duration: float = 30.0  # Maximum recording length
    
    # Transcription
    transcription_model: str = "whisper"  # whisper, google, azure
    whisper_model_size: str = "base"  # tiny, base, small, medium, large


@dataclass
class VoiceUtterance:
    """Represents a detected voice utterance."""
    user_id: int
    username: str
    audio_data: bytes
    duration: float
    timestamp: datetime = field(default_factory=datetime.now)
    transcript: str = ""
    confidence: float = 0.0


class DiscordVoiceListener:
    """
    Listens to Discord voice channels and processes speech.
    """
    
    def __init__(self, bot, config: VoiceConfig = None):
        self.bot = bot
        self.config = config or VoiceConfig()
        self._voice_client = None
        self._state = VoiceState.DISCONNECTED
        self._audio_buffers: dict[int, list[bytes]] = {}  # user_id -> audio chunks
        self._speech_handlers: list[Callable] = []
        self._transcriber = None
        self._listening_task = None
    
    # ============================================
    # Connection Management
    # ============================================
    
    async def join_channel(self, channel) -> bool:
        """
        Join a voice channel.
        
        Args:
            channel: Discord voice channel object
        
        Returns:
            True if joined successfully
        """
        try:
            self._state = VoiceState.CONNECTING
            
            # Connect to voice channel
            self._voice_client = await channel.connect()
            
            # Start receiving audio
            self._voice_client.start_recording(
                self._create_sink(),
                self._on_audio_received,
                channel,
            )
            
            self._state = VoiceState.CONNECTED
            logger.info(f"Joined voice channel: {channel.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to join voice channel: {e}")
            self._state = VoiceState.DISCONNECTED
            return False
    
    async def leave_channel(self) -> None:
        """Leave the current voice channel."""
        if self._voice_client:
            try:
                if self._voice_client.is_connected():
                    self._voice_client.stop_recording()
                    await self._voice_client.disconnect()
            except Exception as e:
                logger.error(f"Error leaving channel: {e}")
            finally:
                self._voice_client = None
        
        self._state = VoiceState.DISCONNECTED
        self._audio_buffers.clear()
        logger.info("Left voice channel")
    
    def _create_sink(self):
        """Create audio sink for recording."""
        try:
            import discord
            
            # Use BasicSink which stores audio per user
            return discord.sinks.WaveSink()
        except Exception as e:
            logger.error(f"Failed to create sink: {e}")
            return None
    
    # ============================================
    # Audio Processing
    # ============================================
    
    async def _on_audio_received(self, sink, channel, *args):
        """Called when recording stops."""
        for user_id, audio in sink.audio_data.items():
            # Get user info
            user = self.bot.get_user(user_id)
            username = user.name if user else str(user_id)
            
            # Convert to bytes
            audio_bytes = audio.file.getvalue()
            duration = len(audio_bytes) / (self.config.sample_rate * self.config.channels * self.config.sample_width)
            
            # Skip if too short
            if duration < self.config.min_speech_duration:
                continue
            
            # Create utterance
            utterance = VoiceUtterance(
                user_id=user_id,
                username=username,
                audio_data=audio_bytes,
                duration=duration,
            )
            
            # Transcribe
            await self._process_utterance(utterance)
    
    async def _process_utterance(self, utterance: VoiceUtterance) -> None:
        """Process a voice utterance."""
        self._state = VoiceState.PROCESSING
        
        try:
            # Transcribe audio
            transcript = await self._transcribe(utterance.audio_data)
            utterance.transcript = transcript
            
            if transcript:
                logger.info(f"[{utterance.username}]: {transcript}")
                
                # Call handlers
                for handler in self._speech_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(utterance)
                        else:
                            handler(utterance)
                    except Exception as e:
                        logger.error(f"Speech handler error: {e}")
        
        except Exception as e:
            logger.error(f"Utterance processing error: {e}")
        
        finally:
            self._state = VoiceState.LISTENING
    
    # ============================================
    # Transcription
    # ============================================
    
    async def _transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text."""
        if self.config.transcription_model == "whisper":
            return await self._transcribe_whisper(audio_data)
        elif self.config.transcription_model == "google":
            return await self._transcribe_google(audio_data)
        else:
            logger.warning(f"Unknown transcription model: {self.config.transcription_model}")
            return ""
    
    async def _transcribe_whisper(self, audio_data: bytes) -> str:
        """Transcribe using OpenAI Whisper."""
        try:
            import whisper
            import numpy as np
            import tempfile
            import os
            
            # Load model if not loaded
            if self._transcriber is None:
                self._transcriber = whisper.load_model(self.config.whisper_model_size)
            
            # Save to temp file (Whisper needs file path)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                # Write WAV header and data
                with wave.open(f.name, 'wb') as wav:
                    wav.setnchannels(self.config.channels)
                    wav.setsampwidth(self.config.sample_width)
                    wav.setframerate(self.config.sample_rate)
                    wav.writeframes(audio_data)
                
                temp_path = f.name
            
            try:
                # Transcribe
                result = self._transcriber.transcribe(
                    temp_path,
                    fp16=False,
                    language=None,  # Auto-detect
                )
                return result["text"].strip()
            finally:
                os.unlink(temp_path)
                
        except ImportError:
            logger.error("whisper not installed. Run: pip install openai-whisper")
            return await self._transcribe_openai_api(audio_data)
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""
    
    async def _transcribe_openai_api(self, audio_data: bytes) -> str:
        """Transcribe using OpenAI API."""
        import os
        import httpx
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ""
        
        try:
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav:
                wav.setnchannels(self.config.channels)
                wav.setsampwidth(self.config.sample_width)
                wav.setframerate(self.config.sample_rate)
                wav.writeframes(audio_data)
            
            wav_buffer.seek(0)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": ("audio.wav", wav_buffer, "audio/wav")},
                    data={"model": "whisper-1"},
                    timeout=30,
                )
                
                if response.status_code == 200:
                    return response.json().get("text", "")
                else:
                    logger.error(f"OpenAI API error: {response.status_code}")
                    return ""
                    
        except Exception as e:
            logger.error(f"OpenAI API transcription error: {e}")
            return ""
    
    async def _transcribe_google(self, audio_data: bytes) -> str:
        """Transcribe using Google Speech-to-Text."""
        try:
            from google.cloud import speech
            
            client = speech.SpeechClient()
            
            audio = speech.RecognitionAudio(content=audio_data)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.config.sample_rate,
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
            
            response = client.recognize(config=config, audio=audio)
            
            if response.results:
                return response.results[0].alternatives[0].transcript
            return ""
            
        except ImportError:
            logger.error("google-cloud-speech not installed")
            return ""
        except Exception as e:
            logger.error(f"Google transcription error: {e}")
            return ""
    
    # ============================================
    # Event Handlers
    # ============================================
    
    def on_speech(self, handler: Callable) -> None:
        """
        Register a speech handler.
        
        Handler signature: (utterance: VoiceUtterance) -> None
        """
        self._speech_handlers.append(handler)
    
    # ============================================
    # Continuous Listening
    # ============================================
    
    async def start_continuous_listening(self) -> None:
        """Start continuous listening mode."""
        if not self._voice_client or not self._voice_client.is_connected():
            logger.warning("Not connected to voice channel")
            return
        
        self._state = VoiceState.LISTENING
        
        # Recording is handled by discord.py's recording feature
        # We just need to process the callbacks
        logger.info("Started continuous listening")
    
    async def stop_continuous_listening(self) -> None:
        """Stop continuous listening mode."""
        if self._voice_client:
            try:
                self._voice_client.stop_recording()
            except:
                pass
        
        self._state = VoiceState.CONNECTED
        logger.info("Stopped continuous listening")
    
    # ============================================
    # Status
    # ============================================
    
    @property
    def state(self) -> VoiceState:
        return self._state
    
    @property
    def is_connected(self) -> bool:
        return self._voice_client and self._voice_client.is_connected()
    
    @property
    def is_listening(self) -> bool:
        return self._state == VoiceState.LISTENING
    
    def get_stats(self) -> dict:
        return {
            "state": self._state.value,
            "connected": self.is_connected,
            "channel": self._voice_client.channel.name if self.is_connected else None,
            "handlers": len(self._speech_handlers),
        }


# ============================================
# Discord Bot Integration
# ============================================

def setup_voice_commands(bot, voice_listener: DiscordVoiceListener):
    """
    Set up Discord voice commands.
    
    Args:
        bot: Discord bot instance
        voice_listener: Voice listener instance
    """
    try:
        import discord
        from discord.ext import commands
        
        @bot.command(name="join")
        async def join_voice(ctx):
            """Join the user's voice channel."""
            if not ctx.author.voice:
                await ctx.send("You need to be in a voice channel!")
                return
            
            channel = ctx.author.voice.channel
            
            if await voice_listener.join_channel(channel):
                await ctx.send(f"Joined {channel.name}! I'm now listening.")
                await voice_listener.start_continuous_listening()
            else:
                await ctx.send("Failed to join voice channel.")
        
        @bot.command(name="leave")
        async def leave_voice(ctx):
            """Leave the voice channel."""
            await voice_listener.leave_channel()
            await ctx.send("Left the voice channel.")
        
        @bot.command(name="listen")
        async def toggle_listen(ctx):
            """Toggle listening mode."""
            if voice_listener.is_listening:
                await voice_listener.stop_continuous_listening()
                await ctx.send("Stopped listening.")
            else:
                await voice_listener.start_continuous_listening()
                await ctx.send("Started listening!")
        
        logger.info("Discord voice commands registered")
        
    except ImportError:
        logger.warning("discord.py not installed")
    except Exception as e:
        logger.error(f"Failed to setup voice commands: {e}")


__all__ = [
    "VoiceState",
    "VoiceConfig",
    "VoiceUtterance",
    "DiscordVoiceListener",
    "setup_voice_commands",
]
