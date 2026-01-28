"""
Thinking Mode - v0.4 Feature
Extended thinking control for AI models that support deep reasoning.

Commands:
    /think - Show current thinking mode status
    /think off - Disable thinking
    /think low - Light reasoning
    /think medium - Standard reasoning
    /think high - Deep reasoning
    /think xhigh - Maximum reasoning (extended thinking)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Dict, Optional, Tuple
import json

from ..utils.logger import logger


class ThinkingLevel(IntEnum):
    """Thinking levels for AI reasoning depth."""
    OFF = 0        # No extended thinking
    LOW = 1        # Light reasoning (~1000 budget)
    MEDIUM = 2     # Standard reasoning (~5000 budget)
    HIGH = 3       # Deep reasoning (~10000 budget)
    XHIGH = 4      # Maximum reasoning (~25000 budget)


# Budget mapping for thinking levels (tokens allocated for thinking)
THINKING_BUDGETS = {
    ThinkingLevel.OFF: 0,
    ThinkingLevel.LOW: 1024,
    ThinkingLevel.MEDIUM: 5120,
    ThinkingLevel.HIGH: 10240,
    ThinkingLevel.XHIGH: 25600,
}

# Level names for display
LEVEL_NAMES = {
    ThinkingLevel.OFF: "off",
    ThinkingLevel.LOW: "low",
    ThinkingLevel.MEDIUM: "medium",
    ThinkingLevel.HIGH: "high",
    ThinkingLevel.XHIGH: "xhigh",
}

# Reverse mapping
NAME_TO_LEVEL = {v: k for k, v in LEVEL_NAMES.items()}


@dataclass
class ThinkingConfig:
    """Configuration for thinking mode per user."""
    level: ThinkingLevel = ThinkingLevel.OFF
    show_thinking: bool = False  # Show thinking process in output
    auto_adjust: bool = True     # Automatically adjust level based on task complexity
    default_level: ThinkingLevel = ThinkingLevel.MEDIUM  # Default when enabled
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_enabled(self) -> bool:
        """Check if thinking mode is enabled."""
        return self.level > ThinkingLevel.OFF
    
    @property
    def budget(self) -> int:
        """Get thinking budget for current level."""
        return THINKING_BUDGETS[self.level]
    
    @property
    def level_name(self) -> str:
        """Get human-readable level name."""
        return LEVEL_NAMES[self.level]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "show_thinking": self.show_thinking,
            "auto_adjust": self.auto_adjust,
            "default_level": self.default_level.value,
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ThinkingConfig":
        """Create from dictionary."""
        return cls(
            level=ThinkingLevel(data.get("level", 0)),
            show_thinking=data.get("show_thinking", False),
            auto_adjust=data.get("auto_adjust", True),
            default_level=ThinkingLevel(data.get("default_level", 2)),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


class ThinkingManager:
    """
    Manager for AI thinking/reasoning mode.
    
    Usage:
        manager = get_thinking_manager()
        
        # Set thinking level
        manager.set_level(user_id, ThinkingLevel.HIGH)
        
        # Get thinking parameters for LLM
        params = manager.get_thinking_params(user_id)
        # Returns: {"thinking": True, "thinking_budget": 10240}
        
        # Auto-adjust based on task complexity
        level = manager.suggest_level("complex mathematical proof...")
    """
    
    _instance: Optional["ThinkingManager"] = None
    
    def __init__(self):
        self._configs: Dict[str, ThinkingConfig] = {}
        self._data_path = "data/thinking_settings.json"
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from disk."""
        try:
            import os
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, config_data in data.items():
                        self._configs[user_id] = ThinkingConfig.from_dict(config_data)
                logger.debug(f"Loaded thinking settings for {len(self._configs)} users")
        except Exception as e:
            logger.warning(f"Failed to load thinking settings: {e}")
    
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
            logger.warning(f"Failed to save thinking settings: {e}")
    
    def get_config(self, user_id: str) -> ThinkingConfig:
        """Get thinking config for user."""
        if user_id not in self._configs:
            self._configs[user_id] = ThinkingConfig()
        return self._configs[user_id]
    
    def set_level(self, user_id: str, level: ThinkingLevel) -> ThinkingConfig:
        """Set thinking level for user."""
        config = self.get_config(user_id)
        config.level = level
        config.updated_at = datetime.now()
        self._save_settings()
        logger.info(f"Thinking level set to {LEVEL_NAMES[level]} for user {user_id}")
        return config
    
    def set_level_by_name(self, user_id: str, level_name: str) -> Tuple[bool, ThinkingConfig]:
        """
        Set thinking level by name.
        
        Returns:
            Tuple of (success, config)
        """
        level_name = level_name.lower().strip()
        if level_name not in NAME_TO_LEVEL:
            return False, self.get_config(user_id)
        
        return True, self.set_level(user_id, NAME_TO_LEVEL[level_name])
    
    def toggle(self, user_id: str) -> ThinkingConfig:
        """Toggle thinking mode on/off."""
        config = self.get_config(user_id)
        if config.is_enabled:
            config.level = ThinkingLevel.OFF
        else:
            config.level = config.default_level
        config.updated_at = datetime.now()
        self._save_settings()
        return config
    
    def set_show_thinking(self, user_id: str, show: bool) -> ThinkingConfig:
        """Set whether to show thinking process."""
        config = self.get_config(user_id)
        config.show_thinking = show
        config.updated_at = datetime.now()
        self._save_settings()
        return config
    
    def get_thinking_params(self, user_id: str) -> dict:
        """
        Get thinking parameters for LLM API call.
        
        Returns dict with:
            - thinking: bool
            - thinking_budget: int (if thinking is True)
        """
        config = self.get_config(user_id)
        
        if not config.is_enabled:
            return {"thinking": False}
        
        return {
            "thinking": True,
            "thinking_budget": config.budget,
        }
    
    def suggest_level(self, task: str) -> ThinkingLevel:
        """
        Suggest a thinking level based on task complexity.
        
        This is a heuristic approach. Can be enhanced with ML.
        """
        task_lower = task.lower()
        
        # Keywords suggesting high complexity
        high_complexity_keywords = [
            "prove", "proof", "theorem", "mathematical",
            "analyze", "analysis", "complex", "algorithm",
            "optimize", "architecture", "design pattern",
            "security", "vulnerability", "exploit",
        ]
        
        # Keywords suggesting medium complexity
        medium_complexity_keywords = [
            "explain", "compare", "implement", "create",
            "build", "develop", "refactor", "improve",
            "debug", "fix", "issue", "problem",
        ]
        
        # Check for high complexity
        for keyword in high_complexity_keywords:
            if keyword in task_lower:
                return ThinkingLevel.HIGH
        
        # Check for medium complexity
        for keyword in medium_complexity_keywords:
            if keyword in task_lower:
                return ThinkingLevel.MEDIUM
        
        # Default to low for simple tasks
        return ThinkingLevel.LOW
    
    def auto_adjust_level(self, user_id: str, task: str) -> ThinkingConfig:
        """
        Auto-adjust thinking level based on task if auto_adjust is enabled.
        """
        config = self.get_config(user_id)
        
        if config.auto_adjust and config.is_enabled:
            suggested = self.suggest_level(task)
            # Only increase, never decrease automatically
            if suggested > config.level:
                config.level = suggested
                config.updated_at = datetime.now()
                self._save_settings()
                logger.debug(f"Auto-adjusted thinking level to {LEVEL_NAMES[suggested]} for user {user_id}")
        
        return config
    
    def format_thinking_output(
        self,
        user_id: str,
        thinking_content: str,
        max_length: int = 500,
    ) -> Optional[str]:
        """
        Format thinking content for display if show_thinking is enabled.
        
        Returns None if thinking display is disabled.
        """
        config = self.get_config(user_id)
        
        if not config.show_thinking:
            return None
        
        if not thinking_content:
            return None
        
        # Truncate if too long
        if len(thinking_content) > max_length:
            thinking_content = thinking_content[:max_length] + "..."
        
        return f"\n💭 **Thinking Process:**\n```\n{thinking_content}\n```"
    
    def get_status_message(self, user_id: str) -> str:
        """Get status message for /think command."""
        config = self.get_config(user_id)
        
        status_icon = "✅" if config.is_enabled else "⬜"
        
        lines = [
            "🧠 **Thinking Mode**",
            "",
            f"Status: {status_icon} {'Enabled' if config.is_enabled else 'Disabled'}",
            f"Level: **{config.level_name}** ({config.level.value}/4)",
            f"Budget: {config.budget:,} tokens",
            "",
            "**Options:**",
            f"• Show thinking: {'✓' if config.show_thinking else '✗'}",
            f"• Auto-adjust: {'✓' if config.auto_adjust else '✗'}",
            f"• Default level: {LEVEL_NAMES[config.default_level]}",
            "",
            "**Levels:**",
            "• off (0) - No extended thinking",
            "• low (1) - Light reasoning (~1K tokens)",
            "• medium (2) - Standard reasoning (~5K tokens)",
            "• high (3) - Deep reasoning (~10K tokens)",
            "• xhigh (4) - Maximum reasoning (~25K tokens)",
            "",
            "**Commands:**",
            "/think <level> - Set thinking level",
            "/think show on|off - Toggle thinking display",
            "/think auto on|off - Toggle auto-adjust",
            "",
            "**Note:** Requires models that support extended thinking",
            "(e.g., Claude 3.5 with Thinking, GPT-5 Thinking)",
        ]
        
        return "\n".join(lines)


# Singleton instance
_thinking_manager: Optional[ThinkingManager] = None


def get_thinking_manager() -> ThinkingManager:
    """Get the global thinking manager instance."""
    global _thinking_manager
    if _thinking_manager is None:
        _thinking_manager = ThinkingManager()
    return _thinking_manager


def reset_thinking_manager():
    """Reset the thinking manager (for testing)."""
    global _thinking_manager
    _thinking_manager = None


__all__ = [
    "ThinkingLevel",
    "ThinkingConfig",
    "ThinkingManager",
    "THINKING_BUDGETS",
    "LEVEL_NAMES",
    "NAME_TO_LEVEL",
    "get_thinking_manager",
    "reset_thinking_manager",
]
