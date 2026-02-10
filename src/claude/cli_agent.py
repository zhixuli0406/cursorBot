"""
Claude Code CLI Agent Integration

Uses the official Claude Code CLI for AI operations.
More stable and direct interaction with Claude AI.

Requires:
- Claude Code CLI installed: pip install claude-code or via npm
- Claude API key from Anthropic Console (console.anthropic.com)

Note: This module is designed to integrate with the Claude Code CLI tool.
For full API documentation, see: https://docs.anthropic.com/claude-code
"""

import asyncio
import os
import re
import shutil
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

from ..utils.logger import logger
from ..utils.config import settings


class CLIStatus(Enum):
    """Claude Code CLI status."""
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    ERROR = "error"


@dataclass
class CLIConfig:
    """Claude Code CLI configuration."""
    # CLI binary path (auto-detected if not set)
    cli_path: str = "claude"  # Default command name

    # Working directory for CLI operations
    working_directory: str = ""

    # Default model to use (claude-opus-4.6, claude-sonnet-4.5, claude-haiku-4.5)
    model: str = ""  # Empty = use default (claude-sonnet-4.5)

    # Timeout for CLI operations (seconds), None = no timeout
    timeout: int | None = None

    # Auto-approve file changes (use with caution)
    auto_approve: bool = False

    # Capture full output
    capture_output: bool = True


@dataclass
class CLIResult:
    """Result from Claude Code CLI execution."""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0
    files_modified: list[str] = field(default_factory=list)


