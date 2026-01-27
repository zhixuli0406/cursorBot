"""
Configuration management for CursorBot
Load settings from environment variables with validation
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_running_in_docker() -> bool:
    """Check if running inside a Docker container."""
    # Method 1: Check for .dockerenv file
    if os.path.exists("/.dockerenv"):
        return True
    # Method 2: Check cgroup
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except:
        pass
    # Method 3: Check environment variable
    return os.environ.get("RUNNING_IN_DOCKER", "").lower() == "true"


def get_effective_workspace_path() -> str:
    """
    Get the effective workspace path.
    In Docker: returns /workspace
    On host: returns CURSOR_WORKSPACE_PATH from environment
    """
    if is_running_in_docker():
        # In Docker, workspace is mounted at /workspace
        docker_workspace = "/workspace"
        if os.path.exists(docker_workspace):
            return docker_workspace
        # Fallback to /app if /workspace doesn't exist
        return "/app"
    
    # On host, use environment variable
    return os.environ.get("CURSOR_WORKSPACE_PATH", "")


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

    # Workspace Settings (raw value from .env)
    cursor_workspace_path: str = Field(
        default="",
        description="Path to local workspace directory",
    )
    
    @property
    def effective_workspace_path(self) -> str:
        """Get the effective workspace path (Docker-aware)."""
        return get_effective_workspace_path() or self.cursor_workspace_path
    
    @property
    def is_docker(self) -> bool:
        """Check if running in Docker."""
        return is_running_in_docker()

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

    # Cursor Background Agent Settings
    cursor_api_key: str = Field(
        default="",
        description="Cursor API key from https://cursor.com/dashboard?tab=background-agents",
    )
    background_agent_enabled: bool = Field(
        default=False,
        description="Enable Background Agent integration (requires valid API key)",
    )
    background_agent_timeout: int = Field(
        default=300,
        description="Timeout for background agent tasks in seconds",
    )
    background_agent_poll_interval: int = Field(
        default=5,
        description="Poll interval for checking task status in seconds",
    )
    cursor_github_repo: str = Field(
        default="",
        description="Optional GitHub repository URL for Background Agent tasks",
    )

    # ============================================
    # AI / LLM Provider Settings
    # ============================================
    
    # Default LLM Settings
    default_llm_provider: str = Field(
        default="",
        description="Default LLM provider: openai, google, anthropic, openrouter, ollama, custom",
    )
    default_llm_model: str = Field(
        default="",
        description="Default model to use (overrides provider default)",
    )
    
    # OpenAI Settings
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key",
    )
    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL (for Azure or custom endpoints)",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1-preview",
    )
    
    # Google Gemini Settings
    google_generative_ai_api_key: str = Field(
        default="",
        description="Google Gemini API key",
    )
    google_model: str = Field(
        default="gemini-2.0-flash",
        description="Google model: gemini-2.0-flash, gemini-1.5-pro, gemini-pro",
    )
    
    @property
    def google_ai_api_key(self) -> str:
        """Alias for google_generative_ai_api_key."""
        return self.google_generative_ai_api_key
    
    # Anthropic Claude Settings
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic Claude API key",
    )
    anthropic_api_base: str = Field(
        default="https://api.anthropic.com/v1",
        description="Anthropic API base URL",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic model: claude-3-5-sonnet, claude-3-opus, claude-3-haiku",
    )
    
    # OpenRouter Settings (proxy to multiple models)
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key (access to multiple AI models)",
    )
    openrouter_model: str = Field(
        default="google/gemini-2.0-flash-exp:free",
        description="OpenRouter model (e.g., openai/gpt-4o, anthropic/claude-3.5-sonnet)",
    )
    
    # Ollama Settings (local models)
    ollama_enabled: bool = Field(
        default=False,
        description="Enable Ollama local models",
    )
    ollama_api_base: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model: llama3.2, mistral, codellama, phi3, qwen2.5",
    )
    
    # Custom OpenAI-Compatible Settings
    custom_api_key: str = Field(
        default="",
        description="Custom endpoint API key (optional)",
    )
    custom_api_base: str = Field(
        default="",
        description="Custom OpenAI-compatible API base URL",
    )
    custom_model: str = Field(
        default="default",
        description="Custom endpoint model name",
    )
    
    # GitHub Copilot / GitHub Models Settings
    github_token: str = Field(
        default="",
        description="GitHub Personal Access Token for Copilot/GitHub Models",
    )
    copilot_enabled: bool = Field(
        default=False,
        description="Enable GitHub Copilot / GitHub Models provider",
    )
    copilot_model: str = Field(
        default="gpt-4o",
        description="Default model for GitHub Copilot (gpt-4o, claude-3.5-sonnet, etc.)",
    )
    
    # AI General Settings
    custom_prompt: str = Field(
        default="",
        description="Custom instructions to add to AI prompts",
    )
    ai_max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for AI responses",
    )
    ai_temperature: float = Field(
        default=0.7,
        description="AI temperature (0.0-1.0)",
    )

    # Discord Settings
    discord_bot_token: str = Field(
        default="",
        description="Discord bot token",
    )
    discord_allowed_guilds: str = Field(
        default="",
        description="Comma-separated list of allowed Discord guild IDs",
    )
    discord_allowed_users: str = Field(
        default="",
        description="Comma-separated list of allowed Discord user IDs",
    )
    discord_enabled: bool = Field(
        default=False,
        description="Enable Discord bot",
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
