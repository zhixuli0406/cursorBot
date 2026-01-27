"""
Web Authentication for CursorBot
Provides authentication middleware and helpers for web interfaces.
"""

import hashlib
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional
from functools import wraps

from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logger import logger
from ..utils.security import (
    RateLimiter,
    generate_secure_token,
    verify_signature,
)


# ============================================
# Configuration
# ============================================

# Get credentials from environment
WEB_USERNAME = os.getenv("WEB_ADMIN_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_ADMIN_PASSWORD", "")  # Must be set for auth to work
WEB_AUTH_ENABLED = os.getenv("WEB_AUTH_ENABLED", "true").lower() == "true"

# Session settings
SESSION_COOKIE_NAME = "cursorbot_session"
SESSION_EXPIRY = 3600 * 24  # 24 hours

# Rate limiting
auth_rate_limiter = RateLimiter(requests_per_minute=10, block_duration=600)


# ============================================
# Session Management
# ============================================

@dataclass
class WebSession:
    """Web session data."""
    session_id: str
    username: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    ip_address: str = ""
    user_agent: str = ""
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return time.time() - self.last_activity > SESSION_EXPIRY


class WebSessionManager:
    """Manage web sessions."""
    
    def __init__(self):
        self._sessions: dict[str, WebSession] = {}
    
    def create_session(
        self,
        username: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> WebSession:
        """Create a new session."""
        session_id = generate_secure_token(32)
        session = WebSession(
            session_id=session_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._sessions[session_id] = session
        logger.info(f"Created web session for {username} from {ip_address}")
        return session
    
    def get_session(self, session_id: str) -> Optional[WebSession]:
        """Get session by ID."""
        if not session_id:
            return None
        
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if session.is_expired:
            self.destroy_session(session_id)
            return None
        
        # Update last activity
        session.last_activity = time.time()
        return session
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        to_remove = [
            sid for sid, session in self._sessions.items()
            if session.is_expired
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)
    
    def get_active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)


# Global session manager
session_manager = WebSessionManager()


# ============================================
# Authentication Helpers
# ============================================

def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password."""
    if not WEB_PASSWORD:
        logger.warning("WEB_ADMIN_PASSWORD not set - authentication disabled")
        return True  # Allow access if no password configured
    
    # Constant-time comparison to prevent timing attacks
    username_match = secrets.compare_digest(username, WEB_USERNAME)
    password_match = secrets.compare_digest(password, WEB_PASSWORD)
    
    return username_match and password_match


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def get_session_from_request(request: Request) -> Optional[WebSession]:
    """Extract session from request cookie."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    return session_manager.get_session(session_id)


async def require_auth(request: Request) -> WebSession:
    """
    Dependency to require authentication.
    Use with FastAPI Depends().
    """
    if not WEB_AUTH_ENABLED:
        # Return a dummy session if auth is disabled
        return WebSession(
            session_id="disabled",
            username="anonymous",
        )
    
    session = get_session_from_request(request)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return session


# ============================================
# HTTP Basic Auth
# ============================================

security = HTTPBasic(auto_error=False)


async def verify_basic_auth(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
) -> Optional[str]:
    """Verify HTTP Basic authentication."""
    if not WEB_AUTH_ENABLED or not WEB_PASSWORD:
        return "anonymous"
    
    if not credentials:
        return None
    
    # Rate limiting
    client_ip = get_client_ip(request)
    if not auth_rate_limiter.is_allowed(f"auth_{client_ip}"):
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please try again later.",
        )
    
    if verify_credentials(credentials.username, credentials.password):
        return credentials.username
    
    return None


# ============================================
# Login Page HTML
# ============================================

LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CursorBot - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        .gradient-bg { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        }
    </style>
