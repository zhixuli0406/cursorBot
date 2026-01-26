"""
File operations module for CursorBot
Provides file editing, creation, and management capabilities
"""

import difflib
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils.logger import logger


@dataclass
class FileChange:
    """Represents a file change operation."""

    path: str
    old_content: Optional[str]
    new_content: str
    operation: str  # 'create', 'update', 'delete'
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class EditResult:
    """Result of a file edit operation."""

    success: bool
    message: str
    diff: Optional[str] = None
    backup_path: Optional[str] = None


class FileOperations:
    """
    File operations handler.
    Provides safe file editing with backup and rollback support.
    """

    def __init__(self, workspace_path: str, backup_enabled: bool = True):
        """
        Initialize file operations.

        Args:
            workspace_path: Root workspace directory
            backup_enabled: Whether to create backups before editing
        """
        self.workspace_path = Path(workspace_path)
        self.backup_enabled = backup_enabled
        self.backup_dir = self.workspace_path / ".cursorbot_backups"
        self._history: list[FileChange] = []

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to workspace."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_path / path
        return path.resolve()

    def _ensure_backup_dir(self) -> None:
        """Ensure backup directory exists."""
        if self.backup_enabled:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _create_backup(self, file_path: Path) -> Optional[str]:
        """
        Create backup of a file.

        Args:
            file_path: Path to file to backup

        Returns:
            Backup file path or None
        """
        if not self.backup_enabled or not file_path.exists():
            return None

        self._ensure_backup_dir()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        relative_path = file_path.relative_to(self.workspace_path)
        backup_name = f"{relative_path.stem}_{timestamp}{relative_path.suffix}"
        backup_path = self.backup_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
            return None

    def _generate_diff(
        self,
        old_content: str,
        new_content: str,
        filename: str = "file",
    ) -> str:
        """
        Generate unified diff between old and new content.

        Args:
            old_content: Original content
            new_content: New content
            filename: Filename for diff header

        Returns:
            Unified diff string
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )

        return "".join(diff)

    def read_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """
        Read file content.

        Args:
            file_path: Path to file
            encoding: File encoding

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = self._resolve_path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        return path.read_text(encoding=encoding)

    def write_file(
        self,
        file_path: str,
        content: str,
        create_dirs: bool = True,
        encoding: str = "utf-8",
    ) -> EditResult:
        """
        Write content to file.

        Args:
            file_path: Path to file
            content: Content to write
            create_dirs: Create parent directories if needed
            encoding: File encoding

        Returns:
            EditResult with operation status
        """
        path = self._resolve_path(file_path)

        try:
            # Check if it's a new file or update
            is_new = not path.exists()
            old_content = None

            if not is_new:
                old_content = path.read_text(encoding=encoding)
                backup_path = self._create_backup(path)
            else:
                backup_path = None
                if create_dirs:
                    path.parent.mkdir(parents=True, exist_ok=True)

            # Write new content
            path.write_text(content, encoding=encoding)

            # Generate diff for updates
            diff = None
            if old_content is not None:
                diff = self._generate_diff(old_content, content, path.name)

            # Record change in history
            self._history.append(FileChange(
                path=str(path),
                old_content=old_content,
                new_content=content,
                operation="create" if is_new else "update",
            ))

            operation = "Created" if is_new else "Updated"
            logger.info(f"{operation} file: {file_path}")

            return EditResult(
                success=True,
                message=f"✅ {operation}: {file_path}",
                diff=diff,
                backup_path=backup_path,
            )

        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return EditResult(
                success=False,
                message=f"❌ Failed to write: {str(e)}",
            )

    def edit_file(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
        encoding: str = "utf-8",
    ) -> EditResult:
        """
        Edit file by replacing specific text.

        Args:
            file_path: Path to file
            old_text: Text to find and replace
            new_text: Replacement text
            encoding: File encoding

        Returns:
            EditResult with operation status
        """
        path = self._resolve_path(file_path)

        try:
            if not path.exists():
                return EditResult(
                    success=False,
                    message=f"❌ File not found: {file_path}",
                )

            content = path.read_text(encoding=encoding)

            if old_text not in content:
                return EditResult(
                    success=False,
                    message="❌ Text to replace not found in file",
                )

            # Create backup
            backup_path = self._create_backup(path)

            # Perform replacement
            new_content = content.replace(old_text, new_text, 1)

            # Write updated content
            path.write_text(new_content, encoding=encoding)

            # Generate diff
            diff = self._generate_diff(content, new_content, path.name)

            # Record change
            self._history.append(FileChange(
                path=str(path),
                old_content=content,
                new_content=new_content,
                operation="update",
            ))

            logger.info(f"Edited file: {file_path}")

            return EditResult(
                success=True,
                message=f"✅ Edited: {file_path}",
                diff=diff,
                backup_path=backup_path,
            )

        except Exception as e:
            logger.error(f"Failed to edit file: {e}")
            return EditResult(
                success=False,
                message=f"❌ Edit failed: {str(e)}",
            )

    def insert_at_line(
        self,
        file_path: str,
        line_number: int,
        text: str,
        encoding: str = "utf-8",
    ) -> EditResult:
        """
        Insert text at a specific line number.

        Args:
            file_path: Path to file
            line_number: Line number to insert at (1-based)
            text: Text to insert
            encoding: File encoding

        Returns:
            EditResult with operation status
        """
        path = self._resolve_path(file_path)

        try:
            if not path.exists():
                return EditResult(
                    success=False,
                    message=f"❌ File not found: {file_path}",
                )

            content = path.read_text(encoding=encoding)
            lines = content.split("\n")

            if line_number < 1 or line_number > len(lines) + 1:
                return EditResult(
                    success=False,
                    message=f"❌ Invalid line number: {line_number}",
                )

            # Create backup
            backup_path = self._create_backup(path)

            # Insert text
            lines.insert(line_number - 1, text)
            new_content = "\n".join(lines)

            # Write updated content
            path.write_text(new_content, encoding=encoding)

            # Generate diff
            diff = self._generate_diff(content, new_content, path.name)

            # Record change
            self._history.append(FileChange(
                path=str(path),
                old_content=content,
                new_content=new_content,
                operation="update",
            ))

            logger.info(f"Inserted at line {line_number}: {file_path}")

            return EditResult(
                success=True,
                message=f"✅ Inserted at line {line_number}: {file_path}",
                diff=diff,
                backup_path=backup_path,
            )

        except Exception as e:
            logger.error(f"Failed to insert at line: {e}")
            return EditResult(
                success=False,
                message=f"❌ Insert failed: {str(e)}",
            )

    def delete_file(self, file_path: str) -> EditResult:
        """
        Delete a file.

        Args:
            file_path: Path to file

        Returns:
            EditResult with operation status
        """
        path = self._resolve_path(file_path)

        try:
            if not path.exists():
                return EditResult(
                    success=False,
                    message=f"❌ File not found: {file_path}",
                )

            # Create backup before deletion
            backup_path = self._create_backup(path)
            old_content = path.read_text() if path.is_file() else None

            # Delete file
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)

            # Record change
            self._history.append(FileChange(
                path=str(path),
                old_content=old_content,
                new_content="",
                operation="delete",
            ))

            logger.info(f"Deleted: {file_path}")

            return EditResult(
                success=True,
                message=f"✅ Deleted: {file_path}",
                backup_path=backup_path,
            )

        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return EditResult(
                success=False,
                message=f"❌ Delete failed: {str(e)}",
            )

    def create_directory(self, dir_path: str) -> EditResult:
        """
        Create a directory.

        Args:
            dir_path: Path to directory

        Returns:
            EditResult with operation status
        """
        path = self._resolve_path(dir_path)

        try:
            path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Created directory: {dir_path}")

            return EditResult(
                success=True,
                message=f"✅ Created directory: {dir_path}",
            )

        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            return EditResult(
                success=False,
                message=f"❌ Failed: {str(e)}",
            )

    def move_file(self, src_path: str, dest_path: str) -> EditResult:
        """
        Move or rename a file.

        Args:
            src_path: Source path
            dest_path: Destination path

        Returns:
            EditResult with operation status
        """
        src = self._resolve_path(src_path)
        dest = self._resolve_path(dest_path)

        try:
            if not src.exists():
                return EditResult(
                    success=False,
                    message=f"❌ Source not found: {src_path}",
                )

            # Create parent directories for destination
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(src), str(dest))

            logger.info(f"Moved: {src_path} -> {dest_path}")

            return EditResult(
                success=True,
                message=f"✅ Moved: {src_path} -> {dest_path}",
            )

        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return EditResult(
                success=False,
                message=f"❌ Move failed: {str(e)}",
            )

    def copy_file(self, src_path: str, dest_path: str) -> EditResult:
        """
        Copy a file.

        Args:
            src_path: Source path
            dest_path: Destination path

        Returns:
            EditResult with operation status
        """
        src = self._resolve_path(src_path)
        dest = self._resolve_path(dest_path)

        try:
            if not src.exists():
                return EditResult(
                    success=False,
                    message=f"❌ Source not found: {src_path}",
                )

            # Create parent directories
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy
            if src.is_file():
                shutil.copy2(str(src), str(dest))
            else:
                shutil.copytree(str(src), str(dest))

            logger.info(f"Copied: {src_path} -> {dest_path}")

            return EditResult(
                success=True,
                message=f"✅ Copied: {src_path} -> {dest_path}",
            )

        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return EditResult(
                success=False,
                message=f"❌ Copy failed: {str(e)}",
            )

    def undo_last_change(self) -> EditResult:
        """
        Undo the last file change.

        Returns:
            EditResult with operation status
        """
        if not self._history:
            return EditResult(
                success=False,
                message="❌ No changes to undo",
            )

        change = self._history.pop()
        path = Path(change.path)

        try:
            if change.operation == "delete":
                # Restore deleted file
                if change.old_content is not None:
                    path.write_text(change.old_content)
                    message = f"✅ Restored: {change.path}"
                else:
                    message = "❌ Cannot restore: no backup content"
                    return EditResult(success=False, message=message)

            elif change.operation == "create":
                # Delete created file
                if path.exists():
                    path.unlink()
                message = f"✅ Removed created file: {change.path}"

            elif change.operation == "update":
                # Restore original content
                if change.old_content is not None:
                    path.write_text(change.old_content)
                    message = f"✅ Reverted: {change.path}"
                else:
                    message = "❌ Cannot revert: no original content"
                    return EditResult(success=False, message=message)

            else:
                message = f"❌ Unknown operation: {change.operation}"
                return EditResult(success=False, message=message)

            logger.info(f"Undo: {change.operation} on {change.path}")
            return EditResult(success=True, message=message)

        except Exception as e:
            logger.error(f"Failed to undo: {e}")
            return EditResult(
                success=False,
                message=f"❌ Undo failed: {str(e)}",
            )

    def get_history(self, limit: int = 10) -> list[dict]:
        """
        Get recent change history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of change records
        """
        return [
            {
                "path": c.path,
                "operation": c.operation,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in self._history[-limit:]
        ]


__all__ = ["FileOperations", "FileChange", "EditResult"]