class ClaudeCodeCLIAgent:
    """
    Claude Code CLI Agent - Uses official `claude` command.

    Features:
    - Direct CLI interaction
    - Non-interactive mode for automation
    - File operation tracking
    - Timeout handling
    - Chat session context
    - Model selection support

    Commands supported:
    - claude chat "message" - Send a chat message
    - claude code file.py "instructions" - Edit code
    - claude --version - Check version
    """

    def __init__(self, config: CLIConfig = None):
        self.config = config or CLIConfig()
        self._cli_path = self._find_cli()
        self._status = CLIStatus.AVAILABLE if self._cli_path else CLIStatus.NOT_INSTALLED
        # Track chat sessions per user for context memory
        # Key: user_id (str), Value: chat_id (str)
        self._user_chat_sessions: dict[str, str] = {}
        # Track model selection per user
        # Key: user_id (str), Value: model_id (str)
        self._user_models: dict[str, str] = {}
        # Cache available models
        self._available_models: list[dict] = []
        self._models_fetched: bool = False

    def _find_cli(self) -> str:
        """Find the Claude Code CLI binary."""
        # Check configured path first
        if self.config.cli_path and os.path.exists(self.config.cli_path):
            return self.config.cli_path

        # Check common locations
        possible_paths = [
            "claude",  # In PATH (most common)
            "/usr/local/bin/claude",
            os.path.expanduser("~/.local/bin/claude"),
            os.path.expanduser("~/bin/claude"),
            # npm global install locations
            os.path.expanduser("~/.npm-global/bin/claude"),
            "/opt/homebrew/bin/claude",  # macOS Homebrew (ARM)
            "/usr/local/bin/claude",  # macOS Homebrew (Intel)
        ]

        for path in possible_paths:
            resolved = shutil.which(path)
            if resolved:
                return resolved
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        return ""

    @property
    def is_available(self) -> bool:
        """Check if Claude Code CLI is available."""
        return self._status == CLIStatus.AVAILABLE

    @property
    def status(self) -> CLIStatus:
        """Get current status."""
        return self._status

    async def check_installation(self) -> dict:
        """Check CLI installation status."""
        if not self._cli_path:
            return {
                "installed": False,
                "path": None,
                "message": "Claude Code CLI not found. Install with: pip install claude-code",
            }

        # Try to get version
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            version = stdout.decode().strip() or "unknown"

            return {
                "installed": True,
                "path": self._cli_path,
                "version": version,
                "message": "Claude Code CLI is ready",
            }
        except Exception as e:
            return {
                "installed": True,
                "path": self._cli_path,
                "version": "unknown",
                "message": f"CLI found but version check failed: {e}",
            }

    # ============================================
    # Core CLI Operations
    # ============================================

    async def run(self, *args: str) -> CLIResult:
        """
        Run Claude Code CLI command with given arguments.

        Args:
            *args: Command arguments

        Returns:
            CLIResult with execution details
        """
        if not self.is_available:
            return CLIResult(
                success=False,
                error="Claude Code CLI is not installed",
                exit_code=-1,
            )

        start_time = datetime.now()

        # Build command
        cmd = [self._cli_path] + list(args)

        # Set environment
        env = os.environ.copy()
        if settings.claude_api_key:
            env["ANTHROPIC_API_KEY"] = settings.claude_api_key

        if self.config.working_directory:
            cwd = self.config.working_directory
        else:
            cwd = settings.claude_working_dir or os.getcwd()

        try:
            # Execute command
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            # Wait for completion with timeout
            timeout = self.config.timeout
            if timeout == 0 or str(timeout).lower() in ("none", "disabled"):
                timeout = None

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                duration = (datetime.now() - start_time).total_seconds()
                return CLIResult(
                    success=False,
                    error=f"Command timed out after {timeout}s",
                    exit_code=-1,
                    duration=duration,
                )

            duration = (datetime.now() - start_time).total_seconds()

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            success = proc.returncode == 0

            if success:
                logger.debug(f"CLI command succeeded in {duration:.2f}s")
            else:
                logger.warning(f"CLI command failed with code {proc.returncode}")

            return CLIResult(
                success=success,
                output=stdout_str,
                error=stderr_str,
                exit_code=proc.returncode,
                duration=duration,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"CLI execution error: {e}")
            return CLIResult(
                success=False,
                error=str(e),
                exit_code=-1,
                duration=duration,
            )

    # ============================================
    # Chat Operations
    # ============================================

    async def chat(self, message: str, user_id: str = None) -> CLIResult:
        """
        Send a chat message to Claude.

        Args:
            message: The message to send
            user_id: Optional user ID for session management

        Returns:
            CLIResult with Claude's response
        """
        if not self.is_available:
            return CLIResult(
                success=False,
                error="Claude Code CLI is not installed",
                exit_code=-1,
            )

        # Build command
        args = ["chat", message]

        # Add model if specified
        model = self.get_user_model(user_id) if user_id else self.config.model
        if model:
            args = ["chat", "--model", model, message]

        result = await self.run(*args)
        return result

    async def ask(self, question: str) -> CLIResult:
        """
        Ask a quick question (non-interactive).

        Args:
            question: The question to ask

        Returns:
            CLIResult with answer
        """
        # For Claude Code CLI, "ask" is similar to "chat"
        # but we can add flags for non-interactive mode
        result = await self.run("chat", "--no-stream", question)
        return result

    async def edit(self, file_path: str, instructions: str) -> CLIResult:
        """
        Edit a file with given instructions.

        Args:
            file_path: Path to the file to edit
            instructions: Instructions for editing

        Returns:
            CLIResult with edit details
        """
        result = await self.run("code", file_path, instructions)

        # Track modified files
        if result.success and os.path.exists(file_path):
            result.files_modified = [file_path]

        return result

    async def generate(self, prompt: str, file_path: str = None) -> CLIResult:
        """
        Generate code or content from a prompt.

        Args:
            prompt: The generation prompt
            file_path: Optional file path to save to

        Returns:
            CLIResult with generated content
        """
        if file_path:
            result = await self.run("code", file_path, prompt)
            if result.success:
                result.files_modified = [file_path]
        else:
            result = await self.chat(prompt)

        return result

    # ============================================
    # Model Management
    # ============================================

    async def list_models(self) -> list[dict]:
        """
        List available Claude models.

        Returns:
            List of model dictionaries with id, name, and description
        """
        if self._models_fetched and self._available_models:
            return self._available_models

        # Claude models as of 2026-02
        models = [
            {
                "id": "claude-opus-4.6",
                "name": "Claude 4.6 Opus",
                "description": "Most capable model, best for complex tasks",
                "context_window": 200000,
            },
            {
                "id": "claude-sonnet-4.5",
                "name": "Claude 4.5 Sonnet",
                "description": "Balanced model, great for most tasks (default)",
                "context_window": 200000,
            },
            {
                "id": "claude-haiku-4.5",
                "name": "Claude 4.5 Haiku",
                "description": "Fastest model, good for simple tasks",
                "context_window": 200000,
            },
        ]

        self._available_models = models
        self._models_fetched = True
        return models

    def get_user_model(self, user_id: str) -> str:
        """
        Get user's selected model.

        Args:
            user_id: User identifier

        Returns:
            Model ID string
        """
        return self._user_models.get(user_id, "claude-sonnet-4.5")

    def set_user_model(self, user_id: str, model_id: str) -> None:
        """
        Set user's model preference.

        Args:
            user_id: User identifier
            model_id: Model ID to use
        """
        self._user_models[user_id] = model_id
        logger.info(f"Set model for user {user_id}: {model_id}")

    # ============================================
    # Session Management
    # ============================================

    def get_user_chat_id(self, user_id: str) -> Optional[str]:
        """
        Get the current CLI chat session ID for a user.

        Args:
            user_id: User identifier

        Returns:
            Chat session ID or None
        """
        return self._user_chat_sessions.get(user_id)

    def set_user_chat_id(self, user_id: str, chat_id: str) -> None:
        """
        Set the CLI chat session ID for a user.

        Args:
            user_id: User identifier
            chat_id: Chat session ID
        """
        self._user_chat_sessions[user_id] = chat_id
        logger.info(f"Set chat session for user {user_id}: {chat_id}")

    def clear_user_chat(self, user_id: str) -> None:
        """
        Clear chat session for a user.

        Args:
            user_id: User identifier
        """
        if user_id in self._user_chat_sessions:
            del self._user_chat_sessions[user_id]
            logger.info(f"Cleared chat session for user {user_id}")


# ============================================
# Global Agent Instance
# ============================================

_global_cli_agent: Optional[ClaudeCodeCLIAgent] = None


def get_cli_agent() -> ClaudeCodeCLIAgent:
    """
    Get or create global CLI agent instance.

    Returns:
        Global ClaudeCodeCLIAgent instance
    """
    global _global_cli_agent
    if _global_cli_agent is None:
        _global_cli_agent = ClaudeCodeCLIAgent()
    return _global_cli_agent


def reset_cli_agent() -> None:
    """Reset the global CLI agent instance."""
    global _global_cli_agent
    _global_cli_agent = None
    logger.info("Reset global CLI agent")


def is_cli_available() -> bool:
    """
    Check if Claude Code CLI is available.

    Returns:
        True if CLI is installed and accessible
    """
    agent = get_cli_agent()
    return agent.is_available


def get_cli_working_directory() -> str:
    """
    Get the working directory for CLI operations.

    Returns:
        Working directory path
    """
    if settings.claude_working_dir:
        return settings.claude_working_dir
    if settings.claude_workspace_path:
        return settings.claude_workspace_path
    return os.getcwd()