</head>
<body class="gradient-bg min-h-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-md">
        <div class="text-center mb-8">
            <div class="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
                <span class="text-4xl">🤖</span>
            </div>
            <h1 class="text-2xl font-bold text-gray-800">CursorBot</h1>
            <p class="text-gray-500 mt-2">請登入以繼續</p>
        </div>
        
        {error_message}
        
        <form method="POST" action="/auth/login" class="space-y-6">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">用戶名</label>
                <input type="text" name="username" required
                       class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                       placeholder="admin">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">密碼</label>
                <input type="password" name="password" required
                       class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                       placeholder="••••••••">
            </div>
            <button type="submit"
                    class="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold rounded-xl hover:from-indigo-600 hover:to-purple-700 transition shadow-lg">
                登入
            </button>
        </form>
        
        <p class="text-center text-gray-400 text-sm mt-6">
            CursorBot Dashboard v0.3
        </p>
    </div>
</body>
</html>
"""


# ============================================
# Auth Router
# ============================================

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """Show login page."""
    if not WEB_AUTH_ENABLED or not WEB_PASSWORD:
        # Redirect to dashboard if auth is disabled
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Check if already logged in
    session = get_session_from_request(request)
    if session:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    error_html = ""
    if error:
        error_html = f'''
        <div class="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-xl">
            {error}
        </div>
        '''
    
    return LOGIN_PAGE_HTML.replace("{error_message}", error_html)


@auth_router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """Handle login form submission."""
    client_ip = get_client_ip(request)
    
    # Rate limiting
    if not auth_rate_limiter.is_allowed(f"login_{client_ip}"):
        return RedirectResponse(
            url="/auth/login?error=登入嘗試次數過多，請稍後再試",
            status_code=302,
        )
    
    if verify_credentials(username, password):
        # Create session
        session = session_manager.create_session(
            username=username,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent", ""),
        )
        
        # Set cookie and redirect
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session.session_id,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
            max_age=SESSION_EXPIRY,
        )
        return response
    
    logger.warning(f"Failed login attempt from {client_ip} for user {username}")
    return RedirectResponse(
        url="/auth/login?error=用戶名或密碼錯誤",
        status_code=302,
    )


@auth_router.get("/logout")
async def logout(request: Request):
    """Handle logout."""
    session = get_session_from_request(request)
    if session:
        session_manager.destroy_session(session.session_id)
    
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@auth_router.get("/status")
async def auth_status(request: Request):
    """Check authentication status."""
    session = get_session_from_request(request)
    if session:
        return {
            "authenticated": True,
            "username": session.username,
            "session_id": session.session_id[:8] + "...",
        }
    return {"authenticated": False}


# ============================================
# Middleware
# ============================================

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for protected routes.
    """
    
    # Routes that require authentication
    PROTECTED_PREFIXES = ["/dashboard", "/chat"]
    
    # Routes that are always public
    PUBLIC_ROUTES = ["/", "/health", "/auth/login", "/auth/logout", "/auth/status"]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip auth if disabled
        if not WEB_AUTH_ENABLED or not WEB_PASSWORD:
            return await call_next(request)
        
        # Check if route is public
        if path in self.PUBLIC_ROUTES:
            return await call_next(request)
        
        # Check if route is protected
        is_protected = any(path.startswith(prefix) for prefix in self.PROTECTED_PREFIXES)
        
        if is_protected:
            session = get_session_from_request(request)
            if not session:
                # Redirect to login for HTML requests
                if "text/html" in request.headers.get("Accept", ""):
                    return RedirectResponse(url="/auth/login", status_code=302)
                # Return 401 for API requests
                return Response(
                    content='{"error": "Authentication required"}',
                    status_code=401,
                    media_type="application/json",
                )
        
        return await call_next(request)


# ============================================
# Exports
# ============================================

__all__ = [
    "WEB_AUTH_ENABLED",
    "session_manager",
    "WebSession",
    "verify_credentials",
    "get_session_from_request",
    "require_auth",
    "auth_router",
    "AuthMiddleware",
]
