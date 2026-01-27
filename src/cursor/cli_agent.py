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
    """
    
    def __init__(self, config: CLIConfig = None):
        self.config = config or CLIConfig()
        self._cli_path = self._find_cli()
        self._status = CLIStatus.AVAILABLE if self._cli_path else CLIStatus.NOT_INSTALLED
    
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
    
    async def run(
        self,
        prompt: str,
        working_directory: str = None,
        model: str = None,
        timeout: int = None,
        on_output: Callable[[str], None] = None,
    ) -> CLIResult:
        """
        Run a prompt through Cursor CLI.
        
        Args:
            prompt: The task or question for the AI
            working_directory: Directory to run in (default: config or cwd)
            model: Model to use (default: config or CLI default)
            timeout: Timeout in seconds (default: config)
            on_output: Callback for streaming output
        
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
        
        # Build command
        cmd = [self._cli_path]
        
        # Add API key if available
        api_key = os.getenv("CURSOR_API_KEY", "")
        if api_key:
            cmd.extend(["--api-key", api_key])
        
        # Use --print for non-interactive output
        cmd.append("--print")
        
        # Use text output format
        cmd.extend(["--output-format", "text"])
        
        # Add the prompt
        cmd.append(prompt)
        
        logger.info(f"Running Cursor CLI: {' '.join(cmd[:3])}... in {cwd}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, "NO_COLOR": "1"},  # Disable color codes
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
        
        # Build command with --mode ask
        cmd = [self._cli_path]
        
        # Add API key if available
        api_key = os.getenv("CURSOR_API_KEY", "")
        if api_key:
            cmd.extend(["--api-key", api_key])
        
        cmd.extend(["--print", "--mode", "ask", prompt])
        
        logger.info(f"Running Cursor CLI (ask mode) in {cwd}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, "NO_COLOR": "1"},
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
        config = CLIConfig(
            working_directory=os.getenv("CURSOR_WORKING_DIR", ""),
            model=os.getenv("CURSOR_CLI_MODEL", ""),
            timeout=int(os.getenv("CURSOR_CLI_TIMEOUT", "300")),
        )
        _cli_agent = CursorCLIAgent(config)
    return _cli_agent


def is_cli_available() -> bool:
    """Check if Cursor CLI is available."""
    return get_cli_agent().is_available


__all__ = [
    "CLIStatus",
    "CLIConfig",
    "CLIResult",
    "CursorCLIAgent",
    "get_cli_agent",
    "is_cli_available",
]
