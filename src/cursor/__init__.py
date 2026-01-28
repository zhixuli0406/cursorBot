"""
Cursor module for CursorBot
Provides workspace management and CLI Agent integration
"""

from .agent import WorkspaceAgent, CursorAgent
from .cli_agent import (
    CursorCLIAgent,
    CLIConfig,
    CLIResult,
    CLIStatus,
    get_cli_agent,
    is_cli_available,
)
from .file_operations import FileOperations, EditResult
from .terminal import TerminalManager, CommandResult, CommandStatus

__all__ = [
    "WorkspaceAgent",
    "CursorAgent",
    "CursorCLIAgent",
    "CLIConfig",
    "CLIResult",
    "CLIStatus",
    "get_cli_agent",
    "is_cli_available",
    "FileOperations",
    "EditResult",
    "TerminalManager",
    "CommandResult",
    "CommandStatus",
]
