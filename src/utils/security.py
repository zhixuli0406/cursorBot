"""
Security utilities for CursorBot
Provides security functions for authentication, sanitization, and protection.
"""

import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Optional, Any

from .logger import logger


# ============================================
# Constants
# ============================================

# Rate limiting defaults
DEFAULT_RATE_LIMIT = 60  # requests per minute
DEFAULT_RATE_WINDOW = 60  # seconds

# Session defaults
SESSION_ID_LENGTH = 32
SESSION_TOKEN_LENGTH = 64

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e/",
    r"%2e%2e\\",
    r"\.\.%2f",
    r"\.\.%5c",
]

# Dangerous command patterns
DANGEROUS_COMMAND_PATTERNS = [
    r";\s*",  # Command chaining
    r"\|\s*",  # Pipe
    r"&&",  # AND operator
    r"\|\|",  # OR operator
    r"`",  # Backtick substitution
    r"\$\(",  # Command substitution
    r"\$\{",  # Variable expansion
    r">\s*",  # Redirect output
    r"<\s*",  # Redirect input
    r"\n",  # Newline injection
]

# Allowed commands whitelist (for shell execution)
ALLOWED_COMMANDS = {
    "ls", "cat", "head", "tail", "grep", "find", "pwd", "echo",
    "git", "npm", "yarn", "pnpm", "pip", "python", "node",
    "curl", "wget", "docker", "kubectl",
}


# ============================================
# Secure Token Generation
# ============================================

def generate_secure_token(length: int = SESSION_TOKEN_LENGTH) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in characters
    
    Returns:
        Secure random hex string
    """
    return secrets.token_hex(length // 2)


def generate_session_id() -> str:
    """Generate a secure session ID."""
    return f"sess_{secrets.token_urlsafe(SESSION_ID_LENGTH)}"


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"sk_{secrets.token_urlsafe(32)}"


# ============================================
# HMAC Signature Verification
# ============================================

def verify_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify HMAC signature with constant-time comparison.
    
    Args:
        payload: The payload bytes to verify
        signature: The signature to check (hex string)
        secret: The secret key
        algorithm: Hash algorithm (sha256, sha1, etc.)
    
    Returns:
        True if signature is valid
    """
    if not payload or not signature or not secret:
        return False
    
    try:
        # Compute expected signature
        mac = hmac.new(
            secret.encode("utf-8"),
            payload,
            getattr(hashlib, algorithm),
        )
        expected = mac.hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.warning(f"Signature verification failed: {e}")
        return False


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    prefix: str = "sha256=",
) -> bool:
    """
    Verify webhook signature (GitHub/Line style).
    
    Args:
        payload: Request body bytes
        signature: Signature header value
        secret: Webhook secret
        prefix: Signature prefix (e.g., "sha256=", "sha1=")
    
    Returns:
        True if valid
    """
    if not signature.startswith(prefix):
        return False
    
    actual_sig = signature[len(prefix):]
    algorithm = prefix.rstrip("=")
    
    return verify_signature(payload, actual_sig, secret, algorithm)


# ============================================
# Input Sanitization
# ============================================

def sanitize_command(command: str) -> tuple[bool, str, str]:
    """
    Sanitize a shell command to prevent injection.
    
    Args:
        command: The command string to check
    
    Returns:
        Tuple of (is_safe, sanitized_command, error_message)
    """
    if not command or not command.strip():
        return False, "", "Empty command"
    
    command = command.strip()
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_COMMAND_PATTERNS:
        if re.search(pattern, command):
            return False, "", f"Dangerous pattern detected: {pattern}"
    
    # Extract base command
    parts = command.split()
    if not parts:
        return False, "", "Invalid command format"
    
    base_cmd = parts[0].split("/")[-1]  # Get basename
    
    # Check whitelist
    if base_cmd not in ALLOWED_COMMANDS:
        return False, "", f"Command not allowed: {base_cmd}"
    
    return True, command, ""


def sanitize_path(
    path: str,
    base_directory: str = None,
    allow_absolute: bool = False,
) -> tuple[bool, str, str]:
    """
    Sanitize a file path to prevent traversal attacks.
    
    Args:
        path: The path to sanitize
        base_directory: Allowed base directory
        allow_absolute: Whether to allow absolute paths
    
    Returns:
        Tuple of (is_safe, sanitized_path, error_message)
    """
    if not path:
        return False, "", "Empty path"
    
    # Check for traversal patterns
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return False, "", "Path traversal detected"
    
    # Normalize path
    normalized = os.path.normpath(path)
    
    # Check for absolute path
    if os.path.isabs(normalized) and not allow_absolute:
        return False, "", "Absolute paths not allowed"
    
    # If base directory specified, ensure path stays within
    if base_directory:
        base = os.path.abspath(base_directory)
        full_path = os.path.abspath(os.path.join(base, normalized))
        
        if not full_path.startswith(base):
            return False, "", "Path escapes base directory"
        
        return True, full_path, ""
    
    return True, normalized, ""


