"""
Rate Limiting - v0.4 Feature
API request rate limiting for security and resource protection.

Implements token bucket algorithm with per-user and global limits.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import asyncio
import time

from ..utils.logger import logger


class RateLimitType(Enum):
    """Types of rate limits."""
    REQUESTS = "requests"      # Total API requests
    TOKENS = "tokens"          # LLM tokens
    COMMANDS = "commands"      # Bot commands
    UPLOADS = "uploads"        # File uploads
    WEBSOCKET = "websocket"    # WebSocket connections


@dataclass
class RateLimitRule:
    """A rate limiting rule."""
    limit_type: RateLimitType
    max_requests: int          # Maximum requests allowed
    window_seconds: int        # Time window in seconds
    burst_limit: int = None    # Max burst (defaults to max_requests)
    cooldown_seconds: int = 0  # Cooldown after limit exceeded
    
    def __post_init__(self):
        if self.burst_limit is None:
            self.burst_limit = self.max_requests


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    tokens: float
    last_update: float
    cooldown_until: float = 0
    
    def to_dict(self) -> dict:
        return {
            "tokens": self.tokens,
            "last_update": self.last_update,
            "cooldown_until": self.cooldown_until,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitBucket":
        return cls(
            tokens=data.get("tokens", 0),
            last_update=data.get("last_update", time.time()),
            cooldown_until=data.get("cooldown_until", 0),
        )


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None
    limit: int = 0
    
    @property
    def retry_after_seconds(self) -> int:
        """Get retry after in whole seconds."""
        return int(self.retry_after) if self.retry_after else 0


# Default rate limit rules
DEFAULT_RULES = {
    RateLimitType.REQUESTS: RateLimitRule(
        limit_type=RateLimitType.REQUESTS,
        max_requests=60,
        window_seconds=60,
        burst_limit=10,
    ),
    RateLimitType.TOKENS: RateLimitRule(
        limit_type=RateLimitType.TOKENS,
        max_requests=100000,  # 100k tokens per hour
        window_seconds=3600,
    ),
    RateLimitType.COMMANDS: RateLimitRule(
        limit_type=RateLimitType.COMMANDS,
        max_requests=30,
        window_seconds=60,
        burst_limit=5,
    ),
    RateLimitType.UPLOADS: RateLimitRule(
        limit_type=RateLimitType.UPLOADS,
        max_requests=10,
        window_seconds=300,  # 10 uploads per 5 minutes
    ),
    RateLimitType.WEBSOCKET: RateLimitRule(
        limit_type=RateLimitType.WEBSOCKET,
        max_requests=100,
        window_seconds=60,  # 100 messages per minute
    ),
}


class RateLimiter:
    """
    Token bucket rate limiter with per-user tracking.
    
    Usage:
        limiter = get_rate_limiter()
        
        # Check if request is allowed
        result = limiter.check(user_id, RateLimitType.REQUESTS)
        if not result.allowed:
            print(f"Rate limited. Retry after {result.retry_after_seconds}s")
        
        # Consume tokens
        limiter.consume(user_id, RateLimitType.TOKENS, count=1500)
        
        # Get current status
        status = limiter.get_status(user_id)
    """
    
    _instance: Optional["RateLimiter"] = None
    
    def __init__(self):
        # user_id -> limit_type -> bucket
        self._buckets: Dict[str, Dict[RateLimitType, RateLimitBucket]] = defaultdict(dict)
        self._rules: Dict[RateLimitType, RateLimitRule] = DEFAULT_RULES.copy()
        self._global_bucket: Dict[RateLimitType, RateLimitBucket] = {}
        self._blocked_users: Dict[str, float] = {}  # user_id -> blocked until
        self._lock = asyncio.Lock()
    
    def set_rule(self, rule: RateLimitRule):
        """Set or update a rate limit rule."""
        self._rules[rule.limit_type] = rule
    
    def get_rule(self, limit_type: RateLimitType) -> Optional[RateLimitRule]:
        """Get rule for a limit type."""
        return self._rules.get(limit_type)
    
    def _get_bucket(self, user_id: str, limit_type: RateLimitType) -> RateLimitBucket:
        """Get or create a bucket for user and limit type."""
        if limit_type not in self._buckets[user_id]:
            rule = self._rules.get(limit_type)
            if rule:
                self._buckets[user_id][limit_type] = RateLimitBucket(
                    tokens=float(rule.max_requests),
                    last_update=time.time(),
                )
            else:
                self._buckets[user_id][limit_type] = RateLimitBucket(
                    tokens=100.0,
                    last_update=time.time(),
                )
        return self._buckets[user_id][limit_type]
    
    def _refill_bucket(self, bucket: RateLimitBucket, rule: RateLimitRule) -> RateLimitBucket:
        """Refill bucket based on time elapsed."""
        now = time.time()
        elapsed = now - bucket.last_update
        
        # Calculate tokens to add
        rate = rule.max_requests / rule.window_seconds
        tokens_to_add = elapsed * rate
        
        bucket.tokens = min(rule.burst_limit, bucket.tokens + tokens_to_add)
        bucket.last_update = now
        
        return bucket
    
    def check(
        self,
        user_id: str,
        limit_type: RateLimitType,
        consume: int = 1,
    ) -> RateLimitResult:
        """
        Check if request is allowed and optionally consume tokens.
        
        Args:
            user_id: User ID
            limit_type: Type of rate limit to check
            consume: Number of tokens to consume if allowed
            
        Returns:
            RateLimitResult with allowed status and metadata
        """
        rule = self._rules.get(limit_type)
        if not rule:
            return RateLimitResult(allowed=True, remaining=999, reset_time=0, limit=999)
        
        # Check if user is blocked
        if user_id in self._blocked_users:
            blocked_until = self._blocked_users[user_id]
            if time.time() < blocked_until:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=blocked_until,
                    retry_after=blocked_until - time.time(),
                    limit=rule.max_requests,
                )
            else:
                del self._blocked_users[user_id]
        
        bucket = self._get_bucket(user_id, limit_type)
        
        # Check cooldown
        if bucket.cooldown_until > time.time():
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=bucket.cooldown_until,
                retry_after=bucket.cooldown_until - time.time(),
                limit=rule.max_requests,
            )
        
        # Refill bucket
        bucket = self._refill_bucket(bucket, rule)
        
        # Check if enough tokens
        if bucket.tokens >= consume:
            bucket.tokens -= consume
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket.tokens),
                reset_time=time.time() + rule.window_seconds,
                limit=rule.max_requests,
            )
        else:
            # Rate limited
            if rule.cooldown_seconds > 0:
                bucket.cooldown_until = time.time() + rule.cooldown_seconds
            
            # Calculate retry after
            tokens_needed = consume - bucket.tokens
            rate = rule.max_requests / rule.window_seconds
            retry_after = tokens_needed / rate
            
            return RateLimitResult(
                allowed=False,
                remaining=int(bucket.tokens),
                reset_time=time.time() + retry_after,
                retry_after=retry_after,
                limit=rule.max_requests,
            )
    
    def consume(self, user_id: str, limit_type: RateLimitType, count: int = 1) -> bool:
        """
        Consume tokens without checking (use after successful check).
        
        Returns True if tokens were available.
        """
        bucket = self._get_bucket(user_id, limit_type)
        rule = self._rules.get(limit_type)
        
        if rule:
            bucket = self._refill_bucket(bucket, rule)
        
        if bucket.tokens >= count:
            bucket.tokens -= count
            return True
        
        bucket.tokens = 0
        return False
    
    def block_user(self, user_id: str, seconds: int):
        """Temporarily block a user."""
        self._blocked_users[user_id] = time.time() + seconds
        logger.warning(f"User {user_id} blocked for {seconds} seconds")
    
    def unblock_user(self, user_id: str):
        """Unblock a user."""
        if user_id in self._blocked_users:
            del self._blocked_users[user_id]
    
    def is_blocked(self, user_id: str) -> bool:
        """Check if user is blocked."""
        if user_id in self._blocked_users:
            if time.time() < self._blocked_users[user_id]:
                return True
            else:
                del self._blocked_users[user_id]
        return False
    
    def reset_user(self, user_id: str):
        """Reset all limits for a user."""
        if user_id in self._buckets:
            del self._buckets[user_id]
        if user_id in self._blocked_users:
            del self._blocked_users[user_id]
    
    def get_status(self, user_id: str) -> Dict[str, dict]:
        """Get rate limit status for all types."""
        status = {}
        
        for limit_type, rule in self._rules.items():
            bucket = self._get_bucket(user_id, limit_type)
            bucket = self._refill_bucket(bucket, rule)
            
            status[limit_type.value] = {
                "limit": rule.max_requests,
                "remaining": int(bucket.tokens),
                "window_seconds": rule.window_seconds,
                "reset_time": bucket.last_update + rule.window_seconds,
            }
        
        return status
    
    def get_status_message(self, user_id: str) -> str:
        """Get formatted status message."""
        status = self.get_status(user_id)
        is_blocked = self.is_blocked(user_id)
        
        lines = [
            "⏱️ **Rate Limits**",
            "",
        ]
        
        if is_blocked:
            blocked_until = self._blocked_users.get(user_id, 0)
            remaining = int(blocked_until - time.time())
            lines.append(f"⚠️ **Blocked** for {remaining} seconds")
            lines.append("")
        
        for limit_type, info in status.items():
            remaining = info["remaining"]
            limit = info["limit"]
            window = info["window_seconds"]
            
            # Calculate percentage
            pct = (remaining / limit) * 100 if limit > 0 else 0
            
            # Status indicator
            if pct > 50:
                indicator = "🟢"
            elif pct > 20:
                indicator = "🟡"
            else:
                indicator = "🔴"
            
            # Format window
            if window >= 3600:
                window_str = f"{window // 3600}h"
            elif window >= 60:
                window_str = f"{window // 60}m"
            else:
                window_str = f"{window}s"
            
            lines.append(f"{indicator} {limit_type}: {remaining}/{limit} ({window_str})")
        
        lines.extend([
            "",
            "Limits reset automatically over time.",
        ])
        
        return "\n".join(lines)


# Rate limit decorator
def rate_limit(limit_type: RateLimitType, consume: int = 1):
    """
    Decorator to apply rate limiting to async functions.
    
    Usage:
        @rate_limit(RateLimitType.REQUESTS)
        async def my_handler(user_id: str, ...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to get user_id from args/kwargs
            user_id = kwargs.get("user_id") or (args[0] if args else "global")
            
            limiter = get_rate_limiter()
            result = limiter.check(str(user_id), limit_type, consume)
            
            if not result.allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Retry after {result.retry_after_seconds} seconds.",
                    retry_after=result.retry_after_seconds,
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int = 0):
        super().__init__(message)
        self.retry_after = retry_after


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def reset_rate_limiter():
    """Reset the rate limiter (for testing)."""
    global _rate_limiter
    _rate_limiter = None


__all__ = [
    "RateLimitType",
    "RateLimitRule",
    "RateLimitBucket",
    "RateLimitResult",
    "RateLimiter",
    "RateLimitExceeded",
    "rate_limit",
    "get_rate_limiter",
    "reset_rate_limiter",
    "DEFAULT_RULES",
]
