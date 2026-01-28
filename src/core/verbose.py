"""
Verbose Mode - v0.4 Feature
Detailed output control for debugging and advanced users.

Commands:
    /verbose - Show current verbose mode status
    /verbose on - Enable verbose mode
    /verbose off - Disable verbose mode
    /verbose level <level> - Set verbosity level (0-3)
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Optional
from datetime import datetime
import json

from ..utils.logger import logger


class VerbosityLevel(IntEnum):
    """Verbosity levels for output detail."""
    OFF = 0       # Minimal output
    LOW = 1       # Basic info
    MEDIUM = 2    # Detailed info
    HIGH = 3      # Full debug output


@dataclass
class VerboseConfig:
    """Configuration for verbose mode per user."""
    enabled: bool = False
    level: VerbosityLevel = VerbosityLevel.LOW
    show_tokens: bool = False
    show_timing: bool = True
    show_model_info: bool = True
    show_raw_response: bool = False
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "level": self.level.value,
            "show_tokens": self.show_tokens,
            "show_timing": self.show_timing,
            "show_model_info": self.show_model_info,
            "show_raw_response": self.show_raw_response,
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VerboseConfig":
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", False),
            level=VerbosityLevel(data.get("level", 1)),
            show_tokens=data.get("show_tokens", False),
            show_timing=data.get("show_timing", True),
            show_model_info=data.get("show_model_info", True),
            show_raw_response=data.get("show_raw_response", False),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


class VerboseManager:
    """
    Manager for verbose mode settings per user.
    
    Usage:
        manager = get_verbose_manager()
        
        # Enable verbose mode
        manager.set_enabled(user_id, True)
        
        # Check if verbose
        if manager.is_verbose(user_id):
            # Show detailed output
            pass
        
        # Format verbose info
        info = manager.format_verbose_info(user_id, response_data)
    """
    
    _instance: Optional["VerboseManager"] = None
    
    def __init__(self):
        self._configs: Dict[str, VerboseConfig] = {}
        self._data_path = "data/verbose_settings.json"
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from disk."""
        try:
            import os
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, config_data in data.items():
                        self._configs[user_id] = VerboseConfig.from_dict(config_data)
                logger.debug(f"Loaded verbose settings for {len(self._configs)} users")
        except Exception as e:
            logger.warning(f"Failed to load verbose settings: {e}")
    
    def _save_settings(self):
        """Save settings to disk."""
        try:
            import os
            os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
            data = {
                user_id: config.to_dict()
                for user_id, config in self._configs.items()
            }
            with open(self._data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save verbose settings: {e}")
    
    def get_config(self, user_id: str) -> VerboseConfig:
        """Get verbose config for user."""
        if user_id not in self._configs:
            self._configs[user_id] = VerboseConfig()
        return self._configs[user_id]
    
    def is_verbose(self, user_id: str) -> bool:
        """Check if verbose mode is enabled for user."""
        config = self.get_config(user_id)
        return config.enabled
    
    def get_level(self, user_id: str) -> VerbosityLevel:
        """Get verbosity level for user."""
        config = self.get_config(user_id)
        return config.level if config.enabled else VerbosityLevel.OFF
    
    def set_enabled(self, user_id: str, enabled: bool) -> VerboseConfig:
        """Enable or disable verbose mode."""
        config = self.get_config(user_id)
        config.enabled = enabled
        config.updated_at = datetime.now()
        self._save_settings()
        logger.info(f"Verbose mode {'enabled' if enabled else 'disabled'} for user {user_id}")
        return config
    
    def set_level(self, user_id: str, level: int) -> VerboseConfig:
        """Set verbosity level (0-3)."""
        config = self.get_config(user_id)
        config.level = VerbosityLevel(max(0, min(3, level)))
        config.enabled = level > 0
        config.updated_at = datetime.now()
        self._save_settings()
        return config
    
    def set_option(self, user_id: str, option: str, value: bool) -> VerboseConfig:
        """Set a specific verbose option."""
        config = self.get_config(user_id)
        if hasattr(config, option):
            setattr(config, option, value)
            config.updated_at = datetime.now()
            self._save_settings()
        return config
    
    def format_verbose_info(
        self,
        user_id: str,
        *,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        duration_ms: Optional[float] = None,
        raw_response: Optional[str] = None,
    ) -> Optional[str]:
        """
        Format verbose information based on user settings.
        
        Returns None if verbose mode is disabled.
        """
        config = self.get_config(user_id)
        if not config.enabled:
            return None
        
        lines = []
        
        # Separator
        lines.append("\n━━━ Verbose Info ━━━")
        
        # Model info
        if config.show_model_info and (model or provider):
            if provider:
                lines.append(f"Provider: {provider}")
            if model:
                lines.append(f"Model: {model}")
        
        # Token usage
        if config.show_tokens and (tokens_input is not None or tokens_output is not None):
            token_info = []
            if tokens_input is not None:
                token_info.append(f"In: {tokens_input}")
            if tokens_output is not None:
                token_info.append(f"Out: {tokens_output}")
            if tokens_input is not None and tokens_output is not None:
                token_info.append(f"Total: {tokens_input + tokens_output}")
            lines.append(f"Tokens: {' | '.join(token_info)}")
        
        # Timing
        if config.show_timing and duration_ms is not None:
            if duration_ms < 1000:
                lines.append(f"Duration: {duration_ms:.0f}ms")
            else:
                lines.append(f"Duration: {duration_ms/1000:.2f}s")
        
        # Raw response (only at HIGH level)
        if config.show_raw_response and config.level >= VerbosityLevel.HIGH and raw_response:
            truncated = raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
            lines.append(f"Raw: {truncated}")
        
        if len(lines) <= 1:
            return None
        
        return "\n".join(lines)
    
    def get_status_message(self, user_id: str) -> str:
        """Get status message for /verbose command."""
        config = self.get_config(user_id)
        
        status_icon = "✅" if config.enabled else "⬜"
        level_names = ["OFF", "LOW", "MEDIUM", "HIGH"]
        level_name = level_names[config.level.value]
        
        lines = [
            f"🔍 **Verbose Mode**",
            "",
            f"Status: {status_icon} {'Enabled' if config.enabled else 'Disabled'}",
            f"Level: **{level_name}** ({config.level.value}/3)",
            "",
            "**Options:**",
            f"• Show tokens: {'✓' if config.show_tokens else '✗'}",
            f"• Show timing: {'✓' if config.show_timing else '✗'}",
            f"• Show model info: {'✓' if config.show_model_info else '✗'}",
            f"• Show raw response: {'✓' if config.show_raw_response else '✗'}",
            "",
            "**Commands:**",
            "/verbose on - Enable verbose mode",
            "/verbose off - Disable verbose mode",
            "/verbose level <0-3> - Set verbosity level",
            "/verbose tokens on|off - Toggle token display",
        ]
        
        return "\n".join(lines)


# Singleton instance
_verbose_manager: Optional[VerboseManager] = None


def get_verbose_manager() -> VerboseManager:
    """Get the global verbose manager instance."""
    global _verbose_manager
    if _verbose_manager is None:
        _verbose_manager = VerboseManager()
    return _verbose_manager


def reset_verbose_manager():
    """Reset the verbose manager (for testing)."""
    global _verbose_manager
    _verbose_manager = None


__all__ = [
    "VerbosityLevel",
    "VerboseConfig",
    "VerboseManager",
    "get_verbose_manager",
    "reset_verbose_manager",
]
