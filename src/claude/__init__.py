"""
Claude module for ClaudeBot

Provides Claude Code CLI integration for AI-powered features.
"""

from .cli_agent import (
    ClaudeCodeCLIAgent,
    CLIConfig,
    CLIResult,
    CLIStatus,
    get_cli_agent,
    reset_cli_agent,
    is_cli_available,
    get_cli_working_directory,
)

from . import utils

__all__ = [
    # CLI Agent
    "ClaudeCodeCLIAgent",
    "CLIConfig",
    "CLIResult",
    "CLIStatus",
    # Global functions
    "get_cli_agent",
    "reset_cli_agent",
    "is_cli_available",
    "get_cli_working_directory",
    # Utils module
    "utils",
]

__version__ = "2.0.0"
