"""
Command Alias System - v0.4 Feature
User-defined command aliases for faster interaction.

Commands:
    /alias - List all aliases
    /alias add <name> <command> - Create an alias
    /alias remove <name> - Remove an alias
    /alias clear - Clear all aliases
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import re

from ..utils.logger import logger


@dataclass
class CommandAlias:
    """A command alias definition."""
    name: str                    # Alias name (without /)
    command: str                 # Full command to execute (without /)
    args: List[str] = None       # Optional default arguments
    description: str = ""        # User description
    created_at: datetime = field(default_factory=datetime.now)
    use_count: int = 0          # How many times used
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "use_count": self.use_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CommandAlias":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            command=data["command"],
            args=data.get("args", []),
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            use_count=data.get("use_count", 0),
        )


# Built-in system aliases (cannot be overridden)
SYSTEM_ALIASES = {
    "h": "help",
    "s": "status",
    "m": "mode",
    "n": "new",
    "c": "clear",
    "ws": "workspace",
    "sk": "skills",
    "ag": "agent",
    "v": "verbose",
    "el": "elevated",
    "th": "think",
}

# Reserved command names (cannot be used as aliases)
RESERVED_COMMANDS = {
    "start", "help", "status", "mode", "model", "climodel",
    "new", "clear", "memory", "workspace", "skills", "stats",
    "agent", "rag", "index", "doctor", "session", "compact",
    "alias", "verbose", "elevated", "think", "notify",
}


class AliasManager:
    """
    Manager for user-defined command aliases.
    
    Usage:
        manager = get_alias_manager()
        
        # Add an alias
        manager.add_alias(user_id, "gpt", "model set openai gpt-4o")
        
        # Resolve an alias
        command, args = manager.resolve(user_id, "gpt")
        # Returns: ("model", ["set", "openai", "gpt-4o"])
        
        # Check if alias exists
        if manager.has_alias(user_id, "gpt"):
            ...
    """
    
    _instance: Optional["AliasManager"] = None
    
    def __init__(self):
        self._aliases: Dict[str, Dict[str, CommandAlias]] = {}  # user_id -> {alias_name -> alias}
        self._data_path = "data/command_aliases.json"
        self._max_aliases_per_user = 50
        self._load_settings()
    
    def _load_settings(self):
        """Load aliases from disk."""
        try:
            import os
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, aliases_data in data.items():
                        self._aliases[user_id] = {
                            name: CommandAlias.from_dict(alias_data)
                            for name, alias_data in aliases_data.items()
                        }
                logger.debug(f"Loaded aliases for {len(self._aliases)} users")
        except Exception as e:
            logger.warning(f"Failed to load aliases: {e}")
    
    def _save_settings(self):
        """Save aliases to disk."""
        try:
            import os
            os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
            data = {
                user_id: {
                    name: alias.to_dict()
                    for name, alias in aliases.items()
                }
                for user_id, aliases in self._aliases.items()
            }
            with open(self._data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save aliases: {e}")
    
    def _validate_alias_name(self, name: str) -> Tuple[bool, str]:
        """Validate alias name."""
        name = name.lower().strip()
        
        if not name:
            return False, "Alias name cannot be empty"
        
        if len(name) > 20:
            return False, "Alias name too long (max 20 characters)"
        
        if not re.match(r'^[a-z0-9_]+$', name):
            return False, "Alias name can only contain letters, numbers, and underscores"
        
        if name in RESERVED_COMMANDS:
            return False, f"'{name}' is a reserved command name"
        
        if name in SYSTEM_ALIASES:
            return False, f"'{name}' is a system alias"
        
        return True, ""
    
    def get_user_aliases(self, user_id: str) -> Dict[str, CommandAlias]:
        """Get all aliases for a user."""
        return self._aliases.get(user_id, {})
    
    def has_alias(self, user_id: str, name: str) -> bool:
        """Check if an alias exists."""
        name = name.lower().strip()
        
        # Check system aliases first
        if name in SYSTEM_ALIASES:
            return True
        
        # Check user aliases
        return name in self.get_user_aliases(user_id)
    
    def get_alias(self, user_id: str, name: str) -> Optional[CommandAlias]:
        """Get an alias by name."""
        name = name.lower().strip()
        return self.get_user_aliases(user_id).get(name)
    
    def add_alias(
        self,
        user_id: str,
        name: str,
        command: str,
        description: str = "",
    ) -> Tuple[bool, str]:
        """
        Add a new alias.
        
        Args:
            user_id: User ID
            name: Alias name (without /)
            command: Command to execute (without /, can include args)
            description: Optional description
            
        Returns:
            Tuple of (success, message)
        """
        name = name.lower().strip()
        command = command.strip()
        
        # Validate name
        valid, error = self._validate_alias_name(name)
        if not valid:
            return False, error
        
        # Parse command
        if command.startswith("/"):
            command = command[1:]
        
        parts = command.split(maxsplit=1)
        base_command = parts[0]
        args = parts[1].split() if len(parts) > 1 else []
        
        # Check user limit
        user_aliases = self.get_user_aliases(user_id)
        if len(user_aliases) >= self._max_aliases_per_user and name not in user_aliases:
            return False, f"Maximum aliases reached ({self._max_aliases_per_user})"
        
        # Initialize user aliases if needed
        if user_id not in self._aliases:
            self._aliases[user_id] = {}
        
        # Create or update alias
        self._aliases[user_id][name] = CommandAlias(
            name=name,
            command=base_command,
            args=args,
            description=description,
        )
        
        self._save_settings()
        logger.info(f"Alias '{name}' -> '{command}' created for user {user_id}")
        
        return True, f"Alias '/{name}' -> '/{command}' created"
    
    def remove_alias(self, user_id: str, name: str) -> Tuple[bool, str]:
        """
        Remove an alias.
        
        Returns:
            Tuple of (success, message)
        """
        name = name.lower().strip()
        
        if name in SYSTEM_ALIASES:
            return False, f"Cannot remove system alias '{name}'"
        
        user_aliases = self.get_user_aliases(user_id)
        if name not in user_aliases:
            return False, f"Alias '{name}' not found"
        
        del self._aliases[user_id][name]
        self._save_settings()
        
        return True, f"Alias '/{name}' removed"
    
    def clear_aliases(self, user_id: str) -> int:
        """Clear all aliases for a user. Returns count removed."""
        count = len(self.get_user_aliases(user_id))
        self._aliases[user_id] = {}
        self._save_settings()
        return count
    
    def resolve(
        self,
        user_id: str,
        name: str,
        extra_args: List[str] = None,
    ) -> Tuple[Optional[str], List[str]]:
        """
        Resolve an alias to its command.
        
        Args:
            user_id: User ID
            name: Alias name (without /)
            extra_args: Additional arguments from user input
            
        Returns:
            Tuple of (command, args) or (None, []) if not found
        """
        name = name.lower().strip()
        
        if extra_args is None:
            extra_args = []
        
        # Check system aliases first
        if name in SYSTEM_ALIASES:
            return SYSTEM_ALIASES[name], extra_args
        
        # Check user aliases
        alias = self.get_alias(user_id, name)
        if alias is None:
            return None, []
        
        # Update use count
        alias.use_count += 1
        self._save_settings()
        
        # Combine alias args with extra args
        all_args = alias.args + extra_args
        
        return alias.command, all_args
    
    def get_all_aliases(self, user_id: str) -> List[dict]:
        """Get all aliases (system + user) as list."""
        aliases = []
        
        # System aliases
        for name, command in SYSTEM_ALIASES.items():
            aliases.append({
                "name": name,
                "command": command,
                "type": "system",
            })
        
        # User aliases
        for name, alias in self.get_user_aliases(user_id).items():
            full_command = alias.command
            if alias.args:
                full_command += " " + " ".join(alias.args)
            aliases.append({
                "name": name,
                "command": full_command,
                "description": alias.description,
                "use_count": alias.use_count,
                "type": "user",
            })
        
        return sorted(aliases, key=lambda a: a["name"])
    
    def get_status_message(self, user_id: str) -> str:
        """Get status message for /alias command."""
        all_aliases = self.get_all_aliases(user_id)
        user_aliases = [a for a in all_aliases if a["type"] == "user"]
        system_aliases = [a for a in all_aliases if a["type"] == "system"]
        
        lines = [
            "📎 **Command Aliases**",
            "",
        ]
        
        # System aliases
        if system_aliases:
            lines.append("**System Aliases:**")
            for a in system_aliases[:10]:
                lines.append(f"• /{a['name']} → /{a['command']}")
            if len(system_aliases) > 10:
                lines.append(f"  ... and {len(system_aliases) - 10} more")
            lines.append("")
        
        # User aliases
        if user_aliases:
            lines.append(f"**Your Aliases ({len(user_aliases)}/{self._max_aliases_per_user}):**")
            for a in user_aliases[:10]:
                desc = f" - {a['description']}" if a.get('description') else ""
                lines.append(f"• /{a['name']} → /{a['command']}{desc}")
            if len(user_aliases) > 10:
                lines.append(f"  ... and {len(user_aliases) - 10} more")
        else:
            lines.append("No custom aliases defined.")
        
        lines.extend([
            "",
            "**Commands:**",
            "/alias add <name> <command> - Create alias",
            "/alias remove <name> - Remove alias",
            "/alias clear - Clear all aliases",
            "",
            "**Example:**",
            "/alias add gpt model set openai gpt-4o",
            "Then use: /gpt",
        ])
        
        return "\n".join(lines)


# Singleton instance
_alias_manager: Optional[AliasManager] = None


def get_alias_manager() -> AliasManager:
    """Get the global alias manager instance."""
    global _alias_manager
    if _alias_manager is None:
        _alias_manager = AliasManager()
    return _alias_manager


def reset_alias_manager():
    """Reset the alias manager (for testing)."""
    global _alias_manager
    _alias_manager = None


__all__ = [
    "CommandAlias",
    "AliasManager",
    "SYSTEM_ALIASES",
    "RESERVED_COMMANDS",
    "get_alias_manager",
    "reset_alias_manager",
]
