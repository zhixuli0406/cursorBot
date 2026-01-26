"""
Cursor command definitions and utilities
Encapsulates common Cursor operations
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class CommandType(Enum):
    """Types of commands that can be sent to Cursor."""

    ASK = "ask"
    CHAT = "chat"
    CODE = "code"
    EDIT = "edit"
    SEARCH = "search"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_LIST = "file_list"
    TERMINAL = "terminal"
    DEBUG = "debug"


@dataclass
class CursorCommand:
    """
    Represents a command to be sent to Cursor Agent.
    """

    type: CommandType
    content: str
    file_path: Optional[str] = None
    options: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert command to dictionary for transmission."""
        data = {
            "type": self.type.value,
            "content": self.content,
        }
        if self.file_path:
            data["file_path"] = self.file_path
        if self.options:
            data["options"] = self.options
        return data


@dataclass
class CommandResult:
    """
    Result from a Cursor command execution.
    """

    success: bool
    content: str
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> "CommandResult":
        """Create CommandResult from API response."""
        if "error" in response:
            return cls(
                success=False,
                content="",
                error=response["error"],
            )
        return cls(
            success=True,
            content=response.get("content", response.get("result", "")),
            metadata=response.get("metadata"),
        )


class CommandBuilder:
    """
    Builder for creating complex Cursor commands.
    """

    def __init__(self, command_type: CommandType):
        self._type = command_type
        self._content = ""
        self._file_path: Optional[str] = None
        self._options: dict[str, Any] = {}

    def content(self, text: str) -> "CommandBuilder":
        """Set command content."""
        self._content = text
        return self

    def file(self, path: str) -> "CommandBuilder":
        """Set target file path."""
        self._file_path = path
        return self

    def option(self, key: str, value: Any) -> "CommandBuilder":
        """Add command option."""
        self._options[key] = value
        return self

    def build(self) -> CursorCommand:
        """Build the command."""
        return CursorCommand(
            type=self._type,
            content=self._content,
            file_path=self._file_path,
            options=self._options if self._options else None,
        )


# Convenience functions for creating commands
def ask(question: str) -> CursorCommand:
    """Create an ASK command."""
    return CommandBuilder(CommandType.ASK).content(question).build()


def chat(message: str) -> CursorCommand:
    """Create a CHAT command."""
    return CommandBuilder(CommandType.CHAT).content(message).build()


def code(instruction: str, file_path: Optional[str] = None) -> CursorCommand:
    """Create a CODE command."""
    builder = CommandBuilder(CommandType.CODE).content(instruction)
    if file_path:
        builder.file(file_path)
    return builder.build()


def edit(changes: str, file_path: str) -> CursorCommand:
    """Create an EDIT command."""
    return (
        CommandBuilder(CommandType.EDIT)
        .content(changes)
        .file(file_path)
        .build()
    )


def search(query: str, scope: Optional[str] = None) -> CursorCommand:
    """Create a SEARCH command."""
    builder = CommandBuilder(CommandType.SEARCH).content(query)
    if scope:
        builder.option("scope", scope)
    return builder.build()


def read_file(path: str) -> CursorCommand:
    """Create a FILE_READ command."""
    return CommandBuilder(CommandType.FILE_READ).file(path).content("").build()


def write_file(path: str, content: str) -> CursorCommand:
    """Create a FILE_WRITE command."""
    return CommandBuilder(CommandType.FILE_WRITE).file(path).content(content).build()


def list_files(directory: str = ".") -> CursorCommand:
    """Create a FILE_LIST command."""
    return CommandBuilder(CommandType.FILE_LIST).file(directory).content("").build()


def run_terminal(command: str) -> CursorCommand:
    """Create a TERMINAL command."""
    return CommandBuilder(CommandType.TERMINAL).content(command).build()


__all__ = [
    "CommandType",
    "CursorCommand",
    "CommandResult",
    "CommandBuilder",
    "ask",
    "chat",
    "code",
    "edit",
    "search",
    "read_file",
    "write_file",
    "list_files",
    "run_terminal",
]
