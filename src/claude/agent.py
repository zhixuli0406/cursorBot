"""
Workspace Agent for ClaudeBot

Simplified workspace management agent.
This is a compatibility wrapper - core functionality moved to claude.utils and cli_agent.
"""

import os
from pathlib import Path
from typing import Optional

from ..utils.config import settings
from ..utils.logger import logger


class WorkspaceAgent:
    """
    Workspace management agent.

    This is a simplified compatibility wrapper to maintain backward compatibility.
    For new code, prefer using claude.utils functions directly.
    """

    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize workspace agent.

        Args:
            workspace_path: Optional workspace path. If not provided, uses settings.
        """
        self._workspace_path = workspace_path or settings.claude_workspace_path or os.getcwd()
        logger.info(f"WorkspaceAgent initialized with workspace: {self._workspace_path}")

    def get_current_workspace(self) -> str:
        """
        Get current workspace path.

        Returns:
            Workspace path as string
        """
        return self._workspace_path

    def set_workspace(self, path: str) -> None:
        """
        Set workspace path.

        Args:
            path: New workspace path
        """
        self._workspace_path = str(Path(path).resolve())
        logger.info(f"Workspace changed to: {self._workspace_path}")

    @property
    def workspace_path(self) -> str:
        """Get workspace path."""
        return self._workspace_path


# Alias for backward compatibility
ClaudeAgent = WorkspaceAgent
CursorAgent = WorkspaceAgent  # Legacy name

__all__ = ["WorkspaceAgent", "ClaudeAgent", "CursorAgent"]
