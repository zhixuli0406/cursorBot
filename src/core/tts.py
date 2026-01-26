"""
Text-to-Speech (TTS) System for CursorBot

Provides:
- Text to speech conversion
- Multiple TTS provider support (OpenAI, Google, Edge TTS)
- Voice selection and configuration
- Audio format conversion
"""

import asyncio
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from ..utils.logger import logger


class TTSProvider(Enum):
    """Supported TTS providers."""
    OPENAI = "openai"
    GOOGLE = "google"
    EDGE = "edge"
    ELEVENLABS = "elevenlabs"


@dataclass
class TTSConfig:
    """Configuration for TTS."""
    provider: TTSProvider = TTSProvider.OPENAI
    voice: str = "alloy"  # OpenAI default voice
    model: str = "tts-1"  # OpenAI TTS model
    speed: float = 1.0
    format: str = "mp3"  # Output format
    api_key: Optional[str] = None
    

@dataclass
class TTSResult:
    """Result from TTS generation."""
    audio_path: str
    duration_seconds: Optional[float] = None
    format: str = "mp3"
    provider: str = ""
    voice: str = ""
    text_length: int = 0


class BaseTTSProvider(ABC):
    """Base class for TTS providers."""
    
    def __init__(self, config: TTSConfig):
        self.config = config
    
    @abstractmethod
    async def synthesize(self, text: str, output_path: str = None) -> TTSResult:
        """
        Convert text to speech.
        
        Args:
            text: Text to convert
            output_path: Optional path to save audio
        
        Returns:
            TTSResult with audio path and metadata
        """
        pass
    
    @abstractmethod
    def get_available_voices(self) -> list[str]:
        """Get list of available voices."""
        pass


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS provider."""
    
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    MODELS = ["tts-1", "tts-1-hd"]
    
    def get_available_voices(self) -> list[str]:
        return self.VOICES
    
    async def synthesize(self, text: str, output_path: str = None) -> TTSResult:
        import httpx
        
        api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Validate voice
        voice = self.config.voice
        if voice not in self.VOICES:
            voice = "alloy"
        
        # Validate model
        model = self.config.model
        if model not in self.MODELS:
            model = "tts-1"
        
        # Prepare output path
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=f".{self.config.format}")
            os.close(fd)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "input": text,
                        "voice": voice,
                        "speed": self.config.speed,
                        "response_format": self.config.format,
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI TTS error: {response.status_code} - {response.text}")
                    raise ValueError(f"OpenAI TTS error: {response.status_code}")
                
                # Write audio file
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                return TTSResult(
                    audio_path=output_path,
                    format=self.config.format,
                    provider="openai",
                    voice=voice,
                    text_length=len(text),
                )
                
        except httpx.TimeoutException:
            raise ValueError("OpenAI TTS request timed out")
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise


class EdgeTTSProvider(BaseTTSProvider):
    """Microsoft Edge TTS provider (free, no API key required)."""
    
    # Common voices
    VOICES = {
        "en-US": [
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-US-AriaNeural",
            "en-US-DavisNeural",
        ],
        "zh-TW": [
            "zh-TW-HsiaoChenNeural",
            "zh-TW-YunJheNeural",
            "zh-TW-HsiaoYuNeural",
        ],
        "zh-CN": [
            "zh-CN-XiaoxiaoNeural",
            "zh-CN-YunxiNeural",
            "zh-CN-YunyangNeural",
        ],
        "ja-JP": [
            "ja-JP-NanamiNeural",
            "ja-JP-KeitaNeural",
        ],
    }
    
    def get_available_voices(self) -> list[str]:
        voices = []
        for locale_voices in self.VOICES.values():
            voices.extend(locale_voices)
        return voices
    
    async def synthesize(self, text: str, output_path: str = None) -> TTSResult:
        try:
            import edge_tts
        except ImportError:
            raise ValueError("edge-tts not installed. Run: pip install edge-tts")
        
        # Use configured voice or default
        voice = self.config.voice
        if voice not in self.get_available_voices():
            voice = "en-US-JennyNeural"
        
        # Prepare output path
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
        
        try:
            communicate = edge_tts.Communicate(text, voice, rate=f"+{int((self.config.speed - 1) * 100)}%")
            await communicate.save(output_path)
            
            return TTSResult(
                audio_path=output_path,
                format="mp3",
                provider="edge",
                voice=voice,
                text_length=len(text),
            )
            
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            raise


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs TTS provider (high quality voices)."""
    
    VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",
        "domi": "AZnzlk1XvdvUeBnXmlld",
        "bella": "EXAVITQu4vr4xnSDxMaL",
        "antoni": "ErXwobaYiN019PkySvjV",
        "elli": "MF3mGyEYCl7XYWbV9V6O",
        "josh": "TxGEqnHWrfWFTfGW9XjX",
        "arnold": "VR6AewLTigWG4xSOukaG",
        "adam": "pNInz6obpgDQGcFmaJgB",
        "sam": "yoZ06aMxZJJ28mfd3POQ",
    }
    
    def get_available_voices(self) -> list[str]:
        return list(self.VOICES.keys())
    
    async def synthesize(self, text: str, output_path: str = None) -> TTSResult:
        import httpx
        
        api_key = self.config.api_key or os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        # Get voice ID
        voice = self.config.voice.lower()
        voice_id = self.VOICES.get(voice, self.VOICES["rachel"])
        
        # Prepare output path
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.5,
                        }
                    },
                )
                
                if response.status_code != 200:
                    raise ValueError(f"ElevenLabs TTS error: {response.status_code}")
                
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                return TTSResult(
                    audio_path=output_path,
                    format="mp3",
                    provider="elevenlabs",
                    voice=voice,
                    text_length=len(text),
                )
                
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            raise


