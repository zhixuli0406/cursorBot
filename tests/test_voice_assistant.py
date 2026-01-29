"""
Tests for CursorBot v1.1 Voice Assistant

Tests the voice assistant core functionality:
- Voice assistant configuration
- Intent recognition
- Command execution
- Context awareness
- Learning engine
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Import voice assistant modules
from src.core.voice_assistant import (
    VoiceAssistant, VoiceAssistantConfig, AssistantState,
    WakeEngine, STTEngine, TTSEngine, IntentCategory,
    Utterance, Intent, AssistantResponse,
    IntentRecognizer, AudioProcessor, SoundEffects,
)
from src.core.voice_commands import (
    CommandExecutor, CommandResult, CommandStatus,
    SystemCommandHandler, ApplicationCommandHandler,
    CodeCommandHandler, WebCommandHandler, ReminderCommandHandler,
)
from src.core.voice_context import (
    ContextEngine, FullContext, TimeContext, LocationContext,
    ActivityContext, DeviceContext, UserContext,
    TimeOfDay, DayType, LocationType, ActivityType, DeviceType,
    TimeContextProvider,
)
from src.core.voice_learning import (
    VoiceLearningEngine, UserProfile, InteractionRecord, LearnedPattern,
)


class TestVoiceAssistantConfig:
    """Test VoiceAssistantConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = VoiceAssistantConfig()
        
        assert config.wake_enabled is True
        assert config.wake_engine == WakeEngine.VOSK
        assert len(config.wake_words) > 0
        assert config.sample_rate == 16000
        assert config.stt_engine == STTEngine.WHISPER_LOCAL
        assert config.tts_engine == TTSEngine.EDGE
        assert config.vad_enabled is True
        assert config.noise_reduction is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = VoiceAssistantConfig(
            wake_enabled=False,
            wake_words=["custom wake"],
            stt_language="en",
            tts_voice="en-US-AriaNeural"
        )
        
        assert config.wake_enabled is False
        assert "custom wake" in config.wake_words
        assert config.stt_language == "en"


class TestIntentRecognizer:
    """Test intent recognition."""
    
    @pytest.fixture
    def recognizer(self):
        """Create recognizer instance."""
        config = VoiceAssistantConfig()
        return IntentRecognizer(config)
    
    @pytest.mark.asyncio
    async def test_recognize_question(self, recognizer):
        """Test recognizing question intent."""
        intent = await recognizer.recognize("什麼是 Python？")
        assert intent.category == IntentCategory.QUESTION
    
    @pytest.mark.asyncio
    async def test_recognize_command(self, recognizer):
        """Test recognizing command intent."""
        intent = await recognizer.recognize("打開 Cursor")
        assert intent.category == IntentCategory.COMMAND
    
    @pytest.mark.asyncio
    async def test_recognize_control(self, recognizer):
        """Test recognizing control intent."""
        intent = await recognizer.recognize("調高音量")
        assert intent.category == IntentCategory.CONTROL
    
    @pytest.mark.asyncio
    async def test_recognize_search(self, recognizer):
        """Test recognizing search intent."""
        intent = await recognizer.recognize("搜尋天氣")
        assert intent.category == IntentCategory.SEARCH
    
    @pytest.mark.asyncio
    async def test_recognize_reminder(self, recognizer):
        """Test recognizing reminder intent."""
        intent = await recognizer.recognize("提醒我明天開會")
        assert intent.category == IntentCategory.REMINDER
    
    @pytest.mark.asyncio
    async def test_recognize_code(self, recognizer):
        """Test recognizing code intent."""
        intent = await recognizer.recognize("Git commit")
        assert intent.category == IntentCategory.CODE
    
    @pytest.mark.asyncio
    async def test_recognize_chat(self, recognizer):
        """Test recognizing chat intent."""
        intent = await recognizer.recognize("你好")
        assert intent.category == IntentCategory.CHAT


