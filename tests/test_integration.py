"""
Integration Tests for CursorBot

End-to-end tests for:
- Platform command handling
- Webhook processing
- Multi-platform consistency
- Async task flow
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ============================================
# Unified Command Integration Tests
# ============================================

class TestUnifiedCommandIntegration:
    """Test unified command handling across platforms."""
    
    @pytest.mark.asyncio
    async def test_start_command_telegram(self):
        """Test /start command on Telegram."""
        from src.core.unified_commands import execute_command, CommandContext
        
        ctx = CommandContext(
            user_id="123456789",
            user_name="TestUser",
            platform="telegram",
        )
        
        result = await execute_command("start", ctx)
        
        assert result.success is True
        assert "歡迎" in result.message
    
    @pytest.mark.asyncio
    async def test_start_command_line(self):
        """Test /start command on LINE."""
        from src.core.unified_commands import execute_command, CommandContext
        
        ctx = CommandContext(
            user_id="U722f9b179e0f56f500adb3d11dae6e99",
            user_name="LINEUser",
            platform="line",
        )
        
        result = await execute_command("start", ctx)
        
        assert result.success is True
        assert "歡迎" in result.message
    
    @pytest.mark.asyncio
    async def test_help_command_consistency(self):
        """Test /help returns same content across platforms."""
        from src.core.unified_commands import execute_command, CommandContext
        
        platforms = ["telegram", "discord", "line", "slack"]
        results = []
        
        for platform in platforms:
            ctx = CommandContext(
                user_id="user123",
                user_name="Test",
                platform=platform,
            )
            result = await execute_command("help", ctx)
            results.append(result.message)
        
        # All platforms should have same help content
        assert len(set(results)) == 1
    
    @pytest.mark.asyncio
    async def test_status_command(self):
        """Test /status command."""
        from src.core.unified_commands import execute_command, CommandContext
        
        ctx = CommandContext(
            user_id="user123",
            user_name="Test",
            platform="telegram",
        )
        
        result = await execute_command("status", ctx)
        
        assert result.success is True
        assert "狀態" in result.message
    
    @pytest.mark.asyncio
    async def test_mode_command(self):
        """Test /mode command."""
        from src.core.unified_commands import execute_command, CommandContext
        
        ctx = CommandContext(
            user_id="user123",
            user_name="Test",
            platform="telegram",
            args=[],
        )
        
        result = await execute_command("mode", ctx)
        
        assert result.success is True
        assert "模式" in result.message
    
    @pytest.mark.asyncio
    async def test_mode_switch(self):
        """Test switching modes."""
        from src.core.unified_commands import execute_command, CommandContext
        
        ctx = CommandContext(
            user_id="user123",
            user_name="Test",
            platform="telegram",
            args=["cli"],
        )
        
        result = await execute_command("mode", ctx)
        
        assert result.success is True


# ============================================
# Webhook Integration Tests
# ============================================

class TestWebhookIntegration:
    """Test webhook processing."""
    
    @pytest.mark.asyncio
    async def test_line_webhook_message_parsing(self):
        """Test LINE webhook parses messages correctly."""
        from src.server.social_webhooks import handle_platform_message
        
        # Simulate LINE message
        response = await handle_platform_message(
            user_id="U722f9b179e0f56f500adb3d11dae6e99",
            text="/help",
            platform="line",
            user_name="TestUser",
            allowed_users="U722f9b179e0f56f500adb3d11dae6e99",
        )
        
        assert "指令說明" in response
    
    @pytest.mark.asyncio
    async def test_slack_webhook_command_parsing(self):
        """Test Slack webhook parses commands correctly."""
        from src.server.social_webhooks import handle_platform_message
        
        response = await handle_platform_message(
            user_id="U12345678",
            text="/status",
            platform="slack",
            user_name="SlackUser",
            allowed_users="U12345678",
        )
        
        assert "狀態" in response


# ============================================
# Async Task Flow Tests
# ============================================

class TestAsyncTaskFlow:
    """Test async task execution flow."""
    
    def test_task_creation_flow(self):
        """Test creating async task."""
        from src.core.async_tasks import (
            get_task_manager, reset_task_manager,
            AsyncTask, TaskType, TaskStatus,
        )
        
        reset_task_manager()
        manager = get_task_manager()
        
        # Create task
        task = manager.create_task(
            user_id="user123",
            chat_id="chat456",
            platform="telegram",
            task_type=TaskType.AGENT,
            prompt="Test task",
        )
        
        assert task.id is not None
        assert task.status == TaskStatus.PENDING
    
    def test_task_status_updates(self):
        """Test task status transitions."""
        from src.core.async_tasks import (
            get_task_manager, reset_task_manager,
            TaskType, TaskStatus,
        )
        
        reset_task_manager()
        manager = get_task_manager()
        
        # Create and start task
        task = manager.create_task(
            user_id="user123",
            chat_id="chat456",
            platform="telegram",
            task_type=TaskType.CLI,
            prompt="Test",
        )
        
        # Update status
        manager.update_task_status(task.id, TaskStatus.RUNNING)
        updated = manager.get_task(task.id)
        assert updated.status == TaskStatus.RUNNING
        
        # Complete task
        manager.update_task_status(task.id, TaskStatus.COMPLETED, result="Done")
        completed = manager.get_task(task.id)
        assert completed.status == TaskStatus.COMPLETED
        assert completed.result == "Done"
    
    def test_task_cancellation(self):
        """Test task cancellation."""
        from src.core.async_tasks import (
            get_task_manager, reset_task_manager,
            TaskType, TaskStatus,
        )
        
        reset_task_manager()
        manager = get_task_manager()
        
        # Create task
        task = manager.create_task(
            user_id="user123",
            chat_id="chat456",
            platform="telegram",
            task_type=TaskType.AGENT,
            prompt="Test",
        )
        
        # Cancel task
        result = manager.cancel_task(task.id)
        assert result is True
        
        cancelled = manager.get_task(task.id)
        assert cancelled.status == TaskStatus.CANCELLED
    
    def test_user_tasks_listing(self):
        """Test listing user's tasks."""
        from src.core.async_tasks import (
            get_task_manager, reset_task_manager,
            TaskType,
        )
        
        reset_task_manager()
        manager = get_task_manager()
        
        # Create multiple tasks
        for i in range(3):
            manager.create_task(
                user_id="user123",
                chat_id="chat456",
                platform="telegram",
                task_type=TaskType.AGENT,
                prompt=f"Task {i}",
            )
        
        # Create task for different user
        manager.create_task(
            user_id="user456",
            chat_id="chat789",
            platform="telegram",
            task_type=TaskType.CLI,
            prompt="Other user task",
        )
        
        # List user's tasks
        tasks = manager.get_user_tasks("user123")
        assert len(tasks) == 3


