"""
Workspace Agent for CursorBot
Manages workspace navigation and local file operations
"""

import time
from pathlib import Path
from typing import Any, Optional

from ..utils.config import settings
from ..utils.logger import logger


class WorkspaceAgent:
    """
    Workspace management agent.
    Handles workspace navigation, file listing, and project switching.
    """

    def __init__(self):
        """Initialize the Workspace Agent."""
        root_path = settings.cursor_workspace_path
        if not root_path:
            root_path = str(Path.cwd())
            logger.warning(f"CURSOR_WORKSPACE_PATH not set, using: {root_path}")

        self.root_workspace = Path(root_path)
        self.workspace_path = self.root_workspace
        self._commands_executed = 0
        self._last_activity: Optional[float] = None

    async def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = time.time()
        self._commands_executed += 1

    # ============================================
    # File Operations
    # ============================================

    async def read_file(self, file_path: str) -> str:
        """
        Read file content from workspace.

        Args:
            file_path: Relative or absolute path to file

        Returns:
            File content as string
        """
        logger.info(f"Reading file: {file_path}")

        # Resolve path
        if not Path(file_path).is_absolute():
            full_path = self.workspace_path / file_path
        else:
            full_path = Path(file_path)

        try:
            if not full_path.exists():
                return f"❌ 檔案不存在: {file_path}"

            if not full_path.is_file():
                return f"❌ 不是有效檔案: {file_path}"

            content = full_path.read_text(encoding="utf-8")
            await self._update_activity()
            return content
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return f"❌ 讀取錯誤: {str(e)}"

    async def list_files(self, directory: str = ".") -> str:
        """
        List files in a directory.

        Args:
            directory: Directory path to list

        Returns:
            Formatted list of files
        """
        logger.info(f"Listing directory: {directory}")

        # Resolve path
        if not Path(directory).is_absolute():
            full_path = self.workspace_path / directory
        else:
            full_path = Path(directory)

        try:
            if not full_path.exists():
                return f"❌ 目錄不存在: {directory}"

            if not full_path.is_dir():
                return f"❌ 不是目錄: {directory}"

            items = []
            for item in sorted(full_path.iterdir()):
                if item.name.startswith("."):
                    continue  # Skip hidden files
                prefix = "📂" if item.is_dir() else "📄"
                items.append(f"{prefix} {item.name}")

            await self._update_activity()

            if not items:
                return "（目錄為空）"

            return "\n".join(items)
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            return f"❌ 錯誤: {str(e)}"

    async def search_code(self, query: str) -> str:
        """
        Search for code in workspace.

        Args:
            query: Search query string

        Returns:
            Formatted search results
        """
        import re

        logger.info(f"Searching code: {query}")

        results = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        try:
            for file_path in self.workspace_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".md"]:
                    continue
                if any(p in str(file_path) for p in ["node_modules", ".git", "__pycache__", "venv", ".venv"]):
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                    for i, line in enumerate(content.split("\n"), 1):
                        if pattern.search(line):
                            relative_path = file_path.relative_to(self.workspace_path)
                            results.append({
                                "file": str(relative_path),
                                "line": i,
                                "content": line.strip(),
                            })
                            if len(results) >= 20:
                                break
                except Exception:
                    continue

                if len(results) >= 20:
                    break

            if not results:
                return "🔍 未找到匹配結果"

            formatted = []
            for r in results[:10]:
                formatted.append(
                    f"📄 <code>{r['file']}:{r['line']}</code>\n"
                    f"   {r['content'][:80]}"
                )

            await self._update_activity()
            return "\n\n".join(formatted)

        except Exception as e:
            return f"❌ 搜尋錯誤: {str(e)}"

    async def list_projects(self) -> str:
        """
        List available projects in current workspace.

        Returns:
            Formatted project list
        """
        try:
            projects = []
            for item in sorted(self.workspace_path.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    projects.append(f"📁 {item.name}")

            if not projects:
                return "（無專案）"

            return "\n".join(projects)
        except Exception as e:
            return f"❌ 錯誤: {str(e)}"

    async def switch_project(self, project_name: str) -> str:
        """
        Switch to a different project within current workspace.

        Args:
            project_name: Name of the project to switch to

        Returns:
            Status message
        """
        project_path = self.workspace_path / project_name

        if not project_path.exists():
            return f"❌ 專案不存在: {project_name}"

        if not project_path.is_dir():
            return f"❌ 不是有效專案: {project_name}"

        # Update workspace path
        self.workspace_path = project_path
        await self._update_activity()

        return f"✅ 已切換到專案: {project_name}"

    # ============================================
    # Workspace Management
    # ============================================

    def get_root_workspace(self) -> Path:
        """Get the root workspace path from settings."""
        return self.root_workspace

    def get_current_workspace(self) -> str:
        """Get current workspace path as string."""
        return str(self.workspace_path)

    def get_current_workspace_name(self) -> str:
        """Get current workspace folder name."""
        return self.workspace_path.name

    async def list_workspaces(self) -> list[dict]:
        """
        List all available workspaces (folders) in root workspace.

        Returns:
            List of workspace info dictionaries
        """
        root = self.get_root_workspace()
        workspaces = []

        logger.info(f"Listing workspaces from: {root}")

        if not root.exists():
            logger.error(f"Root workspace path does not exist: {root}")
            return workspaces

        try:
            for item in sorted(root.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    # Quick check for project indicators
                    has_git = (item / ".git").exists()
                    has_package = (item / "package.json").exists()
                    has_requirements = (item / "requirements.txt").exists()

                    # Determine project type
                    project_type = "📁"
                    if has_git:
                        project_type = "📦"
                    if has_package:
                        project_type = "🟢"  # Node.js
                    if has_requirements:
                        project_type = "🐍"  # Python

                    # Quick file count - only count direct children
                    try:
                        file_count = sum(1 for f in item.iterdir() if f.is_file())
                    except PermissionError:
                        file_count = 0

                    workspaces.append({
                        "name": item.name,
                        "path": str(item),
                        "type": project_type,
                        "file_count": file_count,
                        "has_git": has_git,
                        "is_current": item == self.workspace_path,
                    })

            logger.info(f"Found {len(workspaces)} workspaces")

        except Exception as e:
            logger.error(f"Error listing workspaces: {e}")

        return workspaces

    async def list_workspaces_formatted(self) -> str:
        """
        List workspaces in formatted string.

        Returns:
            Formatted workspace list
        """
        workspaces = await self.list_workspaces()

        if not workspaces:
            return "（無可用的工作區）"

        lines = []
        for ws in workspaces:
            current_mark = " ✓" if ws["is_current"] else ""
            lines.append(
                f"{ws['type']} <b>{ws['name']}</b>{current_mark}\n"
                f"   📄 {ws['file_count']} 個檔案"
            )

        return "\n".join(lines)

    async def switch_workspace(self, workspace_name: str) -> str:
        """
        Switch to a different workspace from root workspace.

        Args:
            workspace_name: Name of the workspace folder

        Returns:
            Status message
        """
        root = self.get_root_workspace()
        new_workspace = root / workspace_name

        if not new_workspace.exists():
            return f"❌ 工作區不存在: {workspace_name}"

        if not new_workspace.is_dir():
            return f"❌ 不是有效的工作區: {workspace_name}"

        # Update workspace path
        old_workspace = self.workspace_path.name
        self.workspace_path = new_workspace
        await self._update_activity()

        logger.info(f"Switched workspace: {old_workspace} -> {workspace_name}")

        return (
            f"✅ 已切換工作區\n\n"
            f"📂 <b>{workspace_name}</b>\n"
            f"📍 {new_workspace}"
        )

    async def get_workspace_info(self) -> dict:
        """
        Get detailed info about current workspace.

        Returns:
            Workspace info dictionary
        """
        ws = self.workspace_path

        # Count files by type
        file_types = {}
        total_files = 0

        try:
            for f in ws.rglob("*"):
                if f.is_file() and not any(
                    p in str(f) for p in [".git", "node_modules", "__pycache__", "venv", ".venv"]
                ):
                    total_files += 1
                    ext = f.suffix.lower() or "(無副檔名)"
                    file_types[ext] = file_types.get(ext, 0) + 1

                    # Limit iteration for large directories
                    if total_files > 1000:
                        break
        except Exception:
            pass

        # Sort by count
        top_types = sorted(file_types.items(), key=lambda x: -x[1])[:5]

        return {
            "name": ws.name,
            "path": str(ws),
            "total_files": total_files,
            "top_file_types": top_types,
            "has_git": (ws / ".git").exists(),
            "has_package_json": (ws / "package.json").exists(),
            "has_requirements": (ws / "requirements.txt").exists(),
            "has_readme": (ws / "README.md").exists() or (ws / "readme.md").exists(),
        }


# Alias for backward compatibility
CursorAgent = WorkspaceAgent

__all__ = ["WorkspaceAgent", "CursorAgent"]
