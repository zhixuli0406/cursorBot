"""
Configuration management for CursorBot
Load settings from environment variables with validation
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file or environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Bot Settings
    telegram_bot_token: str = Field(
        default="",
        description="Telegram Bot API token from @BotFather",
    )
    telegram_allowed_users: str = Field(
        default="",
        description="Comma-separated list of allowed Telegram user IDs",
    )

    # Cursor Agent Settings
    cursor_workspace_path: str = Field(
        default="",
        description="Path to Cursor workspace directory",
    )
    cursor_mcp_port: int = Field(
        default=3000,
        description="MCP server port for Cursor communication",
    )
    cursor_executable_path: Optional[str] = Field(
        default=None,
        description="Path to Cursor executable",
    )
    cursor_api_key: str = Field(
        default="",
        description="Cursor API key from https://cursor.com/settings",
    )
    cursor_default_repo: str = Field(
        default="",
        description="Default GitHub repository for Cursor Cloud Agents",
    )

    # Server Settings
    server_host: str = Field(
        default="0.0.0.0",
        description="API server host address",
    )
    server_port: int = Field(
        default=8000,
        description="API server port",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Security Settings
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for encryption",
    )
    session_timeout: int = Field(
        default=3600,
        description="Session timeout in seconds",
    )

    # Database Settings
    database_path: str = Field(
        default="./data/cursorbot.db",
        description="SQLite database file path",
    )

    # Logging Settings
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_file_path: str = Field(
        default="./logs/cursorbot.log",
        description="Log file path",
    )

    # AI Provider Settings
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for GPT models",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use",
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        description="Custom OpenAI API base URL (for Azure or proxies)",
    )
    claude_api_key: str = Field(
        default="",
        description="Anthropic Claude API key",
    )
    claude_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use",
    )

    @property
    def allowed_user_ids(self) -> List[int]:
        """Parse comma-separated user IDs into a list of integers."""
        if not self.telegram_allowed_users:
            return []
        try:
            return [
                int(uid.strip())
                for uid in self.telegram_allowed_users.split(",")
                if uid.strip()
            ]
        except ValueError:
            return []

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid choice."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper_v

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        # Database directory
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Log directory
        log_path = Path(self.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
