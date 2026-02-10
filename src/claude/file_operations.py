"""
File Operations for ClaudeBot

Simplified file operations wrapper.
This is a compatibility layer - for new code, use claude.utils functions directly.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import utils
from ..utils.logger import logger


@dataclass
class EditResult:
    """Result from edit operation."""
    success: bool
    message: str = ""
    files_modified: list[str] = None

    def __post_init__(self):
        if self.files_modified is None:
            self.files_modified = []


class FileOperations:
    """
    File operations manager.

    This is a compatibility wrapper around claude.utils functions.
    For new code, prefer using claude.utils directly.
    """

    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize file operations.

        Args:
            workspace_path: Workspace directory path
        """
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        logger.info(f"FileOperations initialized with workspace: {self.workspace_path}")

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve file path relative to workspace.

        Args:
            file_path: File path (relative or absolute)

        Returns:
            Resolved absolute path
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_path / path
        return path.resolve()

    async def read_file(self, file_path: str) -> str:
        """
        Read file contents.

        Args:
            file_path: File path to read

        Returns:
            File contents as string
        """
        resolved = self._resolve_path(file_path)
        return await utils.read_file(resolved)

    async def write_file(self, file_path: str, content: str, backup: bool = True) -> EditResult:
        """
        Write content to file.

        Args:
            file_path: File path to write
            content: Content to write
            backup: Whether to create backup

        Returns:
            EditResult with operation status
        """
        try:
            resolved = self._resolve_path(file_path)
            await utils.write_file(resolved, content, backup=backup)
            return EditResult(
                success=True,
                message=f"Successfully wrote to {file_path}",
                files_modified=[str(resolved)]
            )
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return EditResult(
                success=False,
                message=f"Failed to write file: {e}"
            )

    async def edit_file(
        self,
        file_path: str,
        old_text: str,
        new_text: str
    ) -> EditResult:
        """
        Edit file by replacing text.

        Args:
            file_path: File path to edit
            old_text: Text to find
            new_text: Text to replace with

        Returns:
            EditResult with operation status
        """
        try:
            resolved = self._resolve_path(file_path)
            content = await utils.read_file(resolved)

            if old_text not in content:
                return EditResult(
                    success=False,
                    message=f"Text not found in {file_path}"
                )

            new_content = content.replace(old_text, new_text)
            await utils.write_file(resolved, new_content, backup=True)

            return EditResult(
                success=True,
                message=f"Successfully edited {file_path}",
                files_modified=[str(resolved)]
            )
        except Exception as e:
            logger.error(f"Failed to edit file {file_path}: {e}")
            return EditResult(
                success=False,
                message=f"Failed to edit file: {e}"
            )

    async def insert_at_line(
        self,
        file_path: str,
        line_number: int,
        text: str
    ) -> EditResult:
        """
        Insert text at specific line number.

        Args:
            file_path: File path to edit
            line_number: Line number to insert at (1-indexed)
            text: Text to insert

        Returns:
            EditResult with operation status
        """
        try:
            resolved = self._resolve_path(file_path)
            content = await utils.read_file(resolved)
            lines = content.splitlines(keepends=True)

            if line_number < 1 or line_number > len(lines) + 1:
                return EditResult(
                    success=False,
                    message=f"Invalid line number: {line_number}"
                )

            # Insert at specified line (1-indexed)
            lines.insert(line_number - 1, text + "\n")
            new_content = "".join(lines)

            await utils.write_file(resolved, new_content, backup=True)

            return EditResult(
                success=True,
                message=f"Successfully inserted text at line {line_number}",
                files_modified=[str(resolved)]
            )
        except Exception as e:
            logger.error(f"Failed to insert at line in {file_path}: {e}")
            return EditResult(
                success=False,
                message=f"Failed to insert text: {e}"
            )

    async def delete_file(self, file_path: str, backup: bool = True) -> EditResult:
        """
        Delete a file.

        Args:
            file_path: File path to delete
            backup: Whether to create backup before deleting

        Returns:
            EditResult with operation status
        """
        try:
            resolved = self._resolve_path(file_path)
            await utils.delete_file(resolved, backup=backup)
            return EditResult(
                success=True,
                message=f"Successfully deleted {file_path}"
            )
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return EditResult(
                success=False,
                message=f"Failed to delete file: {e}"
            )

    async def copy_file(self, src: str, dst: str) -> EditResult:
        """
        Copy a file.

        Args:
            src: Source file path
            dst: Destination file path

        Returns:
            EditResult with operation status
        """
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            await utils.copy_file(src_path, dst_path)
            return EditResult(
                success=True,
                message=f"Successfully copied {src} to {dst}",
                files_modified=[str(dst_path)]
            )
        except Exception as e:
            logger.error(f"Failed to copy file {src} to {dst}: {e}")
            return EditResult(
                success=False,
                message=f"Failed to copy file: {e}"
            )

    async def move_file(self, src: str, dst: str) -> EditResult:
        """
        Move a file.

        Args:
            src: Source file path
            dst: Destination file path

        Returns:
            EditResult with operation status
        """
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            await utils.move_file(src_path, dst_path)
            return EditResult(
                success=True,
                message=f"Successfully moved {src} to {dst}",
                files_modified=[str(dst_path)]
            )
        except Exception as e:
            logger.error(f"Failed to move file {src} to {dst}: {e}")
            return EditResult(
                success=False,
                message=f"Failed to move file: {e}"
            )

    async def undo_last_change(self, file_path: str) -> EditResult:
        """
        Undo last change by restoring from backup.

        Args:
            file_path: File path to restore

        Returns:
            EditResult with operation status
        """
        try:
            resolved = self._resolve_path(file_path)
            backup_path = resolved.with_suffix(resolved.suffix + '.backup')

            if not backup_path.exists():
                return EditResult(
                    success=False,
                    message=f"No backup found for {file_path}"
                )

            await utils.copy_file(backup_path, resolved)
            return EditResult(
                success=True,
                message=f"Successfully restored {file_path} from backup",
                files_modified=[str(resolved)]
            )
        except Exception as e:
            logger.error(f"Failed to undo changes for {file_path}: {e}")
            return EditResult(
                success=False,
                message=f"Failed to undo changes: {e}"
            )


__all__ = ["FileOperations", "EditResult"]
