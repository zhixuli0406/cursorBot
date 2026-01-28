"""
Unified Error Handling - v0.4 Feature
Consistent error types and messages across the application.

Provides:
    - Standardized error types
    - Error codes for API responses
    - Localized error messages (i18n ready)
    - Error tracking and logging
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional
import traceback
import json

from ..utils.logger import logger


class ErrorCode(IntEnum):
    """Standardized error codes."""
    # General errors (1xxx)
    UNKNOWN = 1000
    INTERNAL_ERROR = 1001
    NOT_IMPLEMENTED = 1002
    TIMEOUT = 1003
    
    # Validation errors (2xxx)
    VALIDATION_ERROR = 2000
    INVALID_INPUT = 2001
    MISSING_REQUIRED = 2002
    INVALID_FORMAT = 2003
    VALUE_OUT_OF_RANGE = 2004
    
    # Authentication/Authorization errors (3xxx)
    AUTH_ERROR = 3000
    UNAUTHORIZED = 3001
    FORBIDDEN = 3002
    TOKEN_EXPIRED = 3003
    INVALID_TOKEN = 3004
    ELEVATION_REQUIRED = 3005
    
    # Resource errors (4xxx)
    RESOURCE_ERROR = 4000
    NOT_FOUND = 4001
    ALREADY_EXISTS = 4002
    RESOURCE_EXHAUSTED = 4003
    
    # Rate limiting errors (5xxx)
    RATE_LIMIT_ERROR = 5000
    TOO_MANY_REQUESTS = 5001
    QUOTA_EXCEEDED = 5002
    
    # External service errors (6xxx)
    EXTERNAL_ERROR = 6000
    LLM_ERROR = 6001
    PLATFORM_ERROR = 6002
    API_ERROR = 6003
    NETWORK_ERROR = 6004
    
    # Command errors (7xxx)
    COMMAND_ERROR = 7000
    INVALID_COMMAND = 7001
    COMMAND_FAILED = 7002
    PERMISSION_DENIED = 7003


# Error messages (i18n ready)
ERROR_MESSAGES: Dict[ErrorCode, Dict[str, str]] = {
    ErrorCode.UNKNOWN: {
        "en": "An unknown error occurred",
        "zh-TW": "發生未知錯誤",
        "zh-CN": "发生未知错误",
    },
    ErrorCode.INTERNAL_ERROR: {
        "en": "Internal server error",
        "zh-TW": "內部伺服器錯誤",
        "zh-CN": "内部服务器错误",
    },
    ErrorCode.TIMEOUT: {
        "en": "Operation timed out",
        "zh-TW": "操作逾時",
        "zh-CN": "操作超时",
    },
    ErrorCode.VALIDATION_ERROR: {
        "en": "Validation failed",
        "zh-TW": "驗證失敗",
        "zh-CN": "验证失败",
    },
    ErrorCode.INVALID_INPUT: {
        "en": "Invalid input provided",
        "zh-TW": "輸入無效",
        "zh-CN": "输入无效",
    },
    ErrorCode.MISSING_REQUIRED: {
        "en": "Required field is missing",
        "zh-TW": "缺少必要欄位",
        "zh-CN": "缺少必要字段",
    },
    ErrorCode.UNAUTHORIZED: {
        "en": "Authentication required",
        "zh-TW": "需要驗證身份",
        "zh-CN": "需要验证身份",
    },
    ErrorCode.FORBIDDEN: {
        "en": "Permission denied",
        "zh-TW": "權限不足",
        "zh-CN": "权限不足",
    },
    ErrorCode.ELEVATION_REQUIRED: {
        "en": "Elevated privileges required. Use /elevated on",
        "zh-TW": "需要提升權限。請使用 /elevated on",
        "zh-CN": "需要提升权限。请使用 /elevated on",
    },
    ErrorCode.NOT_FOUND: {
        "en": "Resource not found",
        "zh-TW": "找不到資源",
        "zh-CN": "找不到资源",
    },
    ErrorCode.ALREADY_EXISTS: {
        "en": "Resource already exists",
        "zh-TW": "資源已存在",
        "zh-CN": "资源已存在",
    },
    ErrorCode.TOO_MANY_REQUESTS: {
        "en": "Too many requests. Please slow down",
        "zh-TW": "請求過於頻繁，請稍後再試",
        "zh-CN": "请求过于频繁，请稍后再试",
    },
    ErrorCode.QUOTA_EXCEEDED: {
        "en": "Quota exceeded",
        "zh-TW": "配額已用盡",
        "zh-CN": "配额已用尽",
    },
    ErrorCode.LLM_ERROR: {
        "en": "AI model error",
        "zh-TW": "AI 模型錯誤",
        "zh-CN": "AI 模型错误",
    },
    ErrorCode.INVALID_COMMAND: {
        "en": "Invalid command",
        "zh-TW": "無效的指令",
        "zh-CN": "无效的指令",
    },
    ErrorCode.COMMAND_FAILED: {
        "en": "Command execution failed",
        "zh-TW": "指令執行失敗",
        "zh-CN": "指令执行失败",
    },
    ErrorCode.PERMISSION_DENIED: {
        "en": "You don't have permission to perform this action",
        "zh-TW": "您沒有權限執行此操作",
        "zh-CN": "您没有权限执行此操作",
    },
}


@dataclass
class ErrorContext:
    """Context information for an error."""
    user_id: Optional[str] = None
    platform: Optional[str] = None
    command: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CursorBotError(Exception):
    """
    Base exception class for CursorBot.
    
    Usage:
        raise CursorBotError(
            code=ErrorCode.INVALID_INPUT,
            message="User ID is required",
            details={"field": "user_id"},
        )
    """
    code: ErrorCode
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    context: Optional[ErrorContext] = None
    cause: Optional[Exception] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.message:
            self.message = self.get_localized_message()
        super().__init__(self.message)
    
    def get_localized_message(self, locale: str = "zh-TW") -> str:
        """Get error message in specified locale."""
        messages = ERROR_MESSAGES.get(self.code, {})
        return messages.get(locale, messages.get("en", str(self.code)))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = {
            "error": True,
            "code": self.code.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
        
        if self.details:
            result["details"] = self.details
        
        if self.context:
            result["context"] = {
                "user_id": self.context.user_id,
                "platform": self.context.platform,
                "request_id": self.context.request_id,
            }
        
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def log(self, level: str = "error"):
        """Log the error."""
        log_data = {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }
        
        if self.context:
            log_data["user_id"] = self.context.user_id
            log_data["platform"] = self.context.platform
        
        if self.cause:
            log_data["cause"] = str(self.cause)
            log_data["traceback"] = traceback.format_exception(
                type(self.cause), self.cause, self.cause.__traceback__
            )
        
        if level == "error":
            logger.error(f"CursorBotError: {log_data}")
        elif level == "warning":
            logger.warning(f"CursorBotError: {log_data}")
        else:
            logger.info(f"CursorBotError: {log_data}")


# Convenience error classes
class ValidationError(CursorBotError):
    """Validation error."""
    def __init__(self, message: str = "", field: str = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            **kwargs
        )


class AuthenticationError(CursorBotError):
    """Authentication error."""
    def __init__(self, message: str = "", **kwargs):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            **kwargs
        )


class PermissionError(CursorBotError):
    """Permission error."""
    def __init__(self, message: str = "", action: str = None, **kwargs):
        details = kwargs.pop("details", {})
        if action:
            details["action"] = action
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            details=details,
            **kwargs
        )


class ElevationRequiredError(CursorBotError):
    """Elevation required error."""
    def __init__(self, action: str = None, **kwargs):
        details = kwargs.pop("details", {})
        if action:
            details["action"] = action
        super().__init__(
            code=ErrorCode.ELEVATION_REQUIRED,
            details=details,
            **kwargs
        )


class NotFoundError(CursorBotError):
    """Resource not found error."""
    def __init__(self, resource: str = "", **kwargs):
        details = kwargs.pop("details", {})
        if resource:
            details["resource"] = resource
        message = f"Resource not found: {resource}" if resource else ""
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            details=details,
            **kwargs
        )


class RateLimitError(CursorBotError):
    """Rate limit error."""
    def __init__(self, retry_after: int = 0, **kwargs):
        details = kwargs.pop("details", {})
        details["retry_after"] = retry_after
        super().__init__(
            code=ErrorCode.TOO_MANY_REQUESTS,
            details=details,
            **kwargs
        )


class LLMError(CursorBotError):
    """LLM provider error."""
    def __init__(self, provider: str = "", message: str = "", **kwargs):
        details = kwargs.pop("details", {})
        if provider:
            details["provider"] = provider
        super().__init__(
            code=ErrorCode.LLM_ERROR,
            message=message or f"AI model error ({provider})",
            details=details,
            **kwargs
        )


class CommandError(CursorBotError):
    """Command execution error."""
    def __init__(self, command: str = "", message: str = "", **kwargs):
        details = kwargs.pop("details", {})
        if command:
            details["command"] = command
        super().__init__(
            code=ErrorCode.COMMAND_FAILED,
            message=message or f"Command failed: {command}",
            details=details,
            **kwargs
        )


class ErrorHandler:
    """
    Centralized error handling and formatting.
    
    Usage:
        handler = get_error_handler()
        
        # Format error for user
        user_message = handler.format_for_user(error)
        
        # Format error for API
        api_response = handler.format_for_api(error)
    """
    
    _instance: Optional["ErrorHandler"] = None
    
    def __init__(self):
        self._locale = "zh-TW"
        self._show_details = False  # Production default
        self._error_count = 0
    
    def set_locale(self, locale: str):
        """Set default locale."""
        self._locale = locale
    
    def set_show_details(self, show: bool):
        """Set whether to show error details to users."""
        self._show_details = show
    
    def format_for_user(
        self,
        error: Exception,
        locale: str = None,
        show_details: bool = None,
    ) -> str:
        """
        Format error message for end user display.
        
        Returns user-friendly error message.
        """
        locale = locale or self._locale
        show_details = show_details if show_details is not None else self._show_details
        
        if isinstance(error, CursorBotError):
            message = error.get_localized_message(locale)
            
            # Add emoji based on error type
            emoji = self._get_error_emoji(error.code)
            
            result = f"{emoji} {message}"
            
            if show_details and error.details:
                detail_str = ", ".join(
                    f"{k}: {v}" for k, v in error.details.items()
                    if k not in ("traceback", "cause")
                )
                if detail_str:
                    result += f"\n\n詳細: {detail_str}"
            
            return result
        else:
            # Generic error
            return f"❌ 發生錯誤: {str(error)[:100]}"
    
    def format_for_api(
        self,
        error: Exception,
        include_traceback: bool = False,
    ) -> dict:
        """
        Format error for API response.
        
        Returns dict suitable for JSON response.
        """
        if isinstance(error, CursorBotError):
            result = error.to_dict()
        else:
            result = {
                "error": True,
                "code": ErrorCode.UNKNOWN.value,
                "message": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        
        if include_traceback:
            result["traceback"] = traceback.format_exc()
        
        return result
    
    def _get_error_emoji(self, code: ErrorCode) -> str:
        """Get emoji for error code."""
        if code.value < 2000:
            return "❌"  # General errors
        elif code.value < 3000:
            return "⚠️"  # Validation errors
        elif code.value < 4000:
            return "🔒"  # Auth errors
        elif code.value < 5000:
            return "🔍"  # Resource errors
        elif code.value < 6000:
            return "⏱️"  # Rate limit errors
        elif code.value < 7000:
            return "🌐"  # External errors
        else:
            return "💬"  # Command errors
    
    def handle(
        self,
        error: Exception,
        context: ErrorContext = None,
        log: bool = True,
    ) -> CursorBotError:
        """
        Handle and optionally log an error.
        
        Wraps non-CursorBotError in CursorBotError.
        """
        self._error_count += 1
        
        if isinstance(error, CursorBotError):
            if context:
                error.context = context
            if log:
                error.log()
            return error
        else:
            # Wrap in CursorBotError
            wrapped = CursorBotError(
                code=ErrorCode.UNKNOWN,
                message=str(error),
                context=context,
                cause=error,
            )
            if log:
                wrapped.log()
            return wrapped
    
    def get_stats(self) -> dict:
        """Get error statistics."""
        return {
            "total_errors": self._error_count,
        }


# Singleton instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def reset_error_handler():
    """Reset the error handler (for testing)."""
    global _error_handler
    _error_handler = None


__all__ = [
    "ErrorCode",
    "ERROR_MESSAGES",
    "ErrorContext",
    "CursorBotError",
    "ValidationError",
    "AuthenticationError",
    "PermissionError",
    "ElevationRequiredError",
    "NotFoundError",
    "RateLimitError",
    "LLMError",
    "CommandError",
    "ErrorHandler",
    "get_error_handler",
    "reset_error_handler",
]