class TestAudioProcessor:
    """Test audio processing utilities."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        config = VoiceAssistantConfig()
        return AudioProcessor(config)
    
    def test_detect_speech_with_speech(self, processor):
        """Test speech detection with audio containing speech."""
        # Create audio with high energy (speech)
        import struct
        samples = [10000] * 1000  # High amplitude
        audio = struct.pack(f"{len(samples)}h", *samples)
        
        assert processor.detect_speech(audio) is True
    
    def test_detect_speech_with_silence(self, processor):
        """Test speech detection with silence."""
        # Create silent audio
        import struct
        samples = [0] * 1000  # Zero amplitude
        audio = struct.pack(f"{len(samples)}h", *samples)
        
        assert processor.detect_speech(audio) is False
    
    def test_reduce_noise(self, processor):
        """Test noise reduction."""
        import struct
        # Create noisy audio
        samples = [100, 200, 5000, 100, 300]  # Mix of noise and signal
        audio = struct.pack(f"{len(samples)}h", *samples)
        
        reduced = processor.reduce_noise(audio)
        assert len(reduced) == len(audio)


class TestCommandExecutor:
    """Test command execution."""
    
    @pytest.fixture
    def executor(self):
        """Create executor instance."""
        return CommandExecutor()
    
    @pytest.mark.asyncio
    async def test_no_handler_for_chat(self, executor):
        """Test that chat intent returns no specific handler result."""
        intent = Intent(
            category=IntentCategory.CHAT,
            raw_text="你好"
        )
        result = await executor.execute(intent)
        assert result.requires_response is True
    
    @pytest.mark.asyncio
    async def test_custom_command_registration(self, executor):
        """Test registering custom command."""
        async def custom_handler(intent):
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text="Custom command executed!"
            )
        
        executor.register_command(r"custom test", custom_handler)
        
        intent = Intent(
            category=IntentCategory.COMMAND,
            raw_text="custom test please"
        )
        result = await executor.execute(intent)
        assert result.status == CommandStatus.SUCCESS
    
    def test_get_available_commands(self, executor):
        """Test getting available commands list."""
        commands = executor.get_available_commands()
        assert len(commands) > 0
        assert isinstance(commands, list)


class TestSystemCommandHandler:
    """Test system command handler."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance."""
        return SystemCommandHandler()
    
    def test_can_handle_control_intent(self, handler):
        """Test handler can handle control intent."""
        intent = Intent(
            category=IntentCategory.CONTROL,
            raw_text="調高音量"
        )
        assert handler.can_handle(intent) is True
    
    def test_cannot_handle_chat_intent(self, handler):
        """Test handler cannot handle chat intent."""
        intent = Intent(
            category=IntentCategory.CHAT,
            raw_text="你好"
        )
        assert handler.can_handle(intent) is False


class TestContextEngine:
    """Test context awareness engine."""
    
    @pytest.fixture
    def engine(self):
        """Create context engine instance."""
        return ContextEngine()
    
    @pytest.mark.asyncio
    async def test_get_current_context(self, engine):
        """Test getting current context."""
        context = await engine.get_current_context()
        
        assert isinstance(context, FullContext)
        assert isinstance(context.time, TimeContext)
        assert isinstance(context.device, DeviceContext)
        assert context.timestamp is not None
    
    def test_get_greeting_morning(self, engine):
        """Test getting morning greeting."""
        # Mock time context
        with patch.object(
            TimeContextProvider, 'get_context',
            return_value=TimeContext(
                time_of_day=TimeOfDay.MORNING,
                day_type=DayType.WEEKDAY,
                hour=9,
                weekday=1,
                date=datetime.now(),
                is_work_hours=True
            )
        ):
            greeting = engine.get_greeting()
            assert "早安" in greeting
    
    def test_update_conversation(self, engine):
        """Test updating conversation context."""
        engine.update_conversation(
            topic="天氣",
            entities={"location": "台北"},
            intent="question"
        )
        
        follow_up = engine.get_follow_up_context()
        assert "天氣" in follow_up["recent_topics"]
        assert follow_up["entities"]["location"] == "台北"
        assert follow_up["last_intent"] == "question"
    
    @pytest.mark.asyncio
    async def test_get_suggestions(self, engine):
        """Test getting contextual suggestions."""
        context = await engine.get_current_context()
        suggestions = engine.get_suggestions(context)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5