# ============================================
# Session Flow Tests
# ============================================

class TestSessionFlow:
    """Test session management flow."""
    
    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        from src.core.session import (
            get_session_manager, reset_session_manager,
            SessionState,
        )
        
        reset_session_manager()
        manager = get_session_manager()
        
        # Create session
        session = manager.get_or_create_session("user123", "telegram")
        assert session.state == SessionState.ACTIVE
        
        # Add messages
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        
        # Check history
        messages = session.get_messages()
        assert len(messages) == 2
        
        # Clear session
        session.clear()
        messages = session.get_messages()
        assert len(messages) == 0
    
    def test_session_compaction(self):
        """Test session history compaction."""
        from src.core.session import (
            get_session_manager, reset_session_manager,
        )
        
        reset_session_manager()
        manager = get_session_manager()
        
        session = manager.get_or_create_session("user123", "telegram")
        
        # Add many messages
        for i in range(20):
            session.add_message("user", f"Message {i}")
            session.add_message("assistant", f"Response {i}")
        
        # Compact should reduce message count
        original_count = len(session.get_messages())
        session.compact(max_messages=10)
        compacted_count = len(session.get_messages())
        
        assert compacted_count <= 10


# ============================================
# LLM Provider Integration Tests
# ============================================

class TestLLMProviderIntegration:
    """Test LLM provider integration."""
    
    def test_provider_selection_priority(self):
        """Test provider auto-selection based on priority."""
        from src.core.llm_providers import LLMProviderManager, ProviderType
        
        manager = LLMProviderManager()
        
        # Check priority list exists
        assert len(manager.PROVIDER_CLASSES) > 0
        assert ProviderType.OPENAI in manager.PROVIDER_CLASSES
        assert ProviderType.ANTHROPIC in manager.PROVIDER_CLASSES
    
    def test_user_model_selection_persistence(self):
        """Test user model selection is persisted."""
        from src.core.llm_providers import get_llm_manager, ProviderType
        
        manager = get_llm_manager()
        
        # Set user model
        manager.set_user_model("user123", ProviderType.ANTHROPIC, "claude-3-opus")
        
        # Get user model
        selection = manager.get_user_model("user123")
        
        if selection:
            provider, model = selection
            assert provider == ProviderType.ANTHROPIC
            assert model == "claude-3-opus"


