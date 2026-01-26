"""
Authentication and authorization utilities for CursorBot
Handles user verification and permission management
"""

from functools import wraps
from typing import Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes

from .config import settings
from .logger import logger


def is_user_authorized(user_id: int) -> bool:
    """
    Check if a user is authorized to use the bot.

    Args:
        user_id: Telegram user ID to check

    Returns:
        True if user is authorized, False otherwise
    """
    allowed_users = settings.allowed_user_ids

    # If no users configured, deny all (security default)
    if not allowed_users:
        logger.warning("No allowed users configured. Denying access.")
        return False

    return user_id in allowed_users


def authorized_only(func: Callable) -> Callable:
    """
    Decorator to restrict handler access to authorized users only.

    Usage:
        @authorized_only
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            ...
    """

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user = update.effective_user
        if user is None:
            logger.warning("Received update without user information")
            return

        if not is_user_authorized(user.id):
            logger.warning(
                f"Unauthorized access attempt by user {user.id} ({user.username})"
            )
            if update.message:
                await update.message.reply_text(
                    "⛔ 您沒有權限使用此 Bot。\n"
                    "Unauthorized access. Contact administrator."
                )
            return

        logger.debug(f"Authorized user {user.id} ({user.username}) accessing {func.__name__}")
        return await func(update, context, *args, **kwargs)

    return wrapper


class SessionManager:
    """
    Manage user sessions with timeout functionality.
    """

    def __init__(self):
        self._sessions: dict[int, dict] = {}

    def create_session(self, user_id: int, data: Optional[dict] = None) -> dict:
        """Create a new session for a user."""
        import time

        session = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "data": data or {},
        }
        self._sessions[user_id] = session
        logger.info(f"Created session for user {user_id}")
        return session

    def get_session(self, user_id: int) -> Optional[dict]:
        """Get user session if valid."""
        import time

        session = self._sessions.get(user_id)
        if session is None:
            return None

        # Check session timeout
        if time.time() - session["last_activity"] > settings.session_timeout:
            self.destroy_session(user_id)
            logger.info(f"Session expired for user {user_id}")
            return None

        # Update last activity
        session["last_activity"] = time.time()
        return session

    def update_session(self, user_id: int, data: dict) -> bool:
        """Update session data."""
        session = self.get_session(user_id)
        if session is None:
            return False

        session["data"].update(data)
        return True

    def destroy_session(self, user_id: int) -> bool:
        """Destroy user session."""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info(f"Destroyed session for user {user_id}")
            return True
        return False


# Global session manager instance
session_manager = SessionManager()

__all__ = ["is_user_authorized", "authorized_only", "session_manager"]
