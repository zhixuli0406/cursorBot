"""
Claude Code Utility Functions

Provides simplified utility functions for file operations and command execution.
These replace the more complex FileOperations and TerminalManager from the old cursor module.
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from ..utils.logger import logger


# ============================================
# File Operations
# ============================================

async def read_file(path: str | Path) -> str:
    """
    Read file contents asynchronously.

    Args:
        path: File path to read

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file can't be read
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    try:
        # Use asyncio to read file (for large files)
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, path.read_text, 'utf-8')
        logger.debug(f"Read file: {path} ({len(content)} bytes)")
        return content
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        raise


async def write_file(path: str | Path, content: str, backup: bool = True) -> None:
    """
    Write content to file asynchronously.

    Args:
        path: File path to write
        content: Content to write
        backup: Whether to create a backup of existing file

    Raises:
        PermissionError: If file can't be written
    """
    path = Path(path)

    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create backup if file exists
    if backup and path.exists():
        backup_path = path.with_suffix(path.suffix + '.backup')
        shutil.copy2(path, backup_path)
        logger.debug(f"Created backup: {backup_path}")

    try:
        # Use asyncio to write file
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: path.write_text(content, encoding='utf-8')
        )
        logger.debug(f"Wrote file: {path} ({len(content)} bytes)")
    except Exception as e:
        logger.error(f"Failed to write file {path}: {e}")
        raise


async def append_to_file(path: str | Path, content: str) -> None:
    """
    Append content to file asynchronously.

    Args:
        path: File path
        content: Content to append

    Raises:
        PermissionError: If file can't be written
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        existing = ""
        if path.exists():
            existing = await read_file(path)

        new_content = existing + content
        await write_file(path, new_content, backup=False)
        logger.debug(f"Appended to file: {path}")
    except Exception as e:
        logger.error(f"Failed to append to file {path}: {e}")
        raise


async def delete_file(path: str | Path, backup: bool = True) -> None:
    """
    Delete a file.

    Args:
        path: File path to delete
        backup: Whether to create a backup before deleting

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if backup:
        backup_path = path.with_suffix(path.suffix + '.deleted')
        shutil.move(str(path), str(backup_path))
        logger.debug(f"Moved file to: {backup_path}")
    else:
        path.unlink()
        logger.debug(f"Deleted file: {path}")


async def copy_file(src: str | Path, dst: str | Path) -> None:
    """
    Copy a file.

    Args:
        src: Source file path
        dst: Destination file path
    """
    src, dst = Path(src), Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, shutil.copy2, str(src), str(dst))
    logger.debug(f"Copied file: {src} -> {dst}")


async def move_file(src: str | Path, dst: str | Path) -> None:
    """
    Move a file.

    Args:
        src: Source file path
        dst: Destination file path
    """
    src, dst = Path(src), Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, shutil.move, str(src), str(dst))
    logger.debug(f"Moved file: {src} -> {dst}")


# ============================================
# Directory Operations
# ============================================

async def create_directory(path: str | Path) -> None:
    """
    Create a directory (with parents).

    Args:
        path: Directory path to create
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Created directory: {path}")


async def list_files(
    directory: str | Path,
    pattern: str = "*",
    recursive: bool = False
) -> list[Path]:
    """
    List files in a directory.

    Args:
        directory: Directory to list
        pattern: Glob pattern (default: "*")
        recursive: Whether to search recursively

    Returns:
        List of file paths
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    if recursive:
        files = list(directory.rglob(pattern))
    else:
        files = list(directory.glob(pattern))

    # Filter out directories, only return files
    files = [f for f in files if f.is_file()]

    logger.debug(f"Listed {len(files)} files in {directory}")
    return files


# ============================================
# Command Execution
# ============================================

async def run_command(
    command: str,
    cwd: Optional[str | Path] = None,
    timeout: Optional[int] = None,
    env: Optional[dict] = None
) -> Tuple[str, str, int]:
    """
    Run a shell command asynchronously.

    Args:
        command: Command to execute
        cwd: Working directory (default: current directory)
        timeout: Timeout in seconds (default: no timeout)
        env: Environment variables (default: inherit from parent)

    Returns:
        Tuple of (stdout, stderr, exit_code)

    Raises:
        asyncio.TimeoutError: If command times out
    """
    if cwd:
        cwd = str(Path(cwd))

    if env is None:
        env = os.environ.copy()

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env
        )

        if timeout:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
        else:
            stdout, stderr = await proc.communicate()

        stdout_str = stdout.decode('utf-8', errors='replace')
        stderr_str = stderr.decode('utf-8', errors='replace')

        logger.debug(f"Command executed: {command[:50]}... (exit code: {proc.returncode})")

        return stdout_str, stderr_str, proc.returncode

    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.error(f"Command timed out: {command[:50]}...")
        raise
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        raise


async def run_command_with_output(
    command: str,
    cwd: Optional[str | Path] = None
) -> str:
    """
    Run a command and return its output (stdout + stderr combined).

    Args:
        command: Command to execute
        cwd: Working directory

    Returns:
        Combined output string

    Raises:
        RuntimeError: If command fails
    """
    stdout, stderr, exit_code = await run_command(command, cwd)

    if exit_code != 0:
        raise RuntimeError(
            f"Command failed with exit code {exit_code}:\n"
            f"Command: {command}\n"
            f"Stdout: {stdout}\n"
            f"Stderr: {stderr}"
        )

    # Combine stdout and stderr
    output = stdout
    if stderr:
        output += "\n" + stderr

    return output.strip()


# ============================================
# Path Utilities
# ============================================

def resolve_path(path: str | Path, base_dir: Optional[str | Path] = None) -> Path:
    """
    Resolve a path (handle relative paths, ~, etc.).

    Args:
        path: Path to resolve
        base_dir: Base directory for relative paths (default: current directory)

    Returns:
        Resolved absolute path
    """
    path = Path(path).expanduser()

    if not path.is_absolute():
        if base_dir:
            path = Path(base_dir) / path
        else:
            path = Path.cwd() / path

    return path.resolve()


def get_file_size(path: str | Path) -> int:
    """
    Get file size in bytes.

    Args:
        path: File path

    Returns:
        File size in bytes

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return path.stat().st_size


def get_file_modified_time(path: str | Path) -> datetime:
    """
    Get file's last modified time.

    Args:
        path: File path

    Returns:
        Modified time as datetime

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return datetime.fromtimestamp(path.stat().st_mtime)
