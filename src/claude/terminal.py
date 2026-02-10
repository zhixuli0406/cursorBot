"""
Terminal Manager for ClaudeBot

Simplified terminal command execution wrapper.
This is a compatibility layer - for new code, use claude.utils.run_command directly.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from . import utils
from ..utils.logger import logger


class CommandStatus(Enum):
    """Command execution status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CommandResult:
    """Result from command execution."""
    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    status: CommandStatus = CommandStatus.COMPLETED

    @property
    def output(self) -> str:
        """Get combined output (stdout + stderr)."""
        result = self.stdout
        if self.stderr:
            result += "\n" + self.stderr
        return result.strip()


class TerminalManager:
    """
    Terminal command execution manager.

    This is a compatibility wrapper around claude.utils.run_command.
    For new code, prefer using claude.utils directly.
    """

    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize terminal manager.

        Args:
            workspace_path: Working directory for commands
        """
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        logger.info(f"TerminalManager initialized with workspace: {self.workspace_path}")

    async def run_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None
    ) -> CommandResult:
        """
        Run a shell command.

        Args:
            command: Command to execute
            timeout: Timeout in seconds (None = no timeout)
            cwd: Working directory (None = use workspace_path)

        Returns:
            CommandResult with execution details
        """
        work_dir = Path(cwd) if cwd else self.workspace_path

        try:
            stdout, stderr, exit_code = await utils.run_command(
                command,
                cwd=str(work_dir),
                timeout=timeout
            )

            success = exit_code == 0
            status = CommandStatus.COMPLETED if success else CommandStatus.FAILED

            return CommandResult(
                success=success,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                status=status
            )

        except asyncio.TimeoutError:
            logger.error(f"Command timed out: {command[:50]}...")
            return CommandResult(
                success=False,
                exit_code=-1,
                stderr=f"Command timed out after {timeout}s",
                status=CommandStatus.TIMEOUT
            )
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                success=False,
                exit_code=-1,
                stderr=str(e),
                status=CommandStatus.FAILED
            )

    async def run(
        self,
        command: str,
        timeout: Optional[int] = None
    ) -> CommandResult:
        """
        Run a command (alias for run_command).

        Args:
            command: Command to execute
            timeout: Timeout in seconds

        Returns:
            CommandResult with execution details
        """
        return await self.run_command(command, timeout=timeout)

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> tuple[bool, str, str, int]:
        """
        Execute a command and return tuple (for backward compatibility).

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            capture_output: Whether to capture output (always True)

        Returns:
            Tuple of (success, stdout, stderr, exit_code)
        """
        result = await self.run_command(command, timeout=timeout)
        return (result.success, result.stdout, result.stderr, result.exit_code)

    def get_working_directory(self) -> str:
        """
        Get current working directory.

        Returns:
            Working directory path as string
        """
        return str(self.workspace_path)

    def set_working_directory(self, path: str) -> None:
        """
        Set working directory.

        Args:
            path: New working directory path
        """
        self.workspace_path = Path(path).resolve()
        logger.info(f"Working directory changed to: {self.workspace_path}")


__all__ = ["TerminalManager", "CommandResult", "CommandStatus"]
