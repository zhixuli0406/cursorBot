"""
Terminal execution module for CursorBot
Provides safe command execution with output streaming
"""

import asyncio
import os
import shlex
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

from ..utils.logger import logger


class CommandStatus(Enum):
    """Status of a terminal command."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class CommandResult:
    """Result of a terminal command execution."""

    command: str
    status: CommandStatus
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @property
    def success(self) -> bool:
        """Check if command executed successfully."""
        return self.status == CommandStatus.COMPLETED and self.exit_code == 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "command": self.command,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


@dataclass
class RunningCommand:
    """Tracks a running command."""

    id: str
    command: str
    process: asyncio.subprocess.Process
    started_at: datetime
    cwd: str
    output_callback: Optional[Callable] = None


class TerminalManager:
    """
    Terminal command execution manager.
    Handles safe command execution with output streaming and timeout.
    """

    # Commands that are blocked for security
    BLOCKED_COMMANDS = {
        "rm -rf /",
        "rm -rf /*",
        ":(){ :|:& };:",  # Fork bomb
        "mkfs",
        "dd if=/dev/zero",
        "chmod -R 777 /",
        "> /dev/sda",
    }

    # Patterns that are potentially dangerous
    DANGEROUS_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        "sudo rm",
        "> /dev/sd",
        "mkfs.",
        "dd if=",
        ":()",
        "chmod 777 /",
    ]

    def __init__(
        self,
        workspace_path: str,
        max_output_size: int = 1024 * 1024,  # 1MB
        default_timeout: int = 300,  # 5 minutes
        allowed_shells: Optional[list[str]] = None,
    ):
        """
        Initialize terminal manager.

        Args:
            workspace_path: Default working directory
            max_output_size: Maximum output size to capture
            default_timeout: Default command timeout in seconds
            allowed_shells: List of allowed shell commands
        """
        self.workspace_path = Path(workspace_path)
        self.max_output_size = max_output_size
        self.default_timeout = default_timeout
        self.allowed_shells = allowed_shells or ["/bin/bash", "/bin/sh", "/bin/zsh"]

        self._running_commands: dict[str, RunningCommand] = {}
        self._command_history: list[CommandResult] = []
        self._next_id = 1

    def _get_next_id(self) -> str:
        """Generate next command ID."""
        cmd_id = f"cmd_{self._next_id}"
        self._next_id += 1
        return cmd_id

    def _is_command_safe(self, command: str) -> tuple[bool, str]:
        """
        Check if a command is safe to execute.

        Args:
            command: Command to check

        Returns:
            Tuple of (is_safe, reason)
        """
        # Check exact matches
        if command.strip() in self.BLOCKED_COMMANDS:
            return False, "Command is explicitly blocked"

        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command:
                return False, f"Command contains dangerous pattern: {pattern}"

        return True, ""

    def _truncate_output(self, output: str) -> str:
        """Truncate output if it exceeds maximum size."""
        if len(output) > self.max_output_size:
            truncated = output[: self.max_output_size]
            return truncated + f"\n... (truncated, {len(output)} total bytes)"
        return output

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
        shell: bool = True,
    ) -> CommandResult:
        """
        Execute a command and wait for completion.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout in seconds
            shell: Whether to run in shell

        Returns:
            CommandResult with execution details
        """
        # Security check
        is_safe, reason = self._is_command_safe(command)
        if not is_safe:
            logger.warning(f"Blocked unsafe command: {command}")
            return CommandResult(
                command=command,
                status=CommandStatus.FAILED,
                stderr=f"Command blocked: {reason}",
            )

        # Resolve working directory
        work_dir = Path(cwd) if cwd else self.workspace_path
        if not work_dir.is_absolute():
            work_dir = self.workspace_path / work_dir

        if not work_dir.exists():
            return CommandResult(
                command=command,
                status=CommandStatus.FAILED,
                stderr=f"Working directory not found: {work_dir}",
            )

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        timeout = timeout or self.default_timeout
        started_at = datetime.now()

        try:
            logger.info(f"Executing: {command[:50]}... in {work_dir}")

            # Create process
            if shell:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(work_dir),
                    env=process_env,
                )
            else:
                args = shlex.split(command)
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(work_dir),
                    env=process_env,
                )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                finished_at = datetime.now()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)

                stdout_str = self._truncate_output(stdout.decode("utf-8", errors="replace"))
                stderr_str = self._truncate_output(stderr.decode("utf-8", errors="replace"))

                status = (
                    CommandStatus.COMPLETED
                    if process.returncode == 0
                    else CommandStatus.FAILED
                )

                result = CommandResult(
                    command=command,
                    status=status,
                    exit_code=process.returncode,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    duration_ms=duration_ms,
                    started_at=started_at,
                    finished_at=finished_at,
                )

            except asyncio.TimeoutError:
                # Kill the process
                process.kill()
                await process.wait()

                result = CommandResult(
                    command=command,
                    status=CommandStatus.TIMEOUT,
                    stderr=f"Command timed out after {timeout} seconds",
                    started_at=started_at,
                    finished_at=datetime.now(),
                )

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            result = CommandResult(
                command=command,
                status=CommandStatus.FAILED,
                stderr=str(e),
                started_at=started_at,
                finished_at=datetime.now(),
            )

        # Record in history
        self._command_history.append(result)
        logger.info(f"Command completed: {result.status.value}, exit={result.exit_code}")

        return result

    async def execute_streaming(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Execute a command with streaming output.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout in seconds

        Yields:
            Output lines as they become available
        """
        # Security check
        is_safe, reason = self._is_command_safe(command)
        if not is_safe:
            yield f"❌ Command blocked: {reason}"
            return

        # Resolve working directory
        work_dir = Path(cwd) if cwd else self.workspace_path
        if not work_dir.is_absolute():
            work_dir = self.workspace_path / work_dir

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        timeout = timeout or self.default_timeout
        cmd_id = self._get_next_id()

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(work_dir),
                env=process_env,
            )

            # Track running command
            running = RunningCommand(
                id=cmd_id,
                command=command,
                process=process,
                started_at=datetime.now(),
                cwd=str(work_dir),
            )
            self._running_commands[cmd_id] = running

            yield f"🚀 Started: {command[:50]}...\n"

            # Stream output
            total_output = 0
            start_time = asyncio.get_event_loop().time()

            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    process.kill()
                    yield f"\n⏱️ Command timed out after {timeout}s"
                    break

                # Read output
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    # Check if process is still running
                    if process.returncode is not None:
                        break
                    continue

                if not line:
                    break

                decoded = line.decode("utf-8", errors="replace")
                total_output += len(decoded)

                if total_output > self.max_output_size:
                    yield "\n... (output truncated)"
                    break

                yield decoded

            # Wait for process to complete
            await process.wait()

            duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
            yield f"\n✅ Completed (exit={process.returncode}, {duration}ms)"

        except Exception as e:
            yield f"\n❌ Error: {str(e)}"

        finally:
            # Remove from running commands
            self._running_commands.pop(cmd_id, None)

    async def start_background(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        output_callback: Optional[Callable] = None,
    ) -> str:
        """
        Start a background command.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            output_callback: Callback for output lines

        Returns:
            Command ID for tracking
        """
        # Security check
        is_safe, reason = self._is_command_safe(command)
        if not is_safe:
            raise ValueError(f"Command blocked: {reason}")

        # Resolve working directory
        work_dir = Path(cwd) if cwd else self.workspace_path
        if not work_dir.is_absolute():
            work_dir = self.workspace_path / work_dir

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(work_dir),
            env=process_env,
        )

        cmd_id = self._get_next_id()

        running = RunningCommand(
            id=cmd_id,
            command=command,
            process=process,
            started_at=datetime.now(),
            cwd=str(work_dir),
            output_callback=output_callback,
        )
        self._running_commands[cmd_id] = running

        # Start output reader task
        asyncio.create_task(self._read_background_output(cmd_id))

        logger.info(f"Started background command {cmd_id}: {command[:50]}...")
        return cmd_id

    async def _read_background_output(self, cmd_id: str) -> None:
        """Read output from background command."""
        running = self._running_commands.get(cmd_id)
        if not running:
            return

        try:
            while True:
                line = await running.process.stdout.readline()
                if not line:
                    break

                decoded = line.decode("utf-8", errors="replace")

                if running.output_callback:
                    try:
                        await running.output_callback(cmd_id, decoded)
                    except Exception as e:
                        logger.error(f"Output callback error: {e}")

        except Exception as e:
            logger.error(f"Background read error: {e}")

        finally:
            self._running_commands.pop(cmd_id, None)

    async def cancel_command(self, cmd_id: str) -> bool:
        """
        Cancel a running command.

        Args:
            cmd_id: Command ID to cancel

        Returns:
            True if cancelled successfully
        """
        running = self._running_commands.get(cmd_id)
        if not running:
            return False

        try:
            running.process.terminate()
            try:
                await asyncio.wait_for(running.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                running.process.kill()

            self._running_commands.pop(cmd_id, None)
            logger.info(f"Cancelled command: {cmd_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel command: {e}")
            return False

    def list_running(self) -> list[dict]:
        """List currently running commands."""
        return [
            {
                "id": r.id,
                "command": r.command[:50] + "..." if len(r.command) > 50 else r.command,
                "cwd": r.cwd,
                "started_at": r.started_at.isoformat(),
                "duration_s": int((datetime.now() - r.started_at).total_seconds()),
            }
            for r in self._running_commands.values()
        ]

    def get_history(self, limit: int = 20) -> list[dict]:
        """Get command execution history."""
        return [r.to_dict() for r in self._command_history[-limit:]]

    async def cancel_all(self) -> int:
        """Cancel all running commands."""
        cancelled = 0
        for cmd_id in list(self._running_commands.keys()):
            if await self.cancel_command(cmd_id):
                cancelled += 1
        return cancelled


__all__ = ["TerminalManager", "CommandResult", "CommandStatus", "RunningCommand"]