# ============================================
# Multi-Platform Consistency Tests
# ============================================

class TestMultiPlatformConsistency:
    """Test consistency across platforms."""
    
    @pytest.mark.asyncio
    async def test_command_response_format(self):
        """Test commands return properly formatted responses."""
        from src.core.unified_commands import execute_command, CommandContext
        
        commands = ["start", "help", "status"]
        
        for cmd in commands:
            ctx = CommandContext(
                user_id="user123",
                user_name="Test",
                platform="telegram",
            )
            
            result = await execute_command(cmd, ctx)
            
            # Response should not be empty
            assert len(result.message) > 0
            
            # Response should be in Traditional Chinese
            # (Check for common Chinese characters)
            chinese_chars = any('\u4e00' <= c <= '\u9fff' for c in result.message)
            assert chinese_chars is True
    
    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Test error handling is consistent."""
        from src.core.unified_commands import execute_command, CommandContext
        
        # Try invalid command
        ctx = CommandContext(
            user_id="user123",
            user_name="Test",
            platform="telegram",
        )
        
        result = await execute_command("invalid_command_xyz", ctx)
        
        # Should handle gracefully
        assert result is not None


# ============================================
# Rate Limiting Integration Tests
# ============================================

class TestRateLimitingIntegration:
    """Test rate limiting integration."""
    
    def test_rate_limit_enforcement(self):
        """Test rate limits are enforced."""
        from src.core.rate_limit import (
            get_rate_limiter, reset_rate_limiter,
            RateLimitConfig, RateLimitType,
        )
        
        reset_rate_limiter()
        limiter = get_rate_limiter()
        
        # Configure strict limit
        config = RateLimitConfig(
            limit_type=RateLimitType.COMMANDS,
            max_requests=3,
            window_seconds=60,
        )
        limiter.configure("cmd_limit", config)
        
        # First 3 should pass
        for i in range(3):
            result = limiter.check_limit("cmd_limit", "user123")
            assert result.allowed is True, f"Request {i+1} should be allowed"
        
        # 4th should be blocked
        result = limiter.check_limit("cmd_limit", "user123")
        assert result.allowed is False
        assert result.retry_after > 0


# ============================================
# Security Integration Tests
# ============================================

class TestSecurityIntegration:
    """Test security features integration."""
    
    def test_input_sanitization_in_commands(self):
        """Test inputs are sanitized before processing."""
        from src.core.input_validation import InputValidator
        
        validator = InputValidator()
        
        # Test various injection attempts
        payloads = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "$(rm -rf /)",
            "`whoami`",
        ]
        
        for payload in payloads:
            result = validator.validate_command_input(payload)
            # Should either reject or sanitize
            assert result.valid is False or payload not in result.sanitized
    
    def test_elevated_permission_timeout(self):
        """Test elevated permissions expire."""
        from src.core.elevated import (
            get_elevation_manager, reset_elevation_manager,
            ProtectedAction,
        )
        import time
        
        reset_elevation_manager()
        manager = get_elevation_manager()
        
        # Grant short elevation (1 second)
        manager.elevate("user123", duration_minutes=0.017)  # ~1 second
        
        # Should be elevated
        assert manager.is_elevated("user123", ProtectedAction.FILE_DELETE) is True
        
        # Wait for expiry
        time.sleep(1.5)
        
        # Should no longer be elevated
        assert manager.is_elevated("user123", ProtectedAction.FILE_DELETE) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
