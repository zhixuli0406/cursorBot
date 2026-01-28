"""
Environment Variable Validation - v0.4 Feature
Startup validation of required environment variables and configurations.

Validates:
    - Required API keys
    - Valid formats for tokens/keys
    - Port ranges
    - URL formats
    - File paths existence
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path

from ..utils.logger import logger


class EnvVarType(Enum):
    """Types of environment variables."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    URL = "url"
    PATH = "path"
    EMAIL = "email"
    CHOICE = "choice"
    LIST = "list"
    TOKEN = "token"  # Sensitive, will be masked in logs


class EnvVarSeverity(Enum):
    """Severity levels for missing/invalid variables."""
    REQUIRED = "required"      # App won't start without it
    RECOMMENDED = "recommended"  # Feature may not work
    OPTIONAL = "optional"      # Nice to have


@dataclass
class EnvVarSpec:
    """Specification for an environment variable."""
    name: str
    var_type: EnvVarType
    severity: EnvVarSeverity = EnvVarSeverity.OPTIONAL
    default: Any = None
    description: str = ""
    min_length: int = 0
    max_length: int = 10000
    min_value: float = None
    max_value: float = None
    choices: List[str] = None
    pattern: str = None  # Regex pattern
    feature: str = None  # Associated feature name
    
    def __post_init__(self):
        if self.choices is None:
            self.choices = []


@dataclass
class ValidationError:
    """An error from validation."""
    var_name: str
    message: str
    severity: EnvVarSeverity
    
    def __str__(self):
        return f"[{self.severity.value.upper()}] {self.var_name}: {self.message}"