class TestTimeContextProvider:
    """Test time context provider."""
    
    def test_get_context_returns_valid_context(self):
        """Test that get_context returns valid TimeContext."""
        provider = TimeContextProvider()
        context = provider.get_context()
        
        assert isinstance(context, TimeContext)
        assert context.time_of_day in TimeOfDay
        assert context.day_type in DayType
        assert 0 <= context.hour < 24
        assert 0 <= context.weekday <= 6


class TestVoiceLearningEngine:
    """Test voice learning engine."""
    
    @pytest.fixture
    def engine(self):
        """Create learning engine instance."""
        engine = VoiceLearningEngine(user_id="test_user")
        yield engine
        # Cleanup
        engine.reset_learning()
    
    @pytest.mark.asyncio
    async def test_record_interaction(self, engine):
        """Test recording an interaction."""
        utterance = Utterance(text="調高音量")
        intent = Intent(
            category=IntentCategory.CONTROL,
            raw_text="調高音量"
        )
        
        await engine.record_interaction(
            utterance=utterance,
            intent=intent,
            response="好的，已調高音量。",
            command_executed=True,
            success=True
        )
        
        assert engine._profile.total_interactions == 1
    
    def test_add_shortcut(self, engine):
        """Test adding a voice shortcut."""
        engine.add_shortcut("快速筆記", "打開備忘錄並新增筆記")
        
        command = engine.get_shortcut("快速筆記")
        assert command == "打開備忘錄並新增筆記"
    
    def test_expand_shortcuts(self, engine):
        """Test expanding shortcuts in text."""
        engine.add_shortcut("快筆", "打開備忘錄")
        
        expanded = engine.expand_shortcuts("執行快筆")
        assert expanded == "打開備忘錄"
    
    def test_remove_shortcut(self, engine):
        """Test removing a shortcut."""
        engine.add_shortcut("test", "test command")
        assert engine.remove_shortcut("test") is True
        assert engine.get_shortcut("test") is None
    
    def test_update_preference(self, engine):
        """Test updating user preference."""
        engine.update_preference("name", "TestUser")
        
        profile = engine.get_profile()
        assert profile.name == "TestUser"
    
    def test_get_statistics(self, engine):
        """Test getting usage statistics."""
        stats = engine.get_statistics()
        
        assert "total_interactions" in stats
        assert "shortcuts_count" in stats
        assert "patterns_learned" in stats
    
    def test_get_personalized_suggestions(self, engine):
        """Test getting personalized suggestions."""
        suggestions = engine.get_personalized_suggestions()
        
        assert isinstance(suggestions, list)


class TestReminderCommandHandler:
    """Test reminder command handler."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance."""
        return ReminderCommandHandler()
    
    def test_can_handle_reminder_intent(self, handler):
        """Test handler can handle reminder intent."""
        intent = Intent(
            category=IntentCategory.REMINDER,
            raw_text="提醒我明天開會"
        )
        assert handler.can_handle(intent) is True
    
    @pytest.mark.asyncio
    async def test_execute_reminder(self, handler):
        """Test creating a reminder."""
        intent = Intent(
            category=IntentCategory.REMINDER,
            raw_text="提醒我10分鐘後喝水"
        )
        
        result = await handler.execute(intent)
        assert result.status == CommandStatus.SUCCESS
        assert "喝水" in result.response_text or "分鐘" in result.response_text


class TestVoiceAssistantIntegration:
    """Integration tests for voice assistant."""
    
    @pytest.fixture
    def assistant(self):
        """Create assistant instance."""
        config = VoiceAssistantConfig(
            wake_enabled=False,  # Disable wake for testing
        )
        return VoiceAssistant(config)
    
    def test_assistant_state_initial(self, assistant):
        """Test initial state is IDLE."""
        assert assistant.state == AssistantState.IDLE
    
    def test_assistant_not_listening_initially(self, assistant):
        """Test assistant is not listening initially."""
        assert assistant.is_listening is False
    
    def test_get_stats(self, assistant):
        """Test getting assistant statistics."""
        stats = assistant.get_stats()
        
        assert "state" in stats
        assert "running" in stats
        assert "wake_enabled" in stats
        assert "stt_engine" in stats
        assert "tts_engine" in stats


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
