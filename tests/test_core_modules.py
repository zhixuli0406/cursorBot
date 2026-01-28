"""
Tests for Core Modules

Tests cover:
- LLM Providers
- Async Tasks
- Rate Limiting
- Input Validation
- Session Management
- Unified Commands
- Memory System
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import time


# ============================================
# LLM Providers Tests
# ============================================

class TestLLMProviders:
    """Test LLM Providers module."""
    
    def test_provider_type_enum(self):
        """Test ProviderType enum."""
        from src.core.llm_providers import ProviderType
        
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.GOOGLE.value == "google"
        assert ProviderType.OPENROUTER.value == "openrouter"
        assert ProviderType.MINIMAX.value == "minimax"
    
    def test_provider_config_creation(self):
        """Test ProviderConfig creation."""
        from src.core.llm_providers import ProviderConfig, ProviderType
        
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            model="gpt-4o",
            enabled=True,
        )
        
        assert config.provider_type == ProviderType.OPENAI
        assert config.api_key == "test-key"
        assert config.model == "gpt-4o"
        assert config.enabled is True
    
    def test_model_info_creation(self):
        """Test ModelInfo creation."""
        from src.core.llm_providers import ModelInfo, ProviderType
        
        info = ModelInfo(
            provider=ProviderType.OPENAI,
            model_id="gpt-4o",
            display_name="GPT-4o",
            description="OpenAI's latest model",
            max_tokens=128000,
            supports_vision=True,
        )
        
        assert info.model_id == "gpt-4o"
        assert info.supports_vision is True
    
    def test_llm_manager_singleton(self):
        """Test LLM manager singleton pattern."""
        from src.core.llm_providers import get_llm_manager
        
        manager1 = get_llm_manager()
        manager2 = get_llm_manager()
        
        assert manager1 is manager2
    
    def test_llm_manager_default_models(self):
        """Test LLM manager has default models."""
        from src.core.llm_providers import LLMProviderManager, ProviderType
        
        assert ProviderType.OPENAI in LLMProviderManager.DEFAULT_MODELS
        assert ProviderType.ANTHROPIC in LLMProviderManager.DEFAULT_MODELS
        assert ProviderType.MINIMAX in LLMProviderManager.DEFAULT_MODELS


# ============================================
# Async Tasks Tests
# ============================================

class TestAsyncTasks:
    """Test Async Tasks module."""
    
    def test_task_status_enum(self):
        """Test TaskStatus enum."""
        from src.core.async_tasks import TaskStatus
        
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
    
    def test_task_type_enum(self):
        """Test TaskType enum."""
        from src.core.async_tasks import TaskType
        
        assert TaskType.AGENT.value == "agent"
        assert TaskType.CLI.value == "cli"
        assert TaskType.RAG.value == "rag"
    
    def test_async_task_creation(self):
        """Test AsyncTask creation."""
        from src.core.async_tasks import AsyncTask, TaskStatus, TaskType
        
        task = AsyncTask(
            id="test-task-123",
            user_id="user-456",
            chat_id="chat-789",
            platform="telegram",
            task_type=TaskType.AGENT,
            prompt="Test prompt",
        )
        
        assert task.id == "test-task-123"
        assert task.status == TaskStatus.PENDING
        assert task.task_type == TaskType.AGENT
    
    def test_task_manager_singleton(self):
        """Test TaskManager singleton pattern."""
        from src.core.async_tasks import get_task_manager
        
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        
        assert manager1 is manager2


# ============================================
# Rate Limiting Tests
# ============================================

class TestRateLimiting:
    """Test Rate Limiting module."""
    
    def test_rate_limit_type_enum(self):
        """Test RateLimitType enum."""
        from src.core.rate_limit import RateLimitType
        
        assert RateLimitType.REQUESTS.value == "requests"
        assert RateLimitType.TOKENS.value == "tokens"
        assert RateLimitType.COMMANDS.value == "commands"
    
    def test_rate_limit_config(self):
        """Test RateLimitConfig creation."""
        from src.core.rate_limit import RateLimitConfig, RateLimitType
        
        config = RateLimitConfig(
            limit_type=RateLimitType.REQUESTS,
            max_requests=100,
            window_seconds=60,
        )
        
        assert config.max_requests == 100
        assert config.window_seconds == 60
    
    def test_token_bucket(self):
        """Test TokenBucket algorithm."""
        from src.core.rate_limit import TokenBucket
        
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should be able to consume tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 5
        
        # Should not be able to consume more than available
        assert bucket.consume(10) is False
    
    def test_rate_limiter_user(self):
        """Test per-user rate limiting."""
        from src.core.rate_limit import RateLimiter, RateLimitConfig, RateLimitType
        
        limiter = RateLimiter()
        config = RateLimitConfig(
            limit_type=RateLimitType.REQUESTS,
            max_requests=5,
            window_seconds=60,
        )
        
        limiter.configure("test_limit", config)
        
        # First 5 requests should pass
        for i in range(5):
            result = limiter.check_limit("test_limit", "user123")
            assert result.allowed is True
        
        # 6th request should be rate limited
        result = limiter.check_limit("test_limit", "user123")
        assert result.allowed is False


# ============================================
# Input Validation Tests
# ============================================

class TestInputValidation:
    """Test Input Validation module."""
    
    def test_validation_result(self):
        """Test ValidationResult creation."""
        from src.core.input_validation import ValidationResult
        
        result = ValidationResult(valid=True, sanitized="test")
        assert result.valid is True
        assert result.sanitized == "test"
        
        result = ValidationResult(valid=False, error="Invalid input")
        assert result.valid is False
        assert result.error == "Invalid input"
    
    def test_command_injection_detection(self):
        """Test command injection detection."""
        from src.core.input_validation import InputValidator
        
        validator = InputValidator()
        
        # Safe input
        result = validator.validate_command_input("echo hello")
        assert result.valid is True
        
        # Dangerous input with command chaining
        result = validator.validate_command_input("echo hello; rm -rf /")
        assert result.valid is False
        assert "injection" in result.error.lower()
    
    def test_path_traversal_detection(self):
        """Test path traversal detection."""
        from src.core.input_validation import InputValidator
        
        validator = InputValidator()
        
        # Safe path
        result = validator.validate_path("src/main.py")
        assert result.valid is True
        
        # Path traversal attempt
        result = validator.validate_path("../../../etc/passwd")
        assert result.valid is False
        assert "traversal" in result.error.lower()
    
    def test_xss_prevention(self):
        """Test XSS prevention."""
        from src.core.input_validation import InputValidator
        
        validator = InputValidator()
        
        # Input with script tag
        result = validator.sanitize_html("<script>alert('xss')</script>Hello")
        assert "<script>" not in result.sanitized
        assert "Hello" in result.sanitized


# ============================================
# Session Management Tests
# ============================================

class TestSessionManagement:
    """Test Session Management module."""
    
    def test_session_state_enum(self):
        """Test SessionState enum."""
        from src.core.session import SessionState
        
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.IDLE.value == "idle"
        assert SessionState.EXPIRED.value == "expired"
    
    def test_session_creation(self):
        """Test Session creation."""
        from src.core.session import Session
        
        session = Session(
            user_id="user123",
            platform="telegram",
        )
        
        assert session.user_id == "user123"
        assert session.platform == "telegram"
        assert session.state == SessionState.ACTIVE
    
    def test_session_manager_singleton(self):
        """Test SessionManager singleton."""
        from src.core.session import get_session_manager
        
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        
        assert manager1 is manager2
    
    def test_session_context_management(self):
        """Test session context management."""
        from src.core.session import get_session_manager, reset_session_manager
        
        reset_session_manager()
        manager = get_session_manager()
        
        # Create session
        session = manager.get_or_create_session("user123", "telegram")
        assert session is not None
        
        # Add context
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        
        # Check context
        messages = session.get_messages()
        assert len(messages) == 2


# ============================================
# Unified Commands Tests
# ============================================

class TestUnifiedCommands:
    """Test Unified Commands module."""
    
    def test_command_category_enum(self):
        """Test CommandCategory enum."""
        from src.core.unified_commands import CommandCategory
        
        assert CommandCategory.BASIC.value == "basic"
        assert CommandCategory.AI.value == "ai"
        assert CommandCategory.AGENT.value == "agent"
    
    def test_command_context_creation(self):
        """Test CommandContext creation."""
        from src.core.unified_commands import CommandContext
        
        ctx = CommandContext(
            user_id="user123",
            user_name="Test User",
            platform="telegram",
            args=["arg1", "arg2"],
        )
        
        assert ctx.user_id == "user123"
        assert ctx.platform == "telegram"
        assert len(ctx.args) == 2
    
    def test_command_result_creation(self):
        """Test CommandResult creation."""
        from src.core.unified_commands import CommandResult
        
        result = CommandResult(
            success=True,
            message="Command executed",
            data={"key": "value"},
        )
        
        assert result.success is True
        assert result.message == "Command executed"
        assert result.data["key"] == "value"
    
    def test_commands_registry(self):
        """Test COMMANDS registry has expected commands."""
        from src.core.unified_commands import COMMANDS
        
        assert "start" in COMMANDS
        assert "help" in COMMANDS
        assert "status" in COMMANDS
        assert "mode" in COMMANDS
        assert "model" in COMMANDS

    @pytest.mark.asyncio
    async def test_execute_command_help(self):
        """Test executing help command."""
        from src.core.unified_commands import execute_command, CommandContext
        
        ctx = CommandContext(
            user_id="user123",
            user_name="Test",
            platform="telegram",
        )
        
        result = await execute_command("help", ctx)
        
        assert result.success is True
        assert "指令說明" in result.message


# ============================================
# Memory System Tests
# ============================================

class TestMemorySystem:
    """Test Memory System module."""
    
    def test_memory_entry_creation(self):
        """Test MemoryEntry creation."""
        from src.core.memory import MemoryEntry
        
        entry = MemoryEntry(
            key="user_preference",
            value="dark_mode",
            user_id="user123",
        )
        
        assert entry.key == "user_preference"
        assert entry.value == "dark_mode"
    
    def test_memory_manager_singleton(self):
        """Test MemoryManager singleton."""
        from src.core.memory import get_memory_manager
        
        manager1 = get_memory_manager()
        manager2 = get_memory_manager()
        
        assert manager1 is manager2
    
    def test_memory_operations(self):
        """Test memory CRUD operations."""
        from src.core.memory import get_memory_manager, reset_memory_manager
        
        reset_memory_manager()
        manager = get_memory_manager()
        
        # Set memory
        manager.set("user123", "name", "Alice")
        
        # Get memory
        value = manager.get("user123", "name")
        assert value == "Alice"
        
        # List memories
        memories = manager.list("user123")
        assert "name" in memories
        
        # Delete memory
        manager.delete("user123", "name")
        value = manager.get("user123", "name")
        assert value is None


# ============================================
# I18n Tests
# ============================================

class TestI18n:
    """Test Internationalization module."""
    
    def test_language_enum(self):
        """Test Language enum."""
        from src.core.i18n import Language
        
        assert Language.ZH_TW.value == "zh-TW"
        assert Language.ZH_CN.value == "zh-CN"
        assert Language.EN.value == "en"
        assert Language.JA.value == "ja"
    
    def test_i18n_manager_singleton(self):
        """Test I18nManager singleton."""
        from src.core.i18n import get_i18n
        
        i18n1 = get_i18n()
        i18n2 = get_i18n()
        
        assert i18n1 is i18n2
    
    def test_translation(self):
        """Test translation function."""
        from src.core.i18n import get_i18n, Language
        
        i18n = get_i18n()
        
        # Test default language (zh-TW)
        text = i18n.t("common.welcome")
        assert text is not None
        assert len(text) > 0


# ============================================
# Verbose Mode Tests
# ============================================

class TestVerboseMode:
    """Test Verbose Mode module."""
    
    def test_verbose_level_enum(self):
        """Test VerboseLevel enum."""
        from src.core.verbose import VerboseLevel
        
        assert VerboseLevel.OFF.value == "off"
        assert VerboseLevel.LOW.value == "low"
        assert VerboseLevel.MEDIUM.value == "medium"
        assert VerboseLevel.HIGH.value == "high"
    
    def test_verbose_manager_singleton(self):
        """Test VerboseManager singleton."""
        from src.core.verbose import get_verbose_manager
        
        manager1 = get_verbose_manager()
        manager2 = get_verbose_manager()
        
        assert manager1 is manager2
    
    def test_verbose_level_setting(self):
        """Test setting verbose level."""
        from src.core.verbose import get_verbose_manager, VerboseLevel, reset_verbose_manager
        
        reset_verbose_manager()
        manager = get_verbose_manager()
        
        # Set level
        manager.set_level("user123", VerboseLevel.HIGH)
        
        # Get level
        level = manager.get_level("user123")
        assert level == VerboseLevel.HIGH


# ============================================
# Elevated Permissions Tests
# ============================================

class TestElevatedPermissions:
    """Test Elevated Permissions module."""
    
    def test_protected_action_enum(self):
        """Test ProtectedAction enum."""
        from src.core.elevated import ProtectedAction
        
        assert ProtectedAction.FILE_DELETE.value == "file_delete"
        assert ProtectedAction.SYSTEM_EXEC.value == "system_exec"
        assert ProtectedAction.CONFIG_WRITE.value == "config_write"
    
    def test_elevation_manager_singleton(self):
        """Test ElevationManager singleton."""
        from src.core.elevated import get_elevation_manager
        
        manager1 = get_elevation_manager()
        manager2 = get_elevation_manager()
        
        assert manager1 is manager2
    
    def test_elevation_check(self):
        """Test elevation check."""
        from src.core.elevated import get_elevation_manager, ProtectedAction, reset_elevation_manager
        
        reset_elevation_manager()
        manager = get_elevation_manager()
        
        # Not elevated by default
        is_elevated = manager.is_elevated("user123", ProtectedAction.FILE_DELETE)
        assert is_elevated is False
        
        # Grant elevation
        manager.elevate("user123", duration_minutes=5)
        
        # Now should be elevated
        is_elevated = manager.is_elevated("user123", ProtectedAction.FILE_DELETE)
        assert is_elevated is True


# ============================================
# Health Check Tests
# ============================================

class TestHealthCheck:
    """Test Health Check module."""
    
    def test_health_status_enum(self):
        """Test HealthStatus enum."""
        from src.core.health import HealthStatus
        
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
    
    def test_component_health(self):
        """Test ComponentHealth creation."""
        from src.core.health import ComponentHealth, HealthStatus
        
        health = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=50,
        )
        
        assert health.name == "database"
        assert health.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_health_checker(self):
        """Test HealthChecker."""
        from src.core.health import HealthChecker
        
        checker = HealthChecker()
        
        # Run health check
        result = await checker.check_all()
        
        assert result.status in ["healthy", "degraded", "unhealthy"]
        assert result.timestamp is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