# ============================================
# TTS Manager
# ============================================

class TTSManager:
    """
    Manages TTS operations with multiple providers.
    """
    
    def __init__(self, default_config: TTSConfig = None):
        self.default_config = default_config or TTSConfig()
        self._providers: dict[TTSProvider, BaseTTSProvider] = {}
    
    def _get_provider(self, provider_type: TTSProvider, config: TTSConfig = None) -> BaseTTSProvider:
        """Get or create a TTS provider."""
        cfg = config or self.default_config
        
        if provider_type == TTSProvider.OPENAI:
            return OpenAITTSProvider(cfg)
        elif provider_type == TTSProvider.EDGE:
            return EdgeTTSProvider(cfg)
        elif provider_type == TTSProvider.ELEVENLABS:
            return ElevenLabsTTSProvider(cfg)
        else:
            raise ValueError(f"Unsupported TTS provider: {provider_type}")
    
    async def synthesize(
        self,
        text: str,
        provider: TTSProvider = None,
        voice: str = None,
        speed: float = None,
        output_path: str = None,
    ) -> TTSResult:
        """
        Convert text to speech.
        
        Args:
            text: Text to convert
            provider: TTS provider to use
            voice: Voice to use
            speed: Speech speed (1.0 = normal)
            output_path: Optional path to save audio
        
        Returns:
            TTSResult with audio path
        """
        # Build config
        config = TTSConfig(
            provider=provider or self.default_config.provider,
            voice=voice or self.default_config.voice,
            speed=speed or self.default_config.speed,
            api_key=self.default_config.api_key,
        )
        
        provider_impl = self._get_provider(config.provider, config)
        return await provider_impl.synthesize(text, output_path)
    
    def get_voices(self, provider: TTSProvider = None) -> list[str]:
        """Get available voices for a provider."""
        provider_type = provider or self.default_config.provider
        provider_impl = self._get_provider(provider_type)
        return provider_impl.get_available_voices()
    
    def get_providers(self) -> list[str]:
        """Get list of supported providers."""
        return [p.value for p in TTSProvider]


# ============================================
# Global Instance
# ============================================

_tts_manager: Optional[TTSManager] = None


def get_tts_manager(config: TTSConfig = None) -> TTSManager:
    """Get the global TTS manager instance."""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager(config)
    return _tts_manager


async def text_to_speech(
    text: str,
    provider: str = "openai",
    voice: str = None,
    output_path: str = None,
) -> TTSResult:
    """
    Convenience function to convert text to speech.
    
    Args:
        text: Text to convert
        provider: Provider name (openai, edge, elevenlabs)
        voice: Voice to use
        output_path: Optional path to save audio
    
    Returns:
        TTSResult with audio path
    """
    manager = get_tts_manager()
    provider_type = TTSProvider(provider.lower())
    return await manager.synthesize(text, provider_type, voice, output_path=output_path)


__all__ = [
    "TTSProvider",
    "TTSConfig",
    "TTSResult",
    "BaseTTSProvider",
    "OpenAITTSProvider",
    "EdgeTTSProvider",
    "ElevenLabsTTSProvider",
    "TTSManager",
    "get_tts_manager",
    "text_to_speech",
]