def sanitize_html(text: str) -> str:
    """
    Sanitize text for safe HTML display.
    
    Args:
        text: Text to sanitize
    
    Returns:
        HTML-safe string
    """
    if not text:
        return ""
    
    # Escape HTML entities
    replacements = [
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
        ('"', "&quot;"),
        ("'", "&#x27;"),
        ("/", "&#x2F;"),
        ("`", "&#x60;"),
        ("=", "&#x3D;"),
    ]
    
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    
    return result


def sanitize_log_message(message: str, sensitive_patterns: list[str] = None) -> str:
    """
    Sanitize a log message by masking sensitive data.
    
    Args:
        message: Log message to sanitize
        sensitive_patterns: Additional patterns to mask
    
    Returns:
        Sanitized message
    """
    if not message:
        return ""
    
    result = message
    
    # Default sensitive patterns
    patterns = [
        # API keys
        (r'(api[_-]?key\s*[=:]\s*)["\']?[\w-]{20,}["\']?', r'\1[REDACTED]'),
        (r'(sk-[a-zA-Z0-9]{20,})', r'[REDACTED_API_KEY]'),
        (r'(token\s*[=:]\s*)["\']?[\w-]{20,}["\']?', r'\1[REDACTED]'),
        
        # Passwords
        (r'(password\s*[=:]\s*)["\']?[^\s"\']+["\']?', r'\1[REDACTED]'),
        (r'(secret\s*[=:]\s*)["\']?[^\s"\']+["\']?', r'\1[REDACTED]'),
        
        # Email addresses (partial mask)
        (r'(\w{2})\w+@(\w+\.\w+)', r'\1***@\2'),
        
        # Credit card numbers
        (r'\b(\d{4})\d{8,12}(\d{4})\b', r'\1********\2'),
        
        # IP addresses (partial mask)
        (r'(\d{1,3}\.\d{1,3}\.)\d{1,3}\.\d{1,3}', r'\1***.***'),
    ]
    
    # Add custom patterns
    if sensitive_patterns:
        for pattern in sensitive_patterns:
            patterns.append((pattern, '[REDACTED]'))
    
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


# ============================================
# Rate Limiting
# ============================================

@dataclass
class RateLimitEntry:
    """Rate limit tracking entry."""
    count: int = 0
    window_start: float = 0.0
    blocked_until: float = 0.0


class RateLimiter:
    """
    In-memory rate limiter with sliding window.
    
    Usage:
        limiter = RateLimiter(requests_per_minute=60)
        if limiter.is_allowed("user_123"):
            # Process request
        else:
            # Return 429 Too Many Requests
    """
    
    def __init__(
        self,
        requests_per_minute: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_RATE_WINDOW,
        block_duration: int = 300,  # 5 minutes block after exceeding
    ):
        self.limit = requests_per_minute
        self.window = window_seconds
        self.block_duration = block_duration
        self._entries: dict[str, RateLimitEntry] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if a request is allowed.
        
        Args:
            identifier: Unique identifier (user ID, IP, etc.)
        
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        
        if identifier not in self._entries:
            self._entries[identifier] = RateLimitEntry(
                count=1,
                window_start=now,
            )
            return True
        
        entry = self._entries[identifier]
        
        # Check if blocked
        if entry.blocked_until > now:
            return False
        
        # Check if window expired
        if now - entry.window_start > self.window:
            # Reset window
            entry.count = 1
            entry.window_start = now
            entry.blocked_until = 0
            return True
        
        # Check limit
        if entry.count >= self.limit:
            # Block the identifier
            entry.blocked_until = now + self.block_duration
            logger.warning(f"Rate limit exceeded for {identifier}, blocked until {entry.blocked_until}")
            return False
        
        # Increment count
        entry.count += 1
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests in current window."""
        if identifier not in self._entries:
            return self.limit
        
        entry = self._entries[identifier]
        now = time.time()
        
        if now - entry.window_start > self.window:
            return self.limit
        
        return max(0, self.limit - entry.count)
    
    def get_reset_time(self, identifier: str) -> float:
        """Get time until rate limit resets."""
        if identifier not in self._entries:
            return 0
        
        entry = self._entries[identifier]
        now = time.time()
        
        if entry.blocked_until > now:
            return entry.blocked_until - now
        
        remaining = self.window - (now - entry.window_start)
        return max(0, remaining)
    
    def clear(self, identifier: str = None):
        """Clear rate limit entries."""
        if identifier:
            self._entries.pop(identifier, None)
        else:
            self._entries.clear()


# Global rate limiters
_api_limiter = RateLimiter(requests_per_minute=60)
_auth_limiter = RateLimiter(requests_per_minute=10, block_duration=600)


def rate_limit(
    limiter: RateLimiter = None,
    identifier_func: Callable = None,
):
    """
    Decorator to apply rate limiting.
    
    Args:
        limiter: RateLimiter instance (default: global API limiter)
        identifier_func: Function to extract identifier from request
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get identifier
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Try to get from common patterns
                identifier = "unknown"
                for arg in args:
                    if hasattr(arg, "effective_user"):
                        identifier = str(arg.effective_user.id)
                        break
                    if hasattr(arg, "client"):
                        identifier = str(getattr(arg.client, "host", "unknown"))
                        break
            
            # Check rate limit
            rl = limiter or _api_limiter
            if not rl.is_allowed(identifier):
                remaining = rl.get_reset_time(identifier)
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Try again in {remaining:.0f}s"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# ============================================
# Authentication Helpers
# ============================================

