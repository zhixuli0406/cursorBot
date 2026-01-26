"""
Cursor module for CursorBot
Provides workspace management and MCP server for Cursor IDE integration
"""

from .agent import WorkspaceAgent, CursorAgent
from .file_operations import FileOperations, EditResult
from .terminal import TerminalManager, CommandResult, CommandStatus

__all__ = [
    "WorkspaceAgent",
    "CursorAgent",
    "FileOperations",
    "EditResult",
    "TerminalManager",
    "CommandResult",
    "CommandStatus",
]
