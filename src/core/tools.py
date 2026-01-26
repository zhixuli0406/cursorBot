"""
Agent Tools for CursorBot
Inspired by Clawd Bot's tool system

Provides agent-callable tools:
- File operations (read, write, list)
- Command execution (sandboxed)
- Web operations (fetch, screenshot)
- GitHub operations
"""

import asyncio
import base64
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import httpx

from ..utils.logger import logger


class ToolCategory(Enum):
    FILESYSTEM = "fs"
    RUNTIME = "runtime"
    WEB = "web"
    GITHUB = "github"
    UTILITY = "utility"


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata or {},
        }


class Tool(ABC):
    """Base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        pass

    def to_schema(self) -> dict:
        """Get tool schema for AI function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
        }


# ============================================
# Filesystem Tools
# ============================================


class ReadFileTool(Tool):
    """Read file contents."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILESYSTEM

    async def execute(
        self,
        path: str,
        encoding: str = "utf-8",
        max_size: int = 1024 * 1024,  # 1MB
        **kwargs
    ) -> ToolResult:
        try:
            file_path = Path(path)

            if not file_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")

            if not file_path.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")

            # Check file size
            size = file_path.stat().st_size
            if size > max_size:
                return ToolResult(
                    success=False,
                    error=f"File too large: {size} bytes (max {max_size})"
                )

            content = file_path.read_text(encoding=encoding)

            return ToolResult(
                success=True,
                data=content,
                metadata={"path": str(path), "size": size}
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WriteFileTool(Tool):
    """Write content to a file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILESYSTEM

    async def execute(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
        **kwargs
    ) -> ToolResult:
        try:
            file_path = Path(path)

            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content, encoding=encoding)

            return ToolResult(
                success=True,
                data={"written": len(content)},
                metadata={"path": str(path)}
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ListDirectoryTool(Tool):
    """List directory contents."""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories in a path"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILESYSTEM

    async def execute(
        self,
        path: str = ".",
        recursive: bool = False,
        pattern: str = "*",
        **kwargs
    ) -> ToolResult:
        try:
            dir_path = Path(path)

            if not dir_path.exists():
                return ToolResult(success=False, error=f"Path not found: {path}")

            if not dir_path.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            if recursive:
                items = list(dir_path.rglob(pattern))
            else:
                items = list(dir_path.glob(pattern))

            files = []
            dirs = []

            for item in items[:1000]:  # Limit results
                rel_path = str(item.relative_to(dir_path))
                if item.is_file():
                    files.append({
                        "name": rel_path,
                        "size": item.stat().st_size,
                    })
                else:
                    dirs.append(rel_path)

            return ToolResult(
                success=True,
                data={"files": files, "directories": dirs},
                metadata={"path": str(path), "total": len(files) + len(dirs)}
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ============================================
# Runtime Tools
# ============================================


class ExecuteCommandTool(Tool):
    """Execute shell commands (sandboxed)."""

    # Allowed commands (whitelist)
    ALLOWED_COMMANDS = {
        "ls", "cat", "head", "tail", "grep", "find", "wc",
        "echo", "pwd", "date", "whoami",
        "git", "npm", "yarn", "pnpm", "pip", "python",
        "node", "deno", "bun",
    }

    # Blocked patterns
    BLOCKED_PATTERNS = [
        "rm -rf", "sudo", "chmod 777", "> /dev",
        "mkfs", "dd if=", ":(){", "fork",
    ]

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return "Execute a shell command (sandboxed)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.RUNTIME

    def _is_command_safe(self, command: str) -> tuple[bool, str]:
        """Check if command is safe to execute."""
        # Check blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in command:
                return False, f"Blocked pattern: {pattern}"

        # Check if base command is allowed
        base_cmd = command.split()[0] if command.split() else ""
        if base_cmd not in self.ALLOWED_COMMANDS:
            return False, f"Command not allowed: {base_cmd}"

        return True, ""

    async def execute(
        self,
        command: str,
        cwd: str = None,
        timeout: int = 30,
        **kwargs
    ) -> ToolResult:
        try:
            # Safety check
            is_safe, reason = self._is_command_safe(command)
            if not is_safe:
                return ToolResult(success=False, error=reason)

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(success=False, error="Command timed out")

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            return ToolResult(
                success=process.returncode == 0,
                data={
                    "stdout": stdout_text[:10000],  # Limit output
                    "stderr": stderr_text[:2000],
                    "return_code": process.returncode,
                },
                metadata={"command": command}
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ============================================
# Web Tools
# ============================================


class FetchURLTool(Tool):
    """Fetch content from a URL."""

    @property
    def name(self) -> str:
        return "fetch_url"

    @property
    def description(self) -> str:
        return "Fetch content from a URL"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WEB

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: dict = None,
        timeout: int = 30,
        **kwargs
    ) -> ToolResult:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=True,
                )

                # Determine content type
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    data = response.json()
                elif "text" in content_type:
                    data = response.text[:50000]  # Limit text
                else:
                    data = base64.b64encode(response.content[:100000]).decode()

                return ToolResult(
                    success=response.is_success,
                    data=data,
                    metadata={
                        "url": url,
                        "status_code": response.status_code,
                        "content_type": content_type,
                    }
                )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ============================================
# GitHub Tools
# ============================================


class GitHubTool(Tool):
    """GitHub operations."""

    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "")

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "Perform GitHub operations"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.GITHUB

    async def execute(
        self,
        action: str,
        repo: str = None,
        **kwargs
    ) -> ToolResult:
        """
        Execute GitHub action.

        Actions:
        - get_repo: Get repository info
        - list_issues: List issues
        - list_prs: List pull requests
        - get_file: Get file contents
        """
        try:
            if action == "get_repo":
                return await self._get_repo(repo)
            elif action == "list_issues":
                return await self._list_issues(repo, **kwargs)
            elif action == "list_prs":
                return await self._list_prs(repo, **kwargs)
            elif action == "get_file":
                return await self._get_file(repo, kwargs.get("path", ""))
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _make_request(self, endpoint: str) -> dict:
        """Make GitHub API request."""
        async with httpx.AsyncClient() as client:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            response = await client.get(
                f"https://api.github.com{endpoint}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def _get_repo(self, repo: str) -> ToolResult:
        """Get repository info."""
        data = await self._make_request(f"/repos/{repo}")
        return ToolResult(
            success=True,
            data={
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "language": data.get("language"),
                "default_branch": data.get("default_branch"),
            }
        )

    async def _list_issues(self, repo: str, state: str = "open", limit: int = 10) -> ToolResult:
        """List issues."""
        data = await self._make_request(f"/repos/{repo}/issues?state={state}&per_page={limit}")
        issues = [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "state": i.get("state"),
                "labels": [l.get("name") for l in i.get("labels", [])],
            }
            for i in data
        ]
        return ToolResult(success=True, data=issues)

    async def _list_prs(self, repo: str, state: str = "open", limit: int = 10) -> ToolResult:
        """List pull requests."""
        data = await self._make_request(f"/repos/{repo}/pulls?state={state}&per_page={limit}")
        prs = [
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "state": pr.get("state"),
                "draft": pr.get("draft"),
            }
            for pr in data
        ]
        return ToolResult(success=True, data=prs)

    async def _get_file(self, repo: str, path: str) -> ToolResult:
        """Get file contents."""
        data = await self._make_request(f"/repos/{repo}/contents/{path}")
        content = base64.b64decode(data.get("content", "")).decode("utf-8")
        return ToolResult(
            success=True,
            data=content,
            metadata={"path": path, "sha": data.get("sha")}
        )


# ============================================
# Tool Registry
# ============================================


class ToolRegistry:
    """Registry for all available tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory = None) -> list[Tool]:
        """List all tools, optionally by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_schemas(self) -> list[dict]:
        """Get all tool schemas for AI function calling."""
        return [t.to_schema() for t in self._tools.values()]

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {name}")

        return await tool.execute(**kwargs)


def create_default_registry() -> ToolRegistry:
    """Create a registry with default tools."""
    registry = ToolRegistry()

    # Filesystem tools
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListDirectoryTool())

    # Runtime tools
    registry.register(ExecuteCommandTool())

    # Web tools
    registry.register(FetchURLTool())

    # GitHub tools
    registry.register(GitHubTool())

    return registry


# Global instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global ToolRegistry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = create_default_registry()
    return _tool_registry


__all__ = [
    "Tool",
    "ToolResult",
    "ToolCategory",
    "ToolRegistry",
    "get_tool_registry",
    # Tools
    "ReadFileTool",
    "WriteFileTool",
    "ListDirectoryTool",
    "ExecuteCommandTool",
    "FetchURLTool",
    "GitHubTool",
]
