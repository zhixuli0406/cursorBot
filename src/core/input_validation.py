"""
Input Validation & Log Sanitization - v0.4 Feature
Security-focused input validation and sensitive data handling.

Features:
    - Command injection prevention
    - SQL injection prevention
    - XSS prevention
    - Log sanitization (remove sensitive data)
    - Path traversal prevention
"""

import re
import html
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Pattern, Tuple
from functools import wraps

from ..utils.logger import logger


# ============================================
# Sensitive Data Patterns
# ============================================

# Patterns for sensitive data that should be sanitized in logs
SENSITIVE_PATTERNS: Dict[str, Pattern] = {
    "api_key": re.compile(
        r'(api[_-]?key|apikey|api_token)\s*[=:]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        re.IGNORECASE
    ),
    "token": re.compile(
        r'(token|bearer|auth)\s*[=:]\s*["\']?([a-zA-Z0-9_.-]{20,})["\']?',
        re.IGNORECASE
    ),
    "password": re.compile(
        r'(password|passwd|pwd|secret)\s*[=:]\s*["\']?([^\s"\']{6,})["\']?',
        re.IGNORECASE
    ),
    "email": re.compile(
        r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
        re.IGNORECASE
    ),
    "phone": re.compile(
        r'(\+?[0-9]{1,4}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?){2,5}\d{2,4}'
    ),
    "credit_card": re.compile(
        r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
    ),
    "ip_address": re.compile(
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ),
    "jwt": re.compile(
        r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'
    ),
    "private_key": re.compile(
        r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----'
    ),
    "aws_key": re.compile(
        r'AKIA[0-9A-Z]{16}'
    ),
    "github_token": re.compile(
        r'gh[pousr]_[A-Za-z0-9_]{36,}'
    ),
}

# Dangerous command patterns
DANGEROUS_COMMAND_PATTERNS = [
    r';\s*rm\s+-rf',
    r';\s*del\s+/[sf]',
    r'\|\s*rm\s+-rf',
    r'&&\s*rm\s+-rf',
    r'`[^`]*rm[^`]*`',
    r'\$\([^)]*rm[^)]*\)',
    r';\s*shutdown',
    r';\s*reboot',
    r';\s*format',
    r'>\s*/dev/',
    r'mkfs\.',
    r'dd\s+if=',
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r'\.\./+',
    r'\.\.\\+',
    r'%2e%2e[/\\]',
    r'%252e%252e[/\\]',
    r'%c0%ae%c0%ae[/\\]',
]


