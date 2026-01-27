"""
Cursor CLI Agent Integration

Uses the official Cursor CLI (`agent` command) instead of Background Agent API.
More stable and direct interaction with Cursor AI.

Requires:
- Cursor CLI installed: curl https://cursor.com/install -fsS | bash
- Cursor subscription for model access
"""

import asyncio
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

from ..utils.logger import logger
from ..utils.config import settings


class CLIStatus(Enum):
    """Cursor CLI status."""
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    ERROR = "error"


@dataclass
class CLIConfig:
    """Cursor CLI configuration."""
    # CLI binary path (auto-detected if not set)
    cli_path: str = ""
    
    # Working directory for CLI operations
    working_directory: str = ""
    
    # Default model to use
    model: str = ""  # Empty = use default
    
    # Timeout for CLI operations (seconds)
    timeout: int = 300
    
    # Auto-approve file changes (use with caution)
    auto_approve: bool = False
    
    # Capture full output
    capture_output: bool = True


@dataclass
class CLIResult:
    """Result from Cursor CLI execution."""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0
    files_modified: list[str] = field(default_factory=list)


class CursorCLIAgent:
    """
    Cursor CLI Agent - Uses official `agent` command.
    
    Features:
    - Direct CLI interaction
    - Non-interactive mode for automation
    - File operation tracking
    - Timeout handling
    - Chat session context (resume conversations)
    - Model selection support
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
        """Find the Cursor CLI binary."""
        # Check configured path first
        if self.config.cli_path and os.path.exists(self.config.cli_path):
            return self.config.cli_path
        
        # Check common locations
        possible_paths = [
            "agent",  # In PATH
            "/usr/local/bin/agent",
            os.path.expanduser("~/.cursor/bin/agent"),
            os.path.expanduser("~/bin/agent"),
            "cursor",  # Alternative command
            "/usr/local/bin/cursor",
            "/Applications/Cursor.app/Contents/MacOS/cursor",
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                return path
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        return ""
    
    @property
    def is_available(self) -> bool:
        """Check if Cursor CLI is available."""
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
                "message": "Cursor CLI not found. Install with: curl https://cursor.com/install -fsS | bash",
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
                "message": "Cursor CLI is ready",
            }
        except Exception as e:
            return {
                "installed": True,
                "path": self._cli_path,
                "version": "unknown",
                "message": f"CLI found but version check failed: {e}",
            }
    
    # ============================================
    # Chat Session Management (Context Memory)
    # ============================================
    
    async def create_chat(self) -> Optional[str]:
        """
        Create a new chat session and return its ID.
        
        Returns:
            Chat ID string, or None if creation failed
        """
        if not self.is_available:
            return None
        
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, "create-chat",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0:
                chat_id = stdout.decode().strip()
                logger.info(f"Created new chat session: {chat_id}")
                return chat_id
            else:
                logger.error(f"Failed to create chat: {stderr.decode()}")
                return None
        except Exception as e:
            logger.error(f"Error creating chat: {e}")
            return None
    
    def get_user_chat_id(self, user_id: str) -> Optional[str]:
        """
        Get the current CLI chat session ID for a user.
        
        Checks both local cache and session manager for cross-platform consistency.
        """
        # Check local cache first
        if user_id in self._user_chat_sessions:
            return self._user_chat_sessions[user_id]
        
        # Try session manager for cross-platform sessions
        try:
            from ..core.session import get_session_manager, ChatType
            session_mgr = get_session_manager()
            # Try to find session for this user
            sessions = session_mgr.list_user_sessions(user_id)
            for session in sessions:
                if session.cli_chat_id:
                    # Cache it locally
                    self._user_chat_sessions[user_id] = session.cli_chat_id
                    return session.cli_chat_id
        except Exception as e:
            logger.debug(f"Session manager lookup failed: {e}")
        
        return None
    
    def set_user_chat_id(self, user_id: str, chat_id: str) -> None:
        """
        Set the chat session ID for a user.
        
        Also syncs with session manager for cross-platform consistency.
        """
        self._user_chat_sessions[user_id] = chat_id
        logger.info(f"Set chat session for user {user_id}: {chat_id}")
        
        # Sync with session manager
        try:
            from ..core.session import get_session_manager, ChatType
            session_mgr = get_session_manager()
            # Get or create session for this user
            session = session_mgr.get_session(
                user_id=user_id,
                chat_id=user_id,  # For CLI, chat_id is same as user_id
                chat_type=ChatType.DM,
                channel="cli",
            )
            session_mgr.set_cli_chat_id(session.session_key, chat_id)
        except Exception as e:
            logger.debug(f"Session manager sync failed: {e}")
    
    def clear_user_chat(self, user_id: str) -> bool:
        """
        Clear the chat session for a user (start fresh conversation).
        
        Also clears from session manager.
        
        Returns:
            True if a session was cleared, False if no session existed
        """
        cleared = False
        
        if user_id in self._user_chat_sessions:
            old_chat = self._user_chat_sessions.pop(user_id)
            logger.info(f"Cleared chat session for user {user_id}: {old_chat}")
            cleared = True
        
        # Also clear from session manager
        try:
            from ..core.session import get_session_manager, ChatType
            session_mgr = get_session_manager()
            sessions = session_mgr.list_user_sessions(user_id)
            for session in sessions:
                if session.cli_chat_id:
                    session_mgr.set_cli_chat_id(session.session_key, "")
                    cleared = True
        except Exception as e:
            logger.debug(f"Session manager clear failed: {e}")
        
        return cleared
    
    def get_all_user_sessions(self) -> dict[str, str]:
        """Get all active user chat sessions."""
        return self._user_chat_sessions.copy()
    
    # ============================================
    # Model Management
    # ============================================
    
    async def list_models(self, force_refresh: bool = False) -> list[dict]:
        """
        List available models from Cursor CLI.
        
        Returns:
            List of model dictionaries with 'id', 'name', 'current', 'default' keys
        """
        if not self.is_available:
            return []
        
        # Return cached if available
        if self._models_fetched and not force_refresh:
            return self._available_models
        
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, "agent", "--list-models",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0:
                output = stdout.decode()
                models = self._parse_models_output(output)
                self._available_models = models
                self._models_fetched = True
                logger.info(f"Fetched {len(models)} CLI models")
                return models
            else:
                logger.error(f"Failed to list models: {stderr.decode()}")
                return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def _parse_models_output(self, output: str) -> list[dict]:
        """Parse the output of --list-models command."""
        models = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # Skip header and empty lines
            if not line or line.startswith('Available') or line.startswith('Tip:'):
                continue
            
            # Parse format: "model-id - Model Name (current, default)"
            if ' - ' in line:
                parts = line.split(' - ', 1)
                model_id = parts[0].strip()
                rest = parts[1].strip() if len(parts) > 1 else ""
                
                # Check for flags
                is_current = "(current" in rest.lower()
                is_default = "default)" in rest.lower()
                
                # Clean the name
                name = rest
                for flag in ['(current, default)', '(current)', '(default)']:
                    name = name.replace(flag, '').strip()
                
                models.append({
                    "id": model_id,
                    "name": name or model_id,
                    "current": is_current,
                    "default": is_default,
                })
        
        return models
    
    def get_user_model(self, user_id: str) -> Optional[str]:
        """Get the selected model for a user."""
        return self._user_models.get(user_id)
    
    def set_user_model(self, user_id: str, model_id: str) -> None:
        """Set the model for a user."""
        self._user_models[user_id] = model_id
        logger.info(f"Set CLI model for user {user_id}: {model_id}")
    
    def clear_user_model(self, user_id: str) -> bool:
        """Clear the model selection for a user (use default)."""
        if user_id in self._user_models:
            del self._user_models[user_id]
            logger.info(f"Cleared CLI model for user {user_id}")
            return True
        return False
    
    def get_all_user_models(self) -> dict[str, str]:
        """Get all user model selections."""
        return self._user_models.copy()
    
    async def run(
        self,
        prompt: str,
        working_directory: str = None,
        model: str = None,
        timeout: int = None,
        on_output: Callable[[str], None] = None,
        user_id: str = None,
    ) -> CLIResult:
        """
        Run a prompt through Cursor CLI with optional context memory.
        
        Args:
            prompt: The task or question for the AI
            working_directory: Directory to run in (default: config or cwd)
            model: Model to use (default: config or CLI default)
            timeout: Timeout in seconds (default: config)
            on_output: Callback for streaming output
            user_id: User ID for context memory (enables --resume)
        
        Returns:
            CLIResult with output and status
        """
        if not self.is_available:
            return CLIResult(
                success=False,
                error="Cursor CLI not installed",
                exit_code=-1,
            )
        
        start_time = datetime.now()
        cwd = working_directory or self.config.working_directory or os.getcwd()
        timeout = timeout or self.config.timeout
        
        # Build command (API key passed via env var for security)
        cmd = [self._cli_path]
        
        # Use --print for non-interactive output
        cmd.append("--print")
        
        # Use text output format
        cmd.extend(["--output-format", "text"])
        
        # Check for existing chat session (context memory)
        # Can be disabled via CLI_DISABLE_RESUME=1 if causing issues
        chat_id = None
        new_chat_created = False
        use_resume = os.getenv("CLI_DISABLE_RESUME", "").lower() not in ("1", "true", "yes")
        
        if user_id and use_resume:
            chat_id = self.get_user_chat_id(user_id)
            if not chat_id:
                # Create a new chat session for context memory
                chat_id = await self.create_chat()
                if chat_id:
                    self.set_user_chat_id(user_id, chat_id)
                    new_chat_created = True
            
            if chat_id:
                # Resume existing conversation (or newly created one)
                cmd.extend(["--resume", chat_id])
                logger.info(f"{'Starting new' if new_chat_created else 'Resuming'} chat {chat_id} for user {user_id}")
        elif user_id and not use_resume:
            logger.info(f"CLI resume disabled, running without context memory for user {user_id}")
        
        # Add model if specified (priority: explicit param > user setting > config)
        effective_model = model
        if not effective_model and user_id:
            effective_model = self.get_user_model(user_id)
        if not effective_model:
            effective_model = self.config.model
        
        if effective_model:
            cmd.extend(["--model", effective_model])
            logger.info(f"Using CLI model: {effective_model}")
        
        # Add the prompt
        cmd.append(prompt)
        
        # Prepare environment with API key (safer than command line args)
        # Command line args are visible in process list (ps aux)
        process_env = {**os.environ, "NO_COLOR": "1"}
        api_key = os.getenv("CURSOR_API_KEY", "")
        if api_key:
            process_env["CURSOR_API_KEY"] = api_key
        
        # Log the full command (without API key) for debugging
        safe_cmd = [c for c in cmd]  # Don't log API key
        logger.info(f"Running Cursor CLI in {cwd}" + (f" (chat: {chat_id})" if chat_id else " (new chat)"))
        logger.debug(f"CLI command: {' '.join(safe_cmd)}")
        logger.debug(f"Prompt: {prompt[:100]}...")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=process_env,  # API key passed via env (not command line)
            )
            
            output_lines = []
            error_lines = []
            
            async def read_stream(stream, lines, callback=None):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode('utf-8', errors='replace')
                    lines.append(text)
                    if callback:
                        callback(text)
            
            # Read stdout and stderr concurrently
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(proc.stdout, output_lines, on_output),
                    read_stream(proc.stderr, error_lines),
                ),
                timeout=timeout,
            )
            
            await proc.wait()
            
            duration = (datetime.now() - start_time).total_seconds()
            output = "".join(output_lines)
            error = "".join(error_lines)
            
            # Log output for debugging
            logger.info(f"CLI completed in {duration:.1f}s, exit code: {proc.returncode}")
            logger.debug(f"CLI output length: {len(output)} chars")
            if output:
                logger.debug(f"CLI output preview: {output[:200]}...")
            if error:
                logger.warning(f"CLI stderr: {error[:200]}...")
            
            # Extract modified files from output
            files_modified = self._extract_modified_files(output)
            
            return CLIResult(
                success=proc.returncode == 0,
                output=output,
                error=error,
                exit_code=proc.returncode,
                duration=duration,
                files_modified=files_modified,
            )
            
        except asyncio.TimeoutError:
            proc.kill()
            return CLIResult(
                success=False,
                error=f"CLI operation timed out after {timeout}s",
                exit_code=-1,
                duration=timeout,
            )
        except Exception as e:
            logger.error(f"CLI error: {e}")
            return CLIResult(
                success=False,
                error=str(e),
                exit_code=-1,
            )
    
    def _extract_modified_files(self, output: str) -> list[str]:
        """Extract list of modified files from CLI output."""
        files = []
        
        # Common patterns for file modifications
        patterns = [
            r"(?:Modified|Created|Updated|Wrote|Edited):\s*(.+)",
            r"(?:✓|✔)\s*(.+\.\w+)",
            r"File:\s*(.+)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            files.extend(matches)
        
        return list(set(files))
    
    async def ask(
        self,
        question: str,
        context: str = None,
        working_directory: str = None,
    ) -> CLIResult:
        """
        Ask a question (no file modifications).
        
        Args:
            question: The question to ask
            context: Additional context
            working_directory: Directory context
        
        Returns:
            CLIResult with the answer
        """
        prompt = question
        if context:
            prompt = f"Context: {context}\n\nQuestion: {question}"
        
        return await self.run_ask(
            prompt=prompt,
            working_directory=working_directory,
        )
    
    async def run_ask(
        self,
        prompt: str,
        working_directory: str = None,
        timeout: int = None,
    ) -> CLIResult:
        """
        Run in ask mode (read-only, Q&A style).
        
        Args:
            prompt: The question
            working_directory: Directory context
            timeout: Timeout in seconds
        
        Returns:
            CLIResult with the answer
        """
        if not self.is_available:
            return CLIResult(
                success=False,
                error="Cursor CLI not installed",
                exit_code=-1,
            )
        
        start_time = datetime.now()
        cwd = working_directory or self.config.working_directory or os.getcwd()
        timeout = timeout or self.config.timeout
        
        # Build command with --mode ask (API key via env for security)
        cmd = [self._cli_path, "--print", "--mode", "ask", prompt]
        
        # Prepare environment with API key (safer than command line args)
        process_env = {**os.environ, "NO_COLOR": "1"}
        api_key = os.getenv("CURSOR_API_KEY", "")
        if api_key:
            process_env["CURSOR_API_KEY"] = api_key
        
        logger.info(f"Running Cursor CLI (ask mode) in {cwd}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=process_env,  # API key passed via env (not command line)
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            output = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace')
            
            return CLIResult(
                success=proc.returncode == 0,
                output=output,
                error=error,
                exit_code=proc.returncode,
                duration=duration,
            )
            
        except asyncio.TimeoutError:
            proc.kill()
            return CLIResult(
                success=False,
                error=f"CLI operation timed out after {timeout}s",
                exit_code=-1,
                duration=timeout,
            )
        except Exception as e:
            logger.error(f"CLI ask error: {e}")
            return CLIResult(
                success=False,
                error=str(e),
                exit_code=-1,
            )
    
    async def edit(
        self,
        instruction: str,
        file_path: str = None,
        working_directory: str = None,
    ) -> CLIResult:
        """
        Edit files based on instruction.
        
        Args:
            instruction: What to do
            file_path: Specific file to edit (optional)
            working_directory: Directory context
        
        Returns:
            CLIResult with changes
        """
        prompt = instruction
        if file_path:
            prompt = f"Edit file {file_path}: {instruction}"
        
        return await self.run(
            prompt=prompt,
            working_directory=working_directory,
        )
    
    async def generate(
        self,
        description: str,
        output_path: str = None,
        working_directory: str = None,
    ) -> CLIResult:
        """
        Generate new code or files.
        
        Args:
            description: What to generate
            output_path: Where to save (optional)
            working_directory: Directory context
        
        Returns:
            CLIResult with generated content
        """
        prompt = f"Generate: {description}"
        if output_path:
            prompt = f"Create file {output_path}: {description}"
        
        return await self.run(
            prompt=prompt,
            working_directory=working_directory,
        )


# ============================================
# Global Instance
# ============================================

_cli_agent: Optional[CursorCLIAgent] = None


def get_cli_agent() -> CursorCLIAgent:
    """Get or create the global CLI agent instance."""
    global _cli_agent
    if _cli_agent is None:
        # Priority: CURSOR_WORKING_DIR > settings.effective_workspace_path
        # This ensures consistency with other modules that use CURSOR_WORKSPACE_PATH
        working_dir = os.getenv("CURSOR_WORKING_DIR", "")
        if not working_dir:
            working_dir = settings.effective_workspace_path
        
        config = CLIConfig(
            working_directory=working_dir,
            model=os.getenv("CURSOR_CLI_MODEL", ""),
            timeout=int(os.getenv("CURSOR_CLI_TIMEOUT", "300")),
        )
        _cli_agent = CursorCLIAgent(config)
        logger.info(f"CLI Agent initialized with working directory: {working_dir}")
    return _cli_agent


def is_cli_available() -> bool:
    """Check if Cursor CLI is available."""
    return get_cli_agent().is_available


def reset_cli_agent() -> None:
    """Reset the global CLI agent instance (e.g., after workspace change)."""
    global _cli_agent
    _cli_agent = None
    logger.info("CLI Agent reset, will reinitialize on next use")


def get_cli_working_directory() -> str:
    """Get the current working directory for CLI agent."""
    agent = get_cli_agent()
    return agent.config.working_directory or os.getcwd()


__all__ = [
    "CLIStatus",
    "CLIConfig",
    "CLIResult",
    "CursorCLIAgent",
    "get_cli_agent",
    "is_cli_available",
    "reset_cli_agent",
    "get_cli_working_directory",
]
