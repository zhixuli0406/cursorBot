"""
Doctor - System Diagnostics Tool for CursorBot

Provides:
- Comprehensive system health checks
- Configuration validation
- Dependency verification
- Performance diagnostics
- Troubleshooting recommendations
"""

import asyncio
import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class DiagnosticLevel(Enum):
    """Diagnostic result severity levels."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    INFO = "info"


@dataclass
class DiagnosticResult:
    """Result from a single diagnostic check."""
    name: str
    level: DiagnosticLevel
    message: str
    details: dict = field(default_factory=dict)
    recommendation: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "recommendation": self.recommendation,
        }


@dataclass
class DiagnosticReport:
    """Complete diagnostic report."""
    timestamp: datetime = field(default_factory=datetime.now)
    results: list[DiagnosticResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    
    @property
    def overall_status(self) -> DiagnosticLevel:
        """Determine overall status from all results."""
        if any(r.level == DiagnosticLevel.CRITICAL for r in self.results):
            return DiagnosticLevel.CRITICAL
        if any(r.level == DiagnosticLevel.ERROR for r in self.results):
            return DiagnosticLevel.ERROR
        if any(r.level == DiagnosticLevel.WARNING for r in self.results):
            return DiagnosticLevel.WARNING
        return DiagnosticLevel.OK
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
        }
    
    def to_text(self) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 50,
            "CursorBot Diagnostic Report",
            f"Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Overall Status: {self.overall_status.value.upper()}",
            "=" * 50,
            "",
        ]
        
        # Group by level
        for level in [DiagnosticLevel.CRITICAL, DiagnosticLevel.ERROR, 
                      DiagnosticLevel.WARNING, DiagnosticLevel.OK, DiagnosticLevel.INFO]:
            level_results = [r for r in self.results if r.level == level]
            if level_results:
                lines.append(f"[{level.value.upper()}]")
                for r in level_results:
                    icon = {"ok": "✓", "warning": "⚠", "error": "✗", "critical": "☠", "info": "ℹ"}
                    lines.append(f"  {icon.get(level.value, '•')} {r.name}: {r.message}")
                    if r.recommendation:
                        lines.append(f"    → {r.recommendation}")
                lines.append("")
        
        # Summary
        if self.summary:
            lines.append("Summary:")
            for key, value in self.summary.items():
                lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)


class Doctor:
    """
    System diagnostics tool for CursorBot.
    """
    
    def __init__(self):
        self._checks: list[tuple[str, Callable]] = []
        self._register_default_checks()
    
    def _register_default_checks(self) -> None:
        """Register all default diagnostic checks."""
        self.register_check("python_version", self._check_python_version)
        self.register_check("environment_variables", self._check_env_vars)
        self.register_check("disk_space", self._check_disk_space)
        self.register_check("memory", self._check_memory)
        self.register_check("dependencies", self._check_dependencies)
        self.register_check("telegram_config", self._check_telegram_config)
        self.register_check("llm_providers", self._check_llm_providers)
        self.register_check("cursor_api", self._check_cursor_api)
        self.register_check("database", self._check_database)
        self.register_check("network", self._check_network)
        self.register_check("docker", self._check_docker)
        self.register_check("git", self._check_git)
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """Register a diagnostic check."""
        self._checks.append((name, check_func))
    
    async def run_all_checks(self) -> DiagnosticReport:
        """Run all registered diagnostic checks."""
        report = DiagnosticReport()
        
        for name, check_func in self._checks:
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                if isinstance(result, DiagnosticResult):
                    report.results.append(result)
                elif isinstance(result, list):
                    report.results.extend(result)
                    
            except Exception as e:
                report.results.append(DiagnosticResult(
                    name=name,
                    level=DiagnosticLevel.ERROR,
                    message=f"Check failed: {str(e)}",
                ))
        
        # Generate summary
        report.summary = {
            "total_checks": len(report.results),
            "ok": sum(1 for r in report.results if r.level == DiagnosticLevel.OK),
            "warnings": sum(1 for r in report.results if r.level == DiagnosticLevel.WARNING),
            "errors": sum(1 for r in report.results if r.level == DiagnosticLevel.ERROR),
            "critical": sum(1 for r in report.results if r.level == DiagnosticLevel.CRITICAL),
        }
        
        return report
    
    async def run_check(self, name: str) -> Optional[DiagnosticResult]:
        """Run a specific check by name."""
        for check_name, check_func in self._checks:
            if check_name == name:
                if asyncio.iscoroutinefunction(check_func):
                    return await check_func()
                return check_func()
        return None
    
    # ============================================
    # Default Diagnostic Checks
    # ============================================
    
    def _check_python_version(self) -> DiagnosticResult:
        """Check Python version compatibility."""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major != 3:
            return DiagnosticResult(
                name="python_version",
                level=DiagnosticLevel.CRITICAL,
                message=f"Python {version_str} - Requires Python 3",
                recommendation="Install Python 3.10-3.12",
            )
        
        if version.minor < 10:
            return DiagnosticResult(
                name="python_version",
                level=DiagnosticLevel.ERROR,
                message=f"Python {version_str} - Too old",
                recommendation="Upgrade to Python 3.10 or later",
            )
        
        if version.minor >= 13:
            return DiagnosticResult(
                name="python_version",
                level=DiagnosticLevel.WARNING,
                message=f"Python {version_str} - May have compatibility issues",
                recommendation="Consider using Python 3.11 or 3.12",
            )
        
        return DiagnosticResult(
            name="python_version",
            level=DiagnosticLevel.OK,
            message=f"Python {version_str}",
            details={"version": version_str, "platform": platform.platform()},
        )
    
    def _check_env_vars(self) -> list[DiagnosticResult]:
        """Check required environment variables."""
        results = []
        
        required = [
            ("TELEGRAM_BOT_TOKEN", "Telegram bot functionality"),
            ("TELEGRAM_ALLOWED_USERS", "User authorization"),
        ]
        
        optional = [
            ("CURSOR_API_KEY", "Background Agent"),
            ("OPENAI_API_KEY", "OpenAI models"),
            ("ANTHROPIC_API_KEY", "Anthropic models"),
            ("GOOGLE_GENERATIVE_AI_API_KEY", "Google Gemini"),
            ("OPENROUTER_API_KEY", "OpenRouter proxy"),
            ("DISCORD_BOT_TOKEN", "Discord bot"),
        ]
        
        for var, purpose in required:
            value = os.getenv(var)
            if not value:
                results.append(DiagnosticResult(
                    name=f"env_{var}",
                    level=DiagnosticLevel.CRITICAL,
                    message=f"{var} not set - Required for {purpose}",
                    recommendation=f"Set {var} in .env file",
                ))
            else:
                results.append(DiagnosticResult(
                    name=f"env_{var}",
                    level=DiagnosticLevel.OK,
                    message=f"{var} configured",
                ))
        
        configured_optional = 0
        for var, purpose in optional:
            value = os.getenv(var)
            if value:
                configured_optional += 1
        
        results.append(DiagnosticResult(
            name="env_optional",
            level=DiagnosticLevel.INFO,
            message=f"{configured_optional}/{len(optional)} optional providers configured",
            details={"configured": configured_optional, "total": len(optional)},
        ))
        
        return results
    
    def _check_disk_space(self) -> DiagnosticResult:
        """Check available disk space."""
        try:
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024 ** 3)
            used_percent = (used / total) * 100
            
            if free_gb < 1:
                level = DiagnosticLevel.CRITICAL
                message = f"Disk space critically low: {free_gb:.1f} GB free"
                recommendation = "Free up disk space immediately"
            elif free_gb < 5:
                level = DiagnosticLevel.WARNING
                message = f"Disk space low: {free_gb:.1f} GB free"
                recommendation = "Consider freeing up disk space"
            else:
                level = DiagnosticLevel.OK
                message = f"{free_gb:.1f} GB free ({100-used_percent:.0f}%)"
                recommendation = None
            
            return DiagnosticResult(
                name="disk_space",
                level=level,
                message=message,
                details={"free_gb": round(free_gb, 2), "used_percent": round(used_percent, 1)},
                recommendation=recommendation,
            )
        except Exception as e:
            return DiagnosticResult(
                name="disk_space",
                level=DiagnosticLevel.WARNING,
                message=f"Could not check disk space: {e}",
            )
    
    def _check_memory(self) -> DiagnosticResult:
        """Check available memory."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            available_gb = mem.available / (1024 ** 3)
            used_percent = mem.percent
            
            if available_gb < 0.5:
                level = DiagnosticLevel.CRITICAL
                message = f"Memory critically low: {available_gb:.2f} GB available"
                recommendation = "Close other applications or increase RAM"
            elif available_gb < 1:
                level = DiagnosticLevel.WARNING
                message = f"Memory low: {available_gb:.2f} GB available"
                recommendation = "Monitor memory usage"
            else:
                level = DiagnosticLevel.OK
                message = f"{available_gb:.2f} GB available ({100-used_percent:.0f}%)"
                recommendation = None
            
            return DiagnosticResult(
                name="memory",
                level=level,
                message=message,
                details={"available_gb": round(available_gb, 2), "used_percent": used_percent},
                recommendation=recommendation,
            )
        except ImportError:
            return DiagnosticResult(
                name="memory",
                level=DiagnosticLevel.INFO,
                message="psutil not installed - cannot check memory",
                recommendation="pip install psutil for memory monitoring",
            )
    
    def _check_dependencies(self) -> list[DiagnosticResult]:
        """Check required Python dependencies."""
        results = []
        
        required_packages = [
            ("python-telegram-bot", "telegram"),
            ("httpx", "httpx"),
            ("pydantic", "pydantic"),
            ("pydantic-settings", "pydantic_settings"),
        ]
        
        optional_packages = [
            ("playwright", "playwright"),
            ("discord.py", "discord"),
            ("psutil", "psutil"),
            ("edge-tts", "edge_tts"),
        ]
        
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                results.append(DiagnosticResult(
                    name=f"dep_{package_name}",
                    level=DiagnosticLevel.OK,
                    message=f"{package_name} installed",
                ))
            except ImportError:
                results.append(DiagnosticResult(
                    name=f"dep_{package_name}",
                    level=DiagnosticLevel.ERROR,
                    message=f"{package_name} not installed",
                    recommendation=f"pip install {package_name}",
                ))
        
        optional_installed = 0
        for package_name, import_name in optional_packages:
            try:
                __import__(import_name)
                optional_installed += 1
            except ImportError:
                pass
        
        results.append(DiagnosticResult(
            name="dep_optional",
            level=DiagnosticLevel.INFO,
            message=f"{optional_installed}/{len(optional_packages)} optional packages installed",
        ))
        
        return results
    
    def _check_telegram_config(self) -> DiagnosticResult:
        """Check Telegram bot configuration."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        users = os.getenv("TELEGRAM_ALLOWED_USERS")
        
        if not token:
            return DiagnosticResult(
                name="telegram_config",
                level=DiagnosticLevel.CRITICAL,
                message="Telegram bot token not configured",
                recommendation="Set TELEGRAM_BOT_TOKEN in .env",
            )
        
        if not users:
            return DiagnosticResult(
                name="telegram_config",
                level=DiagnosticLevel.WARNING,
                message="No allowed users configured",
                recommendation="Set TELEGRAM_ALLOWED_USERS to restrict access",
            )
        
        user_count = len(users.split(","))
        return DiagnosticResult(
            name="telegram_config",
            level=DiagnosticLevel.OK,
            message=f"Telegram configured with {user_count} allowed user(s)",
            details={"allowed_users_count": user_count},
        )
    
    def _check_llm_providers(self) -> DiagnosticResult:
        """Check LLM provider configuration."""
        providers = []
        
        if os.getenv("OPENAI_API_KEY"):
            providers.append("OpenAI")
        if os.getenv("ANTHROPIC_API_KEY"):
            providers.append("Anthropic")
        if os.getenv("GOOGLE_GENERATIVE_AI_API_KEY"):
            providers.append("Google")
        if os.getenv("OPENROUTER_API_KEY"):
            providers.append("OpenRouter")
        if os.getenv("OLLAMA_ENABLED", "").lower() == "true":
            providers.append("Ollama")
        
        if not providers:
            return DiagnosticResult(
                name="llm_providers",
                level=DiagnosticLevel.WARNING,
                message="No LLM providers configured",
                recommendation="Configure at least one: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.",
            )
        
        return DiagnosticResult(
            name="llm_providers",
            level=DiagnosticLevel.OK,
            message=f"{len(providers)} provider(s): {', '.join(providers)}",
            details={"providers": providers},
        )
    
    def _check_cursor_api(self) -> DiagnosticResult:
        """Check Cursor Background Agent configuration."""
        enabled = os.getenv("BACKGROUND_AGENT_ENABLED", "").lower() == "true"
        api_key = os.getenv("CURSOR_API_KEY")
        
        if not enabled:
            return DiagnosticResult(
                name="cursor_api",
                level=DiagnosticLevel.INFO,
                message="Background Agent disabled",
            )
        
        if not api_key:
            return DiagnosticResult(
                name="cursor_api",
                level=DiagnosticLevel.WARNING,
                message="Background Agent enabled but no API key",
                recommendation="Set CURSOR_API_KEY in .env",
            )
        
        return DiagnosticResult(
            name="cursor_api",
            level=DiagnosticLevel.OK,
            message="Cursor Background Agent configured",
        )
    
    def _check_database(self) -> DiagnosticResult:
        """Check database configuration."""
        db_path = os.getenv("DATABASE_PATH", "./data/cursorbot.db")
        
        # Check if data directory exists
        data_dir = os.path.dirname(db_path)
        if data_dir and not os.path.exists(data_dir):
            return DiagnosticResult(
                name="database",
                level=DiagnosticLevel.WARNING,
                message=f"Data directory does not exist: {data_dir}",
                recommendation="Directory will be created on first run",
            )
        
        return DiagnosticResult(
            name="database",
            level=DiagnosticLevel.OK,
            message=f"Database path: {db_path}",
            details={"path": db_path},
        )
    
    async def _check_network(self) -> DiagnosticResult:
        """Check network connectivity."""
        import httpx
        
        endpoints = [
            ("Telegram API", "https://api.telegram.org"),
            ("OpenAI API", "https://api.openai.com"),
        ]
        
        accessible = []
        failed = []
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in endpoints:
                try:
                    response = await client.head(url)
                    if response.status_code < 500:
                        accessible.append(name)
                    else:
                        failed.append(name)
                except Exception:
                    failed.append(name)
        
        if failed:
            if "Telegram API" in failed:
                level = DiagnosticLevel.CRITICAL
                message = "Cannot reach Telegram API"
                recommendation = "Check internet connection or firewall"
            else:
                level = DiagnosticLevel.WARNING
                message = f"Some endpoints unreachable: {', '.join(failed)}"
                recommendation = "Check network connectivity"
        else:
            level = DiagnosticLevel.OK
            message = "Network connectivity OK"
            recommendation = None
        
        return DiagnosticResult(
            name="network",
            level=level,
            message=message,
            details={"accessible": accessible, "failed": failed},
            recommendation=recommendation,
        )
    
    def _check_docker(self) -> DiagnosticResult:
        """Check if running in Docker."""
        in_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER")
        
        if in_docker:
            return DiagnosticResult(
                name="docker",
                level=DiagnosticLevel.INFO,
                message="Running in Docker container",
                details={"in_docker": True},
            )
        
        # Check if Docker is available
        docker_available = shutil.which("docker") is not None
        
        return DiagnosticResult(
            name="docker",
            level=DiagnosticLevel.INFO,
            message="Running locally" + (" (Docker available)" if docker_available else ""),
            details={"in_docker": False, "docker_available": docker_available},
        )
    
    def _check_git(self) -> DiagnosticResult:
        """Check Git availability."""
        git_path = shutil.which("git")
        
        if not git_path:
            return DiagnosticResult(
                name="git",
                level=DiagnosticLevel.WARNING,
                message="Git not found",
                recommendation="Install Git for version control features",
            )
        
        return DiagnosticResult(
            name="git",
            level=DiagnosticLevel.OK,
            message="Git available",
            details={"path": git_path},
        )


# ============================================
# Global Instance
# ============================================

_doctor: Optional[Doctor] = None


def get_doctor() -> Doctor:
    """Get the global Doctor instance."""
    global _doctor
    if _doctor is None:
        _doctor = Doctor()
    return _doctor


async def run_diagnostics() -> DiagnosticReport:
    """Convenience function to run all diagnostics."""
    doctor = get_doctor()
    return await doctor.run_all_checks()


__all__ = [
    "DiagnosticLevel",
    "DiagnosticResult",
    "DiagnosticReport",
    "Doctor",
    "get_doctor",
    "run_diagnostics",
]