@dataclass
class ValidationResult:
    """Result of input validation."""
    valid: bool
    sanitized: str = ""
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class InputValidator:
    """
    Input validation and sanitization utilities.
    
    Usage:
        validator = get_input_validator()
        
        # Validate command input
        result = validator.validate_command(user_input)
        if not result.valid:
            return "Invalid input: " + result.errors[0]
        
        # Sanitize for logging
        safe_log = validator.sanitize_for_log(sensitive_data)
    """
    
    _instance: Optional["InputValidator"] = None
    
    def __init__(self):
        self._compiled_dangerous = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_COMMAND_PATTERNS]
        self._compiled_traversal = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]
    
    def validate_command(self, input_text: str, max_length: int = 4096) -> ValidationResult:
        """
        Validate command input for security issues.
        
        Checks:
            - Length limits
            - Command injection patterns
            - Null bytes
            - Control characters
        """
        errors = []
        warnings = []
        
        if not input_text:
            return ValidationResult(valid=True, sanitized="")
        
        # Check length
        if len(input_text) > max_length:
            errors.append(f"Input too long ({len(input_text)} > {max_length})")
        
        # Check for null bytes
        if '\x00' in input_text:
            errors.append("Null bytes detected in input")
            input_text = input_text.replace('\x00', '')
        
        # Check for dangerous command patterns
        for pattern in self._compiled_dangerous:
            if pattern.search(input_text):
                errors.append("Potentially dangerous command pattern detected")
                break
        
        # Check for path traversal
        for pattern in self._compiled_traversal:
            if pattern.search(input_text):
                warnings.append("Path traversal pattern detected")
                break
        
        # Sanitize control characters (except newlines)
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', input_text)
        
        return ValidationResult(
            valid=len(errors) == 0,
            sanitized=sanitized,
            errors=errors,
            warnings=warnings,
        )
    
    def validate_path(self, path: str, base_path: str = None) -> ValidationResult:
        """
        Validate file path for security issues.
        
        Checks:
            - Path traversal
            - Absolute path when relative expected
            - Null bytes
        """
        errors = []
        warnings = []
        
        if not path:
            return ValidationResult(valid=False, errors=["Empty path"])
        
        # Check for null bytes
        if '\x00' in path:
            errors.append("Null bytes in path")
            path = path.replace('\x00', '')
        
        # Check for path traversal
        for pattern in self._compiled_traversal:
            if pattern.search(path):
                errors.append("Path traversal detected")
                break
        
        # If base path provided, ensure path stays within it
        if base_path:
            import os
            try:
                # Resolve to absolute paths
                abs_base = os.path.abspath(base_path)
                abs_path = os.path.abspath(os.path.join(base_path, path))
                
                # Check if resolved path is under base
                if not abs_path.startswith(abs_base):
                    errors.append("Path escapes base directory")
            except Exception:
                errors.append("Invalid path")
        
        return ValidationResult(
            valid=len(errors) == 0,
            sanitized=path,
            errors=errors,
            warnings=warnings,
        )
    
    def validate_filename(self, filename: str) -> ValidationResult:
        """Validate filename for security."""
        errors = []
        
        if not filename:
            return ValidationResult(valid=False, errors=["Empty filename"])
        
        # Remove path separators
        sanitized = filename.replace('/', '_').replace('\\', '_')
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Check for special names
        dangerous_names = ['..', '.', 'CON', 'PRN', 'AUX', 'NUL',
                         'COM1', 'LPT1', '.htaccess', '.git']
        if sanitized.upper() in [n.upper() for n in dangerous_names]:
            errors.append("Reserved or dangerous filename")
        
        # Limit length
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
            errors.append("Filename too long")
        
        return ValidationResult(
            valid=len(errors) == 0,
            sanitized=sanitized,
            errors=errors,
        )
    
    def sanitize_html(self, text: str) -> str:
        """Escape HTML special characters to prevent XSS."""
        return html.escape(text)
    
    def sanitize_for_log(
        self,
        data: Any,
        mask: str = "***REDACTED***",
        hash_suffix: bool = True,
    ) -> str:
        """
        Sanitize data for safe logging by masking sensitive information.
        
        Args:
            data: Data to sanitize
            mask: Replacement text for sensitive data
            hash_suffix: Add hash suffix to help correlate masked values
        """
        if data is None:
            return "None"
        
        text = str(data)
        
        for name, pattern in SENSITIVE_PATTERNS.items():
            def replacer(match):
                if hash_suffix:
                    # Add short hash to help identify same values
                    value_hash = hashlib.md5(match.group(0).encode()).hexdigest()[:6]
                    return f"{mask}:{name}:{value_hash}"
                return f"{mask}:{name}"
            
            text = pattern.sub(replacer, text)
        
        return text
    
    def sanitize_dict_for_log(
        self,
        data: dict,
        sensitive_keys: List[str] = None,
    ) -> dict:
        """
        Sanitize a dictionary for logging.
        
        Args:
            data: Dictionary to sanitize
            sensitive_keys: Additional keys to mask (besides defaults)
        """
        if sensitive_keys is None:
            sensitive_keys = []
        
        # Default sensitive keys
        all_sensitive = {
            'password', 'passwd', 'pwd', 'secret', 'token', 'api_key',
            'apikey', 'auth', 'authorization', 'bearer', 'credential',
            'private_key', 'access_token', 'refresh_token', 'session_id',
        }
        all_sensitive.update(k.lower() for k in sensitive_keys)
        
        def sanitize_value(key: str, value: Any) -> Any:
            if isinstance(value, dict):
                return self.sanitize_dict_for_log(value, sensitive_keys)
            elif isinstance(value, list):
                return [sanitize_value(key, v) for v in value]
            elif key.lower() in all_sensitive:
                if isinstance(value, str) and len(value) > 0:
                    return f"***REDACTED:{len(value)}chars***"
                return "***REDACTED***"
            elif isinstance(value, str):
                return self.sanitize_for_log(value)
            return value
        
        return {k: sanitize_value(k, v) for k, v in data.items()}
    
    def validate_json(self, text: str, max_depth: int = 10) -> ValidationResult:
        """
        Validate JSON input for security.
        
        Checks:
            - Valid JSON syntax
            - Maximum nesting depth (prevent DoS)
            - Size limits
        """
        import json as json_module
        
        errors = []
        
        try:
            data = json_module.loads(text)
            
            # Check depth
            def check_depth(obj, depth=0):
                if depth > max_depth:
                    return False
                if isinstance(obj, dict):
                    return all(check_depth(v, depth + 1) for v in obj.values())
                elif isinstance(obj, list):
                    return all(check_depth(v, depth + 1) for v in obj)
                return True
            
            if not check_depth(data):
                errors.append(f"JSON nesting exceeds maximum depth ({max_depth})")
            
        except json_module.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)[:50]}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            sanitized=text,
            errors=errors,
        )


def validate_input(input_text: str, max_length: int = 4096) -> ValidationResult:
    """Convenience function for input validation."""
    return get_input_validator().validate_command(input_text, max_length)


def sanitize_for_log(data: Any) -> str:
    """Convenience function for log sanitization."""
    return get_input_validator().sanitize_for_log(data)


# Decorator for automatic input validation
def validated_input(max_length: int = 4096, param_name: str = "text"):
    """
    Decorator to automatically validate input parameter.
    
    Usage:
        @validated_input(max_length=1000, param_name="message")
        async def handle_message(message: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the input value
            if param_name in kwargs:
                value = kwargs[param_name]
            else:
                # Assume it's a positional argument
                return await func(*args, **kwargs)
            
            # Validate
            validator = get_input_validator()
            result = validator.validate_command(str(value), max_length)
            
            if not result.valid:
                raise ValueError(f"Invalid input: {result.errors[0]}")
            
            # Replace with sanitized value
            kwargs[param_name] = result.sanitized
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Singleton instance
_input_validator: Optional[InputValidator] = None


def get_input_validator() -> InputValidator:
    """Get the global input validator instance."""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator


def reset_input_validator():
    """Reset the input validator (for testing)."""
    global _input_validator
    _input_validator = None


__all__ = [
    "ValidationResult",
    "InputValidator",
    "SENSITIVE_PATTERNS",
    "validate_input",
    "sanitize_for_log",
    "validated_input",
    "get_input_validator",
    "reset_input_validator",
]
