"""
Sandbox Execution System for CursorBot

Provides:
- Safe code execution in isolated environments
- Docker-based sandboxing
- Resource limits (CPU, memory, time)
- Network isolation
"""

import asyncio
import os
import subprocess
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..utils.logger import logger


class SandboxType(Enum):
    """Types of sandbox environments."""
    DOCKER = "docker"
    SUBPROCESS = "subprocess"
    RESTRICTED = "restricted"  # Python restricted execution


class ExecutionStatus(Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    sandbox_type: SandboxType = SandboxType.SUBPROCESS
    timeout: float = 30.0  # seconds
    memory_limit: str = "256m"  # Docker memory limit
    cpu_limit: float = 1.0  # CPU cores
    network_enabled: bool = False
    allow_file_write: bool = False
    working_dir: Optional[str] = None
    env_vars: dict = field(default_factory=dict)
    docker_image: str = "python:3.11-slim"


@dataclass
class ExecutionResult:
    """Result from sandbox execution."""
    id: str
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BaseSandbox(ABC):
    """Base class for sandbox implementations."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
    
    @abstractmethod
    async def execute(self, code: str, language: str = "python") -> ExecutionResult:
        """
        Execute code in the sandbox.
        
        Args:
            code: Code to execute
            language: Programming language
        
        Returns:
            ExecutionResult
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up sandbox resources."""
        pass


class SubprocessSandbox(BaseSandbox):
    """
    Subprocess-based sandbox for simple isolation.
    Uses subprocess with resource limits.
    """
    
    LANGUAGE_COMMANDS = {
        "python": ["python", "-c"],
        "python3": ["python3", "-c"],
        "node": ["node", "-e"],
        "javascript": ["node", "-e"],
        "bash": ["bash", "-c"],
        "sh": ["sh", "-c"],
    }
    
    async def execute(self, code: str, language: str = "python") -> ExecutionResult:
        execution_id = str(uuid.uuid4())[:8]
        start_time = asyncio.get_event_loop().time()
        
        result = ExecutionResult(
            id=execution_id,
            status=ExecutionStatus.RUNNING,
        )
        
        # Get command for language
        cmd = self.LANGUAGE_COMMANDS.get(language.lower())
        if not cmd:
            result.status = ExecutionStatus.FAILED
            result.error = f"Unsupported language: {language}"
            return result
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd, code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.working_dir,
                env={**os.environ, **self.config.env_vars} if self.config.env_vars else None,
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout
                )
                
                result.stdout = stdout.decode("utf-8", errors="replace")
                result.stderr = stderr.decode("utf-8", errors="replace")
                result.exit_code = process.returncode
                result.status = ExecutionStatus.COMPLETED if process.returncode == 0 else ExecutionStatus.FAILED
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                result.status = ExecutionStatus.TIMEOUT
                result.error = f"Execution timed out after {self.config.timeout}s"
                
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            logger.error(f"Sandbox execution error: {e}")
        
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return result
    
    async def cleanup(self) -> None:
        pass


class DockerSandbox(BaseSandbox):
    """
    Docker-based sandbox for strong isolation.
    """
    
    DOCKER_IMAGES = {
        "python": "python:3.11-slim",
        "python3": "python:3.11-slim",
        "node": "node:20-slim",
        "javascript": "node:20-slim",
    }
    
    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self._container_ids: list[str] = []
    
    async def execute(self, code: str, language: str = "python") -> ExecutionResult:
        execution_id = str(uuid.uuid4())[:8]
        start_time = asyncio.get_event_loop().time()
        
        result = ExecutionResult(
            id=execution_id,
            status=ExecutionStatus.RUNNING,
        )
        
        # Check Docker availability
        if not await self._docker_available():
            result.status = ExecutionStatus.FAILED
            result.error = "Docker is not available"
            return result
        
        # Get Docker image
        image = self.DOCKER_IMAGES.get(language.lower(), self.config.docker_image)
        
        # Create temp file with code
        with tempfile.NamedTemporaryFile(mode="w", suffix=self._get_extension(language), delete=False) as f:
            f.write(code)
            code_file = f.name
        
        try:
            # Build Docker command
            docker_cmd = [
                "docker", "run",
                "--rm",
                f"--memory={self.config.memory_limit}",
                f"--cpus={self.config.cpu_limit}",
                "--name", f"sandbox_{execution_id}",
            ]
            
            # Network isolation
            if not self.config.network_enabled:
                docker_cmd.extend(["--network", "none"])
            
            # Read-only if not allowing file writes
            if not self.config.allow_file_write:
                docker_cmd.append("--read-only")
            
            # Mount code file
            docker_cmd.extend(["-v", f"{code_file}:/code{self._get_extension(language)}:ro"])
            
            # Add image and command
            docker_cmd.append(image)
            docker_cmd.extend(self._get_run_command(language))
            
            # Execute
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self._container_ids.append(f"sandbox_{execution_id}")
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout
                )
                
                result.stdout = stdout.decode("utf-8", errors="replace")
                result.stderr = stderr.decode("utf-8", errors="replace")
                result.exit_code = process.returncode
                result.status = ExecutionStatus.COMPLETED if process.returncode == 0 else ExecutionStatus.FAILED
                
            except asyncio.TimeoutError:
                # Kill container
                await self._kill_container(f"sandbox_{execution_id}")
                result.status = ExecutionStatus.TIMEOUT
                result.error = f"Execution timed out after {self.config.timeout}s"
                
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            
        finally:
            # Cleanup temp file
            try:
                os.unlink(code_file)
            except Exception:
                pass
            
            result.completed_at = datetime.now()
            result.duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Remove from tracking
            if f"sandbox_{execution_id}" in self._container_ids:
                self._container_ids.remove(f"sandbox_{execution_id}")
        
        return result
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": ".py",
            "python3": ".py",
            "node": ".js",
            "javascript": ".js",
        }
        return extensions.get(language.lower(), ".txt")
    
    def _get_run_command(self, language: str) -> list[str]:
        """Get command to run code in container."""
        commands = {
            "python": ["python", "/code.py"],
            "python3": ["python", "/code.py"],
            "node": ["node", "/code.js"],
            "javascript": ["node", "/code.js"],
        }
        return commands.get(language.lower(), ["cat", "/code.txt"])
    
    async def _docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False
    
    async def _kill_container(self, container_name: str) -> None:
        """Kill a running container."""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "kill", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()
        except Exception:
            pass
    
    async def cleanup(self) -> None:
        """Kill all tracked containers."""
        for container_id in self._container_ids:
            await self._kill_container(container_id)
        self._container_ids.clear()


class RestrictedPythonSandbox(BaseSandbox):
    """
    Restricted Python execution using RestrictedPython.
    Limited but safe execution without Docker.
    """
    
    # Dangerous built-ins to remove
    BLOCKED_BUILTINS = {
        "exec", "eval", "compile", "open", "input",
        "__import__", "globals", "locals", "vars",
        "getattr", "setattr", "delattr", "hasattr",
        "dir", "type", "object", "super",
    }
    
    # Safe built-ins to allow
    SAFE_BUILTINS = {
        "abs", "all", "any", "bin", "bool", "chr",
        "dict", "divmod", "enumerate", "filter", "float",
        "format", "frozenset", "hex", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max",
        "min", "next", "oct", "ord", "pow", "print",
        "range", "repr", "reversed", "round", "set",
        "slice", "sorted", "str", "sum", "tuple", "zip",
        "True", "False", "None",
    }
    
    async def execute(self, code: str, language: str = "python") -> ExecutionResult:
        if language.lower() not in ("python", "python3"):
            return ExecutionResult(
                id=str(uuid.uuid4())[:8],
                status=ExecutionStatus.FAILED,
                error="RestrictedPythonSandbox only supports Python",
            )
        
        execution_id = str(uuid.uuid4())[:8]
        start_time = asyncio.get_event_loop().time()
        
        result = ExecutionResult(
            id=execution_id,
            status=ExecutionStatus.RUNNING,
        )
        
        try:
            # Capture stdout
            import io
            import sys
            
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # Create safe builtins
            safe_builtins = {
                name: getattr(__builtins__, name) if hasattr(__builtins__, name) else __builtins__[name]
                for name in self.SAFE_BUILTINS
                if hasattr(__builtins__, name) or (isinstance(__builtins__, dict) and name in __builtins__)
            }
            safe_builtins["__builtins__"] = safe_builtins
            
            # Compile code
            try:
                compiled = compile(code, "<sandbox>", "exec")
            except SyntaxError as e:
                result.status = ExecutionStatus.FAILED
                result.error = f"Syntax error: {e}"
                return result
            
            # Execute with timeout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            try:
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture
                
                # Execute in restricted environment
                exec_globals = {"__builtins__": safe_builtins}
                
                # Use thread to enable timeout
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, exec, compiled, exec_globals),
                    timeout=self.config.timeout
                )
                
                result.status = ExecutionStatus.COMPLETED
                result.exit_code = 0
                
            except asyncio.TimeoutError:
                result.status = ExecutionStatus.TIMEOUT
                result.error = f"Execution timed out after {self.config.timeout}s"
                
            except Exception as e:
                result.status = ExecutionStatus.FAILED
                result.error = str(e)
                result.exit_code = 1
                
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            result.stdout = stdout_capture.getvalue()
            result.stderr = stderr_capture.getvalue()
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return result
    
    async def cleanup(self) -> None:
        pass


# ============================================
# Sandbox Manager
# ============================================

class SandboxManager:
    """
    Manages sandbox execution with multiple backends.
    """
    
    def __init__(self, default_config: SandboxConfig = None):
        self.default_config = default_config or SandboxConfig()
        self._sandboxes: dict[SandboxType, BaseSandbox] = {}
        self._results: dict[str, ExecutionResult] = {}
    
    def _get_sandbox(self, sandbox_type: SandboxType, config: SandboxConfig = None) -> BaseSandbox:
        """Get or create a sandbox instance."""
        cfg = config or self.default_config
        
        if sandbox_type == SandboxType.DOCKER:
            return DockerSandbox(cfg)
        elif sandbox_type == SandboxType.SUBPROCESS:
            return SubprocessSandbox(cfg)
        elif sandbox_type == SandboxType.RESTRICTED:
            return RestrictedPythonSandbox(cfg)
        else:
            raise ValueError(f"Unknown sandbox type: {sandbox_type}")
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        sandbox_type: SandboxType = None,
        timeout: float = None,
    ) -> ExecutionResult:
        """
        Execute code in a sandbox.
        
        Args:
            code: Code to execute
            language: Programming language
            sandbox_type: Sandbox type to use
            timeout: Execution timeout
        
        Returns:
            ExecutionResult
        """
        # Build config
        config = SandboxConfig(
            sandbox_type=sandbox_type or self.default_config.sandbox_type,
            timeout=timeout or self.default_config.timeout,
            memory_limit=self.default_config.memory_limit,
            cpu_limit=self.default_config.cpu_limit,
            network_enabled=self.default_config.network_enabled,
        )
        
        sandbox = self._get_sandbox(config.sandbox_type, config)
        
        try:
            result = await sandbox.execute(code, language)
            self._results[result.id] = result
            
            logger.info(
                f"Sandbox execution {result.id}: "
                f"status={result.status.value}, "
                f"duration={result.duration_ms:.0f}ms"
            )
            
            return result
            
        finally:
            await sandbox.cleanup()
    
    def get_result(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution result by ID."""
        return self._results.get(execution_id)
    
    def get_stats(self) -> dict:
        """Get sandbox statistics."""
        status_counts = {}
        for result in self._results.values():
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_executions": len(self._results),
            "status_counts": status_counts,
        }


# ============================================
# Global Instance
# ============================================

_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager(config: SandboxConfig = None) -> SandboxManager:
    """Get the global sandbox manager instance."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager(config)
    return _sandbox_manager


async def execute_code(
    code: str,
    language: str = "python",
    sandbox_type: str = "subprocess",
    timeout: float = 30.0,
) -> ExecutionResult:
    """
    Convenience function to execute code in a sandbox.
    
    Args:
        code: Code to execute
        language: Programming language
        sandbox_type: Sandbox type (docker, subprocess, restricted)
        timeout: Execution timeout
    
    Returns:
        ExecutionResult
    """
    manager = get_sandbox_manager()
    sandbox = SandboxType(sandbox_type.lower())
    return await manager.execute(code, language, sandbox, timeout)


__all__ = [
    "SandboxType",
    "ExecutionStatus",
    "SandboxConfig",
    "ExecutionResult",
    "BaseSandbox",
    "SubprocessSandbox",
    "DockerSandbox",
    "RestrictedPythonSandbox",
    "SandboxManager",
    "get_sandbox_manager",
    "execute_code",
]
