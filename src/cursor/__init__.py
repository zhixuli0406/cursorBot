"""
Cursor module for CursorBot
Provides workspace management, CLI Agent, and Background Agent integration
"""

from .agent import WorkspaceAgent, CursorAgent
from .background_agent import CursorBackgroundAgent, TaskTracker
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
    "CursorBackgroundAgent",
    "TaskTracker",
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
