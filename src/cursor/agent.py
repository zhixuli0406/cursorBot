"""
Cursor Agent interface
Manages communication and command execution with Cursor IDE
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Optional

from ..utils.config import settings
from ..utils.logger import logger
from .mcp_client import MCPClient, MockMCPClient


class CursorAgent:
    """
    Main interface for communicating with Cursor Agent.
    Handles all operations including code generation, file management,
    and AI conversation.
    """

    def __init__(self, use_mock: bool = False):
        """
        Initialize the Cursor Agent interface.

        Args:
            use_mock: If True, use MockMCPClient for testing without real Cursor connection
        """
        self.workspace_path = Path(settings.cursor_workspace_path)
        self.use_mock = use_mock or settings.debug

        if self.use_mock:
            logger.info("Using MockMCPClient (debug/test mode)")
            self.mcp_client = MockMCPClient(
                host="localhost",
                port=settings.cursor_mcp_port,
            )
        else:
            self.mcp_client = MCPClient(
                host="localhost",
                port=settings.cursor_mcp_port,
            )

        self._connected = False
        self._commands_executed = 0
        self._last_activity: Optional[float] = None

    async def connect(self) -> bool:
        """
        Establish connection to Cursor Agent.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._connected = await self.mcp_client.connect()
            if self._connected:
                logger.info("Connected to Cursor Agent")
                self._last_activity = time.time()
            return self._connected
        except Exception as e:
            logger.error(f"Failed to connect to Cursor Agent: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Cursor Agent."""
        await self.mcp_client.disconnect()
        self._connected = False
        logger.info("Disconnected from Cursor Agent")

    async def get_status(self) -> dict[str, Any]:
        """
        Get current status of Cursor Agent connection.

        Returns:
            Dictionary containing status information
        """
        latency = None
        if self._connected:
            start = time.time()
            try:
                await self.mcp_client.ping()
                latency = int((time.time() - start) * 1000)
            except Exception:
                self._connected = False

        last_activity_str = "N/A"
        if self._last_activity:
            elapsed = int(time.time() - self._last_activity)
            if elapsed < 60:
                last_activity_str = f"{elapsed} 秒前"
            elif elapsed < 3600:
                last_activity_str = f"{elapsed // 60} 分鐘前"
            else:
                last_activity_str = f"{elapsed // 3600} 小時前"

        return {
            "connected": self._connected,
            "workspace": str(self.workspace_path),
            "latency": latency,
            "commands_executed": self._commands_executed,
            "last_activity": last_activity_str,
        }

    async def _ensure_connected(self) -> bool:
        """Ensure connection is established before operations."""
        if not self._connected:
            return await self.connect()
        return True

    async def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = time.time()
        self._commands_executed += 1

    async def ask(self, question: str) -> str:
        """
        Ask a question to Cursor Agent.

        Args:
            question: The question to ask

        Returns:
            Agent's response as string
        """
        logger.info(f"Asking Cursor Agent: {question[:50]}...")

        if not await self._ensure_connected():
            return "❌ 無法連接到 Cursor Agent,請確認 Cursor IDE 正在運行"

        try:
            response = await self.mcp_client.send_message({
                "type": "ask",
                "content": question,
            })
            await self._update_activity()
            return response.get("content", "No response received")
        except Exception as e:
            logger.error(f"Error asking Cursor Agent: {e}")
            return f"❌ 錯誤: {str(e)}"

    async def chat(self, message: str) -> str:
        """
        Send a chat message to Cursor Agent.

        Args:
            message: The message to send

        Returns:
            Agent's response
        """
        logger.info(f"Chat with Cursor Agent: {message[:50]}...")

        if not await self._ensure_connected():
            return "❌ 無法連接到 Cursor Agent"

        try:
            response = await self.mcp_client.send_message({
                "type": "chat",
                "content": message,
            })
            await self._update_activity()
            return response.get("content", "No response received")
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"❌ 錯誤: {str(e)}"

    async def execute_code_instruction(self, instruction: str) -> str:
        """
        Execute a code-related instruction.

        Args:
            instruction: The code instruction to execute

        Returns:
            Execution result
        """
        logger.info(f"Executing code instruction: {instruction[:50]}...")

        if not await self._ensure_connected():
            return "❌ 無法連接到 Cursor Agent"

        try:
            response = await self.mcp_client.send_message({
                "type": "code",
                "instruction": instruction,
            })
            await self._update_activity()
            return response.get("result", "No result")
        except Exception as e:
            logger.error(f"Error executing code instruction: {e}")
            return f"❌ 錯誤: {str(e)}"

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
        logger.info(f"Searching code: {query}")

        if not await self._ensure_connected():
            # Fallback to local search if not connected
            return await self._local_search(query)

        try:
            response = await self.mcp_client.send_message({
                "type": "search",
                "query": query,
            })
            await self._update_activity()

            results = response.get("results", [])
            if not results:
                return "🔍 未找到匹配結果"

            formatted = []
            for r in results[:10]:
                formatted.append(
                    f"📄 <code>{r['file']}:{r['line']}</code>\n"
                    f"   {r['content'][:80]}"
                )

            return "\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return f"❌ 搜尋錯誤: {str(e)}"

    async def _local_search(self, query: str) -> str:
        """
        Perform local file search when agent is not connected.

        Args:
            query: Search query

        Returns:
            Search results
        """
        import re

        results = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        try:
            for file_path in self.workspace_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"]:
                    continue
                if any(p in str(file_path) for p in ["node_modules", ".git", "__pycache__", "venv"]):
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
            return f"❌ 本地搜尋錯誤: {str(e)}"

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
        path = settings.cursor_workspace_path
        if not path:
            logger.warning("CURSOR_WORKSPACE_PATH is not set, using current directory")
            return Path.cwd()
        return Path(path)

    def get_current_workspace(self) -> str:
        """Get current workspace path as string."""
        return str(self.workspace_path)

    def get_current_workspace_name(self) -> str:
        """Get current workspace folder name."""
        return self.workspace_path.name

    async def list_workspaces(self) -> list[dict]:
        """
        List all available workspaces (folders) in CURSOR_WORKSPACE_PATH.

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
                    # Quick check for project indicators (don't count all files)
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

                    # Quick file count - only count direct children, not recursive
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
        Switch to a different workspace from CURSOR_WORKSPACE_PATH.

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


__all__ = ["CursorAgent"]
