"""
Tests for Telegram Bot functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAuthModule:
    """Tests for authentication module."""

    def test_is_user_authorized_with_valid_user(self):
        """Test authorized user returns True."""
        with patch("src.utils.auth.settings") as mock_settings:
            mock_settings.allowed_user_ids = [123456789]

            from src.utils.auth import is_user_authorized

            assert is_user_authorized(123456789) is True

    def test_is_user_authorized_with_invalid_user(self):
        """Test unauthorized user returns False."""
        with patch("src.utils.auth.settings") as mock_settings:
            mock_settings.allowed_user_ids = [123456789]

            from src.utils.auth import is_user_authorized

            assert is_user_authorized(987654321) is False

    def test_is_user_authorized_with_empty_list(self):
        """Test empty allowed list returns False."""
        with patch("src.utils.auth.settings") as mock_settings:
            mock_settings.allowed_user_ids = []

            from src.utils.auth import is_user_authorized

            assert is_user_authorized(123456789) is False


class TestSessionManager:
    """Tests for session management."""

    def test_create_session(self):
        """Test session creation."""
        from src.utils.auth import SessionManager

        manager = SessionManager()
        session = manager.create_session(123, {"key": "value"})

        assert session["user_id"] == 123
        assert session["data"]["key"] == "value"
        assert "created_at" in session
        assert "last_activity" in session

    def test_get_session_existing(self):
        """Test retrieving existing session."""
        from src.utils.auth import SessionManager

        manager = SessionManager()
        manager.create_session(123)

        session = manager.get_session(123)
        assert session is not None
        assert session["user_id"] == 123

    def test_get_session_nonexistent(self):
        """Test retrieving non-existent session."""
        from src.utils.auth import SessionManager

        manager = SessionManager()
        session = manager.get_session(999)

        assert session is None

    def test_destroy_session(self):
        """Test session destruction."""
        from src.utils.auth import SessionManager

        manager = SessionManager()
        manager.create_session(123)

        result = manager.destroy_session(123)
        assert result is True

        session = manager.get_session(123)
        assert session is None


class TestKeyboards:
    """Tests for keyboard utilities."""

    def test_get_main_menu_keyboard(self):
        """Test main menu keyboard creation."""
        from src.bot.keyboards import get_main_menu_keyboard

        keyboard = get_main_menu_keyboard()
        assert keyboard is not None
        assert keyboard.resize_keyboard is True

    def test_get_confirmation_keyboard(self):
        """Test confirmation keyboard creation."""
        from src.bot.keyboards import get_confirmation_keyboard

        keyboard = get_confirmation_keyboard("test_action")
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2  # Confirm and Cancel


@pytest.mark.asyncio
class TestHandlers:
    """Tests for bot handlers."""

    async def test_start_handler(self):
        """Test /start command handler."""
        from src.bot.handlers import start_handler

        # Create mock update and context
        update = MagicMock()
        update.effective_user.id = 123456789
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await start_handler(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "歡迎使用 CursorBot" in call_args[0][0]
