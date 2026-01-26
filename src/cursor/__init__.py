"""
Cursor module for CursorBot
Provides workspace management and Background Agent integration
"""

from .agent import WorkspaceAgent, CursorAgent
from .background_agent import CursorBackgroundAgent, TaskTracker
from .file_operations import FileOperations, EditResult
from .terminal import TerminalManager, CommandResult, CommandStatus

__all__ = [
    "WorkspaceAgent",
    "CursorAgent",
    "CursorBackgroundAgent",
    "TaskTracker",
    "FileOperations",
    "EditResult",
    "TerminalManager",
    "CommandResult",
    "CommandStatus",
]