@dataclass
class AuthToken:
    """Authentication token data."""
    token: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    scopes: list[str] = field(default_factory=list)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        return scope in self.scopes or "*" in self.scopes


class TokenManager:
    """
    Simple in-memory token manager.
    For production, use Redis or a database.
    """
    
    def __init__(self, default_expiry: int = 3600):
        self._tokens: dict[str, AuthToken] = {}
        self.default_expiry = default_expiry
    
    def create_token(
        self,
        user_id: str,
        scopes: list[str] = None,
        expiry: int = None,
    ) -> AuthToken:
        """Create a new auth token."""
        token = generate_secure_token()
        expiry_time = time.time() + (expiry or self.default_expiry)
        
        auth_token = AuthToken(
            token=token,
            user_id=user_id,
            expires_at=expiry_time,
            scopes=scopes or ["*"],
        )
        
        self._tokens[token] = auth_token
        logger.info(f"Created token for user {user_id}")
        return auth_token
    
    def verify_token(self, token: str) -> Optional[AuthToken]:
        """Verify and return token data."""
        if not token:
            return None
        
        auth_token = self._tokens.get(token)
        if not auth_token:
            return None
        
        if auth_token.is_expired:
            self.revoke_token(token)
            return None
        
        return auth_token
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False
    
    def revoke_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user."""
        count = 0
        to_remove = [
            t for t, data in self._tokens.items()
            if data.user_id == user_id
        ]
        for token in to_remove:
            del self._tokens[token]
            count += 1
        return count
    
    def cleanup_expired(self) -> int:
        """Remove expired tokens."""
        now = time.time()
        to_remove = [
            t for t, data in self._tokens.items()
            if data.expires_at > 0 and data.expires_at < now
        ]
        for token in to_remove:
            del self._tokens[token]
        return len(to_remove)


# Global token manager
token_manager = TokenManager()


# ============================================
# Password Hashing (for future use)
# ============================================

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """
    Hash a password using PBKDF2.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
    
    Returns:
        Tuple of (hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    hash_value = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100000,
    )
    
    return hash_value.hex(), salt


def verify_password(password: str, hash_value: str, salt: str) -> bool:
    """Verify a password against its hash."""
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, hash_value)


# ============================================
# Exports
# ============================================

__all__ = [
    # Token generation
    "generate_secure_token",
    "generate_session_id",
    "generate_api_key",
    
    # Signature verification
    "verify_signature",
    "verify_webhook_signature",
    
    # Sanitization
    "sanitize_command",
    "sanitize_path",
    "sanitize_html",
    "sanitize_log_message",
    
    # Rate limiting
    "RateLimiter",
    "RateLimitExceeded",
    "rate_limit",
    
    # Authentication
    "AuthToken",
    "TokenManager",
    "token_manager",
    
    # Password
    "hash_password",
    "verify_password",
    
    # Constants
    "ALLOWED_COMMANDS",
]
