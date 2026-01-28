"""
Health Check & Graceful Shutdown - v0.4 Feature
Application health monitoring and graceful shutdown support.

Endpoints:
    GET /health - Basic health check (for load balancers)
    GET /ready - Readiness check (for Kubernetes)
    GET /health/detail - Detailed health status
"""

import asyncio
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable, Tuple
import json

from ..utils.logger import logger


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentType(Enum):
    """Types of health check components."""
    CORE = "core"
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    PLATFORM = "platform"
    FEATURE = "feature"


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    component_type: ComponentType
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0
    last_check: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.component_type.value,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "last_check": self.last_check.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class HealthReport:
    """Complete health report."""
    status: HealthStatus
    version: str = "0.4.0"
    uptime_seconds: float = 0
    timestamp: datetime = field(default_factory=datetime.now)
    components: List[ComponentHealth] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": self.timestamp.isoformat(),
            "checks": {
                "passed": self.checks_passed,
                "failed": self.checks_failed,
                "total": self.checks_passed + self.checks_failed,
            },
            "components": [c.to_dict() for c in self.components],
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


HealthChecker = Callable[[], Awaitable[ComponentHealth]]


class HealthManager:
    """
    Manager for health checks and graceful shutdown.
    
    Usage:
        health = get_health_manager()
        
        # Register health check
        @health.register_check("database", ComponentType.DATABASE)
        async def check_database():
            return ComponentHealth(
                name="database",
                component_type=ComponentType.DATABASE,
                status=HealthStatus.HEALTHY,
            )
        
        # Run health check
        report = await health.check()
        
        # Graceful shutdown
        health.register_shutdown_handler(cleanup_func)
        await health.shutdown()
    """
    
    _instance: Optional["HealthManager"] = None
    
    def __init__(self):
        self._start_time = time.time()
        self._checks: Dict[str, HealthChecker] = {}
        self._shutdown_handlers: List[Callable] = []
        self._is_shutting_down = False
        self._is_ready = False
        self._version = "0.4.0"
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        try:
            # Only setup signals if running in main thread
            if asyncio.get_event_loop().is_running():
                loop = asyncio.get_event_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(sig, self._handle_shutdown_signal)
            else:
                signal.signal(signal.SIGTERM, self._handle_shutdown_signal_sync)
                signal.signal(signal.SIGINT, self._handle_shutdown_signal_sync)
        except Exception as e:
            logger.warning(f"Could not setup signal handlers: {e}")
    
    def _handle_shutdown_signal(self):
        """Handle shutdown signal (async context)."""
        logger.info("Received shutdown signal")
        asyncio.create_task(self.shutdown())
    
    def _handle_shutdown_signal_sync(self, signum, frame):
        """Handle shutdown signal (sync context)."""
        logger.info(f"Received signal {signum}")
        self._is_shutting_down = True
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._is_shutting_down
    
    @property
    def uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self._start_time
    
    def set_ready(self, ready: bool = True):
        """Mark application as ready to receive traffic."""
        self._is_ready = ready
        logger.info(f"Application ready: {ready}")
    
    def is_ready(self) -> bool:
        """Check if application is ready."""
        return self._is_ready and not self._is_shutting_down
    
    def register_check(
        self,
        name: str,
        component_type: ComponentType = ComponentType.CORE,
    ):
        """
        Decorator to register a health check function.
        
        Usage:
            @health.register_check("database", ComponentType.DATABASE)
            async def check_database():
                ...
        """
        def decorator(func: HealthChecker):
            self._checks[name] = func
            return func
        return decorator
    
    def add_check(self, name: str, checker: HealthChecker):
        """Add a health check function."""
        self._checks[name] = checker
    
    def remove_check(self, name: str):
        """Remove a health check."""
        self._checks.pop(name, None)
    
    def register_shutdown_handler(self, handler: Callable):
        """
        Register a function to be called during shutdown.
        
        Handlers are called in reverse order of registration (LIFO).
        """
        self._shutdown_handlers.append(handler)
    
    async def check(
        self,
        include_components: bool = True,
        timeout: float = 10.0,
    ) -> HealthReport:
        """
        Run all health checks and return a report.
        
        Args:
            include_components: Include individual component checks
            timeout: Timeout for all checks combined
        """
        report = HealthReport(
            status=HealthStatus.HEALTHY,
            version=self._version,
            uptime_seconds=self.uptime,
            timestamp=datetime.now(),
        )
        
        if self._is_shutting_down:
            report.status = HealthStatus.UNHEALTHY
            return report
        
        if not include_components:
            return report
        
        # Run all checks with timeout
        try:
            async with asyncio.timeout(timeout):
                for name, checker in self._checks.items():
                    try:
                        start = time.time()
                        result = await checker()
                        result.latency_ms = (time.time() - start) * 1000
                        result.last_check = datetime.now()
                        report.components.append(result)
                        
                        if result.status == HealthStatus.HEALTHY:
                            report.checks_passed += 1
                        else:
                            report.checks_failed += 1
                            
                    except Exception as e:
                        report.components.append(ComponentHealth(
                            name=name,
                            component_type=ComponentType.CORE,
                            status=HealthStatus.UNHEALTHY,
                            message=str(e)[:100],
                        ))
                        report.checks_failed += 1
                        
        except asyncio.TimeoutError:
            report.status = HealthStatus.DEGRADED
            logger.warning(f"Health check timed out after {timeout}s")
        
        # Determine overall status
        if report.checks_failed > 0:
            # If more than half failed, unhealthy
            total = report.checks_passed + report.checks_failed
            if report.checks_failed > total / 2:
                report.status = HealthStatus.UNHEALTHY
            else:
                report.status = HealthStatus.DEGRADED
        
        return report
    
    async def check_basic(self) -> Tuple[bool, str]:
        """
        Quick basic health check for load balancers.
        
        Returns:
            Tuple of (is_healthy, status_message)
        """
        if self._is_shutting_down:
            return False, "shutting_down"
        
        if not self._is_ready:
            return False, "not_ready"
        
        return True, "ok"
    
    async def check_readiness(self) -> Tuple[bool, str]:
        """
        Readiness check for Kubernetes.
        
        Returns:
            Tuple of (is_ready, status_message)
        """
        if self._is_shutting_down:
            return False, "shutting_down"
        
        if not self._is_ready:
            return False, "not_ready"
        
        # Run quick component checks
        report = await self.check(include_components=True, timeout=5.0)
        
        if report.status == HealthStatus.UNHEALTHY:
            return False, f"unhealthy ({report.checks_failed} failed)"
        
        return True, "ready"
    
    async def shutdown(self, timeout: float = 30.0):
        """
        Perform graceful shutdown.
        
        Args:
            timeout: Maximum time to wait for shutdown handlers
        """
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        self._is_ready = False
        logger.info("Starting graceful shutdown...")
        
        # Call shutdown handlers in reverse order
        for handler in reversed(self._shutdown_handlers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await asyncio.wait_for(handler(), timeout=timeout)
                else:
                    handler()
            except asyncio.TimeoutError:
                logger.warning(f"Shutdown handler {handler.__name__} timed out")
            except Exception as e:
                logger.error(f"Shutdown handler {handler.__name__} failed: {e}")
        
        logger.info("Graceful shutdown complete")
    
    def get_status_message(self) -> str:
        """Get formatted status message."""
        status = "Healthy" if self._is_ready else "Not Ready"
        if self._is_shutting_down:
            status = "Shutting Down"
        
        uptime = self.uptime
        if uptime < 60:
            uptime_str = f"{uptime:.0f}s"
        elif uptime < 3600:
            uptime_str = f"{uptime/60:.1f}m"
        elif uptime < 86400:
            uptime_str = f"{uptime/3600:.1f}h"
        else:
            uptime_str = f"{uptime/86400:.1f}d"
        
        lines = [
            "💚 **Health Status**",
            "",
            f"Status: {status}",
            f"Version: {self._version}",
            f"Uptime: {uptime_str}",
            f"Checks: {len(self._checks)} registered",
            "",
            "**Endpoints:**",
            "GET /health - Basic check",
            "GET /ready - Readiness check",
            "GET /health/detail - Detailed status",
        ]
        
        return "\n".join(lines)


# Singleton instance
_health_manager: Optional[HealthManager] = None


def get_health_manager() -> HealthManager:
    """Get the global health manager instance."""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthManager()
    return _health_manager


def reset_health_manager():
    """Reset the health manager (for testing)."""
    global _health_manager
    _health_manager = None


# Default health checks
async def check_memory() -> ComponentHealth:
    """Check memory usage."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        percent = memory.percent
        
        status = HealthStatus.HEALTHY
        if percent > 90:
            status = HealthStatus.UNHEALTHY
        elif percent > 80:
            status = HealthStatus.DEGRADED
        
        return ComponentHealth(
            name="memory",
            component_type=ComponentType.CORE,
            status=status,
            message=f"{percent}% used",
            metadata={"percent": percent},
        )
    except ImportError:
        return ComponentHealth(
            name="memory",
            component_type=ComponentType.CORE,
            status=HealthStatus.HEALTHY,
            message="psutil not available",
        )


async def check_disk() -> ComponentHealth:
    """Check disk usage."""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        percent = disk.percent
        
        status = HealthStatus.HEALTHY
        if percent > 95:
            status = HealthStatus.UNHEALTHY
        elif percent > 85:
            status = HealthStatus.DEGRADED
        
        return ComponentHealth(
            name="disk",
            component_type=ComponentType.CORE,
            status=status,
            message=f"{percent}% used",
            metadata={"percent": percent},
        )
    except ImportError:
        return ComponentHealth(
            name="disk",
            component_type=ComponentType.CORE,
            status=HealthStatus.HEALTHY,
            message="psutil not available",
        )


def register_default_checks(health: HealthManager):
    """Register default health checks."""
    health.add_check("memory", check_memory)
    health.add_check("disk", check_disk)


__all__ = [
    "HealthStatus",
    "ComponentType",
    "ComponentHealth",
    "HealthReport",
    "HealthManager",
    "get_health_manager",
    "reset_health_manager",
    "register_default_checks",
]
