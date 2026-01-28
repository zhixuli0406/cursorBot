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


def is_authorized(user_id) -> bool:
    """
    Alias for is_user_authorized.
    Accepts user_id as int or str.
    """
    return is_user_authorized(int(user_id))


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
    Manage user sessions with timeout functionality and security features.
    """

    def __init__(self):
        self._sessions: dict[int, dict] = {}
        self._session_tokens: dict[str, int] = {}  # token -> user_id mapping

    def create_session(self, user_id: int, data: Optional[dict] = None) -> dict:
        """Create a new session for a user with secure token."""
        import time
        import secrets
        
        # Generate secure session token
        token = secrets.token_urlsafe(32)
        
        session = {
            "user_id": user_id,
            "token": token,
            "created_at": time.time(),
            "last_activity": time.time(),
            "data": data or {},
            "ip_address": data.get("ip_address") if data else None,
        }
        
        # Invalidate old session for this user (session fixation protection)
        self.destroy_session(user_id)
        
        self._sessions[user_id] = session
        self._session_tokens[token] = user_id
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
    
    def get_session_by_token(self, token: str) -> Optional[dict]:
        """Get session by token (for API authentication)."""
        if not token:
            return None
        
        user_id = self._session_tokens.get(token)
        if user_id is None:
            return None
        
        return self.get_session(user_id)
    
    def validate_session(self, user_id: int, ip_address: str = None) -> bool:
        """
        Validate session with optional IP binding.
        
        Args:
            user_id: User ID to validate
            ip_address: Optional IP to check against stored IP
        
        Returns:
            True if session is valid
        """
        session = self.get_session(user_id)
        if not session:
            return False
        
        # Optional IP binding check (can be disabled for mobile users)
        if ip_address and session.get("ip_address"):
            if session["ip_address"] != ip_address:
                logger.warning(f"Session IP mismatch for user {user_id}")
                # Don't invalidate, just log (IP can change legitimately)
        
        return True

    def update_session(self, user_id: int, data: dict) -> bool:
        """Update session data."""
        session = self.get_session(user_id)
        if session is None:
            return False

        session["data"].update(data)
        return True
    
    def regenerate_token(self, user_id: int) -> Optional[str]:
        """
        Regenerate session token (for privilege escalation scenarios).
        
        Args:
            user_id: User ID
        
        Returns:
            New token or None if session doesn't exist
        """
        import secrets
        
        session = self.get_session(user_id)
        if not session:
            return None
        
        # Remove old token mapping
        old_token = session.get("token")
        if old_token:
            self._session_tokens.pop(old_token, None)
        
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        session["token"] = new_token
        self._session_tokens[new_token] = user_id
        
        logger.info(f"Regenerated session token for user {user_id}")
        return new_token

    def destroy_session(self, user_id: int) -> bool:
        """Destroy user session."""
        if user_id in self._sessions:
            # Remove token mapping
            session = self._sessions[user_id]
            token = session.get("token")
            if token:
                self._session_tokens.pop(token, None)
            
            del self._sessions[user_id]
            logger.info(f"Destroyed session for user {user_id}")
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """Remove all expired sessions."""
        import time
        
        now = time.time()
        expired = []
        
        for user_id, session in self._sessions.items():
            if now - session["last_activity"] > settings.session_timeout:
                expired.append(user_id)
        
        for user_id in expired:
            self.destroy_session(user_id)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def get_active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)


# Global session manager instance
session_manager = SessionManager()

__all__ = ["is_user_authorized", "authorized_only", "session_manager"]
