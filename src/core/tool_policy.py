"""
Tool Policy System for CursorBot

Provides:
- Tool access control
- Permission management
- Rate limiting for tools
- Audit logging
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class PermissionLevel(Enum):
    """Permission levels for tool access."""
    DENY = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


class PolicyAction(Enum):
    """Actions when policy check fails."""
    DENY = "deny"
    WARN = "warn"
    LOG = "log"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    max_calls: int
    period_seconds: int
    per_user: bool = True
    
    def __post_init__(self):
        self._calls: dict[str, list[float]] = {}  # user_id -> timestamps
    
    def check(self, user_id: str = "global") -> bool:
        """Check if rate limit allows the call."""
        key = user_id if self.per_user else "global"
        now = time.time()
        cutoff = now - self.period_seconds
        
        # Clean old entries
        if key in self._calls:
            self._calls[key] = [t for t in self._calls[key] if t > cutoff]
        else:
            self._calls[key] = []
        
        # Check limit
        if len(self._calls[key]) >= self.max_calls:
            return False
        
        # Record call
        self._calls[key].append(now)
        return True
    
    def get_wait_time(self, user_id: str = "global") -> float:
        """Get seconds until next allowed call."""
        key = user_id if self.per_user else "global"
        if key not in self._calls or len(self._calls[key]) < self.max_calls:
            return 0
        
        oldest = min(self._calls[key])
        return max(0, oldest + self.period_seconds - time.time())


@dataclass
class ToolPolicy:
    """Policy for a specific tool."""
    tool_name: str
    enabled: bool = True
    permission_level: PermissionLevel = PermissionLevel.EXECUTE
    allowed_users: list[int] = field(default_factory=list)  # Empty = all users
    denied_users: list[int] = field(default_factory=list)
    rate_limit: Optional[RateLimit] = None
    require_approval: bool = False
    audit_log: bool = True
    action_on_deny: PolicyAction = PolicyAction.DENY
    description: str = ""
    
    def check_permission(self, user_id: int, required_level: PermissionLevel) -> bool:
        """Check if user has required permission level."""
        if not self.enabled:
            return False
        
        if user_id in self.denied_users:
            return False
        
        if self.allowed_users and user_id not in self.allowed_users:
            return False
        
        return self.permission_level.value >= required_level.value
    
    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "enabled": self.enabled,
            "permission_level": self.permission_level.name,
            "require_approval": self.require_approval,
            "audit_log": self.audit_log,
        }


@dataclass
class PolicyCheckResult:
    """Result of a policy check."""
    allowed: bool
    tool_name: str
    user_id: int
    reason: Optional[str] = None
    action: PolicyAction = PolicyAction.DENY
    wait_time: float = 0
    requires_approval: bool = False
    
    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "tool_name": self.tool_name,
            "user_id": self.user_id,
            "reason": self.reason,
            "action": self.action.value,
            "wait_time": self.wait_time,
            "requires_approval": self.requires_approval,
        }


@dataclass
class AuditEntry:
    """Audit log entry."""
    timestamp: datetime
    tool_name: str
    user_id: int
    action: str
    allowed: bool
    details: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "user_id": self.user_id,
            "action": self.action,
            "allowed": self.allowed,
            "details": self.details,
        }


class ToolPolicyManager:
    """
    Manages tool access policies.
    """
    
    # Default rate limits
    DEFAULT_RATE_LIMITS = {
        "terminal": RateLimit(max_calls=10, period_seconds=60),
        "file_write": RateLimit(max_calls=20, period_seconds=60),
        "browser": RateLimit(max_calls=5, period_seconds=60),
        "sandbox": RateLimit(max_calls=3, period_seconds=60),
    }
    
    # Dangerous tools requiring extra permissions
    DANGEROUS_TOOLS = {
        "terminal_exec",
        "file_delete",
        "sandbox_exec",
        "system_command",
    }
    
    def __init__(self):
        self._policies: dict[str, ToolPolicy] = {}
        self._audit_log: list[AuditEntry] = []
        self._global_enabled: bool = True
        self._admin_users: set[int] = set()
        self._approval_callbacks: dict[str, Callable] = {}
    
    def set_policy(self, policy: ToolPolicy) -> None:
        """Set or update a tool policy."""
        self._policies[policy.tool_name] = policy
        logger.info(f"Set policy for tool: {policy.tool_name}")
    
    def get_policy(self, tool_name: str) -> Optional[ToolPolicy]:
        """Get policy for a tool."""
        return self._policies.get(tool_name)
    
    def remove_policy(self, tool_name: str) -> bool:
        """Remove a tool policy."""
        if tool_name in self._policies:
            del self._policies[tool_name]
            return True
        return False
    
    def add_admin(self, user_id: int) -> None:
        """Add an admin user (bypasses all policies)."""
        self._admin_users.add(user_id)
    
    def remove_admin(self, user_id: int) -> None:
        """Remove an admin user."""
        self._admin_users.discard(user_id)
    
    def check_policy(
        self,
        tool_name: str,
        user_id: int,
        required_level: PermissionLevel = PermissionLevel.EXECUTE,
    ) -> PolicyCheckResult:
        """
        Check if a user can use a tool.
        
        Args:
            tool_name: Tool to check
            user_id: User ID
            required_level: Required permission level
        
        Returns:
            PolicyCheckResult
        """
        # Global disable check
        if not self._global_enabled:
            return PolicyCheckResult(
                allowed=False,
                tool_name=tool_name,
                user_id=user_id,
                reason="Tool policies globally disabled",
                action=PolicyAction.DENY,
            )
        
        # Admin bypass
        if user_id in self._admin_users:
            self._log_audit(tool_name, user_id, "admin_access", True)
            return PolicyCheckResult(
                allowed=True,
                tool_name=tool_name,
                user_id=user_id,
                reason="Admin access",
            )
        
        # Get policy
        policy = self._policies.get(tool_name)
        
        # No policy = allow by default (unless dangerous)
        if not policy:
            if tool_name in self.DANGEROUS_TOOLS:
                return PolicyCheckResult(
                    allowed=False,
                    tool_name=tool_name,
                    user_id=user_id,
                    reason=f"Dangerous tool '{tool_name}' requires explicit policy",
                    action=PolicyAction.DENY,
                )
            return PolicyCheckResult(
                allowed=True,
                tool_name=tool_name,
                user_id=user_id,
            )
        
        # Check enabled
        if not policy.enabled:
            return PolicyCheckResult(
                allowed=False,
                tool_name=tool_name,
                user_id=user_id,
                reason="Tool is disabled",
                action=policy.action_on_deny,
            )
        
        # Check permission
        if not policy.check_permission(user_id, required_level):
            self._log_audit(tool_name, user_id, "permission_denied", False)
            return PolicyCheckResult(
                allowed=False,
                tool_name=tool_name,
                user_id=user_id,
                reason="Insufficient permissions",
                action=policy.action_on_deny,
            )
        
        # Check rate limit
        if policy.rate_limit:
            if not policy.rate_limit.check(str(user_id)):
                wait_time = policy.rate_limit.get_wait_time(str(user_id))
                self._log_audit(tool_name, user_id, "rate_limited", False)
                return PolicyCheckResult(
                    allowed=False,
                    tool_name=tool_name,
                    user_id=user_id,
                    reason="Rate limit exceeded",
                    action=PolicyAction.DENY,
                    wait_time=wait_time,
                )
        
        # Check approval required
        if policy.require_approval:
            self._log_audit(tool_name, user_id, "approval_required", False)
            return PolicyCheckResult(
                allowed=False,
                tool_name=tool_name,
                user_id=user_id,
                reason="Approval required",
                action=PolicyAction.REQUIRE_APPROVAL,
                requires_approval=True,
            )
        
        # All checks passed
        if policy.audit_log:
            self._log_audit(tool_name, user_id, "allowed", True)
        
        return PolicyCheckResult(
            allowed=True,
            tool_name=tool_name,
            user_id=user_id,
        )
    
    def _log_audit(
        self,
        tool_name: str,
        user_id: int,
        action: str,
        allowed: bool,
        details: dict = None,
    ) -> None:
        """Log an audit entry."""
        entry = AuditEntry(
            timestamp=datetime.now(),
            tool_name=tool_name,
            user_id=user_id,
            action=action,
            allowed=allowed,
            details=details or {},
        )
        self._audit_log.append(entry)
        
        # Keep only last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
    
    def get_audit_log(
        self,
        tool_name: str = None,
        user_id: int = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get audit log entries."""
        entries = self._audit_log
        
        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]
        
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        
        return [e.to_dict() for e in entries[-limit:]]
    
    def get_all_policies(self) -> list[dict]:
        """Get all configured policies."""
        return [p.to_dict() for p in self._policies.values()]
    
    def enable_globally(self) -> None:
        """Enable tool policies globally."""
        self._global_enabled = True
    
    def disable_globally(self) -> None:
        """Disable tool policies globally."""
        self._global_enabled = False
    
    def get_stats(self) -> dict:
        """Get policy statistics."""
        return {
            "total_policies": len(self._policies),
            "enabled_policies": sum(1 for p in self._policies.values() if p.enabled),
            "audit_log_entries": len(self._audit_log),
            "admin_users": len(self._admin_users),
            "global_enabled": self._global_enabled,
        }


def policy_check(tool_name: str, required_level: PermissionLevel = PermissionLevel.EXECUTE):
    """
    Decorator for policy-protected functions.
    
    Usage:
        @policy_check("terminal", PermissionLevel.EXECUTE)
        async def run_command(user_id: int, command: str):
            ...
    """
    def decorator(func):
        async def wrapper(*args, user_id: int = 0, **kwargs):
            manager = get_tool_policy_manager()
            result = manager.check_policy(tool_name, user_id, required_level)
            
            if not result.allowed:
                raise PermissionError(f"Policy denied: {result.reason}")
            
            return await func(*args, user_id=user_id, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# ============================================
# Global Instance
# ============================================

_policy_manager: Optional[ToolPolicyManager] = None


def get_tool_policy_manager() -> ToolPolicyManager:
    """Get the global tool policy manager instance."""
    global _policy_manager
    if _policy_manager is None:
        _policy_manager = ToolPolicyManager()
    return _policy_manager


__all__ = [
    "PermissionLevel",
    "PolicyAction",
    "RateLimit",
    "ToolPolicy",
    "PolicyCheckResult",
    "AuditEntry",
    "ToolPolicyManager",
    "policy_check",
    "get_tool_policy_manager",
]