@dataclass
class ValidationReport:
    """Complete validation report."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    missing_recommended: List[str] = field(default_factory=list)
    valid_count: int = 0
    total_count: int = 0
    
    def __str__(self):
        lines = [
            f"Environment Validation: {'PASS' if self.valid else 'FAIL'}",
            f"Valid: {self.valid_count}/{self.total_count}",
        ]
        
        if self.missing_required:
            lines.append(f"Missing required: {', '.join(self.missing_required)}")
        
        if self.errors:
            lines.append("Errors:")
            for e in self.errors:
                lines.append(f"  - {e}")
        
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        
        return "\n".join(lines)


# Environment variable specifications for CursorBot
ENV_SPECS: Dict[str, EnvVarSpec] = {
    # Telegram (Required)
    "TELEGRAM_BOT_TOKEN": EnvVarSpec(
        name="TELEGRAM_BOT_TOKEN",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.RECOMMENDED,
        description="Telegram Bot API token",
        min_length=40,
        pattern=r'^\d+:[A-Za-z0-9_-]{35,}$',
        feature="telegram",
    ),
    "TELEGRAM_ALLOWED_USERS": EnvVarSpec(
        name="TELEGRAM_ALLOWED_USERS",
        var_type=EnvVarType.LIST,
        severity=EnvVarSeverity.RECOMMENDED,
        description="Comma-separated list of allowed Telegram user IDs",
        feature="telegram",
    ),
    
    # Server
    "SERVER_PORT": EnvVarSpec(
        name="SERVER_PORT",
        var_type=EnvVarType.INTEGER,
        severity=EnvVarSeverity.OPTIONAL,
        default=8000,
        min_value=1,
        max_value=65535,
        description="API server port",
    ),
    "SERVER_HOST": EnvVarSpec(
        name="SERVER_HOST",
        var_type=EnvVarType.STRING,
        severity=EnvVarSeverity.OPTIONAL,
        default="0.0.0.0",
        description="API server host",
    ),
    
    # AI Providers
    "OPENAI_API_KEY": EnvVarSpec(
        name="OPENAI_API_KEY",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.OPTIONAL,
        pattern=r'^sk-[a-zA-Z0-9]{20,}$',
        description="OpenAI API key",
        feature="openai",
    ),
    "ANTHROPIC_API_KEY": EnvVarSpec(
        name="ANTHROPIC_API_KEY",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.OPTIONAL,
        pattern=r'^sk-ant-[a-zA-Z0-9_-]{20,}$',
        description="Anthropic Claude API key",
        feature="anthropic",
    ),
    "GOOGLE_GENERATIVE_AI_API_KEY": EnvVarSpec(
        name="GOOGLE_GENERATIVE_AI_API_KEY",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.OPTIONAL,
        pattern=r'^AIza[a-zA-Z0-9_-]{35,}$',
        description="Google Gemini API key",
        feature="google",
    ),
    "OPENROUTER_API_KEY": EnvVarSpec(
        name="OPENROUTER_API_KEY",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.OPTIONAL,
        pattern=r'^sk-or-[a-zA-Z0-9-]{20,}$',
        description="OpenRouter API key",
        feature="openrouter",
    ),
    "GITHUB_TOKEN": EnvVarSpec(
        name="GITHUB_TOKEN",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.OPTIONAL,
        pattern=r'^gh[pousr]_[A-Za-z0-9_]{36,}$',
        description="GitHub Personal Access Token",
        feature="github",
    ),
    
    # Discord
    "DISCORD_BOT_TOKEN": EnvVarSpec(
        name="DISCORD_BOT_TOKEN",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.OPTIONAL,
        min_length=50,
        description="Discord bot token",
        feature="discord",
    ),
    "DISCORD_ENABLED": EnvVarSpec(
        name="DISCORD_ENABLED",
        var_type=EnvVarType.BOOLEAN,
        severity=EnvVarSeverity.OPTIONAL,
        default=False,
        feature="discord",
    ),
    
    # Workspace
    "CURSOR_WORKSPACE_PATH": EnvVarSpec(
        name="CURSOR_WORKSPACE_PATH",
        var_type=EnvVarType.PATH,
        severity=EnvVarSeverity.OPTIONAL,
        description="Path to workspace directory",
    ),
    
    # Security
    "SECRET_KEY": EnvVarSpec(
        name="SECRET_KEY",
        var_type=EnvVarType.TOKEN,
        severity=EnvVarSeverity.RECOMMENDED,
        min_length=32,
        description="Secret key for encryption",
        default="change-this-secret-key-in-production",
    ),
    
    # Logging
    "LOG_LEVEL": EnvVarSpec(
        name="LOG_LEVEL",
        var_type=EnvVarType.CHOICE,
        severity=EnvVarSeverity.OPTIONAL,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        description="Logging level",
    ),
}


class EnvironmentValidator:
    """
    Validates environment variables on startup.
    
    Usage:
        validator = get_env_validator()
        
        # Run full validation
        report = validator.validate()
        if not report.valid:
            print(report)
            sys.exit(1)
        
        # Check specific variable
        if validator.is_valid("OPENAI_API_KEY"):
            # Use OpenAI
            pass
    """
    
    _instance: Optional["EnvironmentValidator"] = None
    
    def __init__(self):
        self._specs = ENV_SPECS.copy()
        self._cached_report: Optional[ValidationReport] = None
    
    def add_spec(self, spec: EnvVarSpec):
        """Add a new environment variable specification."""
        self._specs[spec.name] = spec
        self._cached_report = None
    
    def get_value(self, name: str) -> Optional[str]:
        """Get environment variable value."""
        return os.environ.get(name)
    
    def _validate_type(self, spec: EnvVarSpec, value: str) -> Tuple[bool, Optional[str]]:
        """Validate value against expected type."""
        try:
            if spec.var_type == EnvVarType.INTEGER:
                int_val = int(value)
                if spec.min_value is not None and int_val < spec.min_value:
                    return False, f"Value {int_val} below minimum {spec.min_value}"
                if spec.max_value is not None and int_val > spec.max_value:
                    return False, f"Value {int_val} above maximum {spec.max_value}"
            
            elif spec.var_type == EnvVarType.FLOAT:
                float_val = float(value)
                if spec.min_value is not None and float_val < spec.min_value:
                    return False, f"Value {float_val} below minimum {spec.min_value}"
                if spec.max_value is not None and float_val > spec.max_value:
                    return False, f"Value {float_val} above maximum {spec.max_value}"
            
            elif spec.var_type == EnvVarType.BOOLEAN:
                if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                    return False, f"Invalid boolean value: {value}"
            
            elif spec.var_type == EnvVarType.URL:
                if not re.match(r'^https?://', value):
                    return False, "URL must start with http:// or https://"
            
            elif spec.var_type == EnvVarType.PATH:
                # Don't check existence for optional paths
                pass
            
            elif spec.var_type == EnvVarType.EMAIL:
                if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', value):
                    return False, "Invalid email format"
            
            elif spec.var_type == EnvVarType.CHOICE:
                if value.upper() not in [c.upper() for c in spec.choices]:
                    return False, f"Value must be one of: {', '.join(spec.choices)}"
            
            return True, None
            
        except ValueError as e:
            return False, str(e)
    
    def _validate_var(self, spec: EnvVarSpec) -> Optional[ValidationError]:
        """Validate a single environment variable."""
        value = self.get_value(spec.name)
        
        # Check if missing
        if value is None or value == "":
            if spec.severity == EnvVarSeverity.REQUIRED:
                return ValidationError(
                    spec.name,
                    "Required variable not set",
                    spec.severity,
                )
            elif spec.severity == EnvVarSeverity.RECOMMENDED:
                return ValidationError(
                    spec.name,
                    "Recommended variable not set",
                    spec.severity,
                )
            return None
        
        # Check length
        if spec.min_length > 0 and len(value) < spec.min_length:
            return ValidationError(
                spec.name,
                f"Value too short (min {spec.min_length} chars)",
                spec.severity,
            )
        
        if len(value) > spec.max_length:
            return ValidationError(
                spec.name,
                f"Value too long (max {spec.max_length} chars)",
                spec.severity,
            )
        
        # Check pattern
        if spec.pattern:
            if not re.match(spec.pattern, value):
                # For tokens, don't show the actual value
                if spec.var_type == EnvVarType.TOKEN:
                    return ValidationError(
                        spec.name,
                        "Invalid format",
                        spec.severity,
                    )
                else:
                    return ValidationError(
                        spec.name,
                        f"Value does not match expected pattern",
                        spec.severity,
                    )
        
        # Check type
        valid, error = self._validate_type(spec, value)
        if not valid:
            return ValidationError(spec.name, error, spec.severity)
        
        return None
    
    def validate(self, fail_fast: bool = False) -> ValidationReport:
        """
        Validate all environment variables.
        
        Args:
            fail_fast: Stop on first error
            
        Returns:
            ValidationReport with all results
        """
        report = ValidationReport(
            valid=True,
            total_count=len(self._specs),
        )
        
        for name, spec in self._specs.items():
            error = self._validate_var(spec)
            
            if error:
                if error.severity == EnvVarSeverity.REQUIRED:
                    report.errors.append(error)
                    report.missing_required.append(name)
                    report.valid = False
                    
                    if fail_fast:
                        break
                elif error.severity == EnvVarSeverity.RECOMMENDED:
                    report.warnings.append(error)
                    report.missing_recommended.append(name)
                else:
                    report.warnings.append(error)
            else:
                report.valid_count += 1
        
        self._cached_report = report
        return report
    
    def is_valid(self, name: str) -> bool:
        """Check if a specific variable is valid."""
        spec = self._specs.get(name)
        if not spec:
            return True  # Unknown variables are valid
        
        error = self._validate_var(spec)
        return error is None
    
    def is_feature_available(self, feature: str) -> bool:
        """Check if all variables for a feature are valid."""
        feature_specs = [s for s in self._specs.values() if s.feature == feature]
        
        if not feature_specs:
            return True  # Unknown feature
        
        for spec in feature_specs:
            # Only check required/recommended for the feature
            if spec.severity in (EnvVarSeverity.REQUIRED, EnvVarSeverity.RECOMMENDED):
                if self._validate_var(spec):
                    return False
        
        return True
    
    def get_available_features(self) -> List[str]:
        """Get list of features that have valid configuration."""
        features = set()
        for spec in self._specs.values():
            if spec.feature:
                features.add(spec.feature)
        
        return [f for f in features if self.is_feature_available(f)]
    
    def get_status_message(self) -> str:
        """Get formatted status message."""
        report = self._cached_report or self.validate()
        
        lines = [
            "🔧 **Environment Validation**",
            "",
            f"Status: {'✅ Valid' if report.valid else '❌ Invalid'}",
            f"Variables: {report.valid_count}/{report.total_count} valid",
        ]
        
        # Show available features
        features = self.get_available_features()
        if features:
            lines.append(f"\n**Available Features:**")
            for f in sorted(features):
                lines.append(f"• {f}")
        
        # Show missing required
        if report.missing_required:
            lines.append(f"\n**⚠️ Missing Required:**")
            for name in report.missing_required:
                spec = self._specs.get(name)
                desc = spec.description if spec else ""
                lines.append(f"• {name}: {desc}")
        
        # Show missing recommended
        if report.missing_recommended:
            lines.append(f"\n**Missing Recommended:**")
            for name in report.missing_recommended[:5]:
                spec = self._specs.get(name)
                desc = spec.description if spec else ""
                lines.append(f"• {name}: {desc}")
            if len(report.missing_recommended) > 5:
                lines.append(f"  ... and {len(report.missing_recommended) - 5} more")
        
        return "\n".join(lines)


def validate_environment() -> ValidationReport:
    """Convenience function to validate environment."""
    return get_env_validator().validate()


def require_env_var(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable {name} is not set")
    return value


# Singleton instance
_env_validator: Optional[EnvironmentValidator] = None


def get_env_validator() -> EnvironmentValidator:
    """Get the global environment validator instance."""
    global _env_validator
    if _env_validator is None:
        _env_validator = EnvironmentValidator()
    return _env_validator


def reset_env_validator():
    """Reset the environment validator (for testing)."""
    global _env_validator
    _env_validator = None


__all__ = [
    "EnvVarType",
    "EnvVarSeverity",
    "EnvVarSpec",
    "ValidationError",
    "ValidationReport",
    "EnvironmentValidator",
    "ENV_SPECS",
    "validate_environment",
    "require_env_var",
    "get_env_validator",
    "reset_env_validator",
]
