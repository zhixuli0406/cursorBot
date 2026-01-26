"""
Heartbeat and Health Monitoring for CursorBot

Provides:
- Service heartbeat mechanism
- Health status tracking
- Auto-recovery on failure
- Retry mechanism with exponential backoff
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Health status for a single service."""
    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    
    def mark_healthy(self, latency_ms: float = None) -> None:
        """Mark service as healthy."""
        self.status = ServiceStatus.HEALTHY
        self.last_check = datetime.now()
        self.last_success = datetime.now()
        self.consecutive_failures = 0
        self.error_message = None
        self.latency_ms = latency_ms
    
    def mark_unhealthy(self, error: str = None) -> None:
        """Mark service as unhealthy."""
        self.status = ServiceStatus.UNHEALTHY
        self.last_check = datetime.now()
        self.consecutive_failures += 1
        self.error_message = error
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "consecutive_failures": self.consecutive_failures,
            "error_message": self.error_message,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat monitoring."""
    interval_seconds: int = 30  # Check interval
    timeout_seconds: int = 10  # Health check timeout
    failure_threshold: int = 3  # Failures before marking unhealthy
    recovery_threshold: int = 2  # Successes before marking healthy
    auto_recover: bool = True  # Attempt auto-recovery
    notify_on_failure: bool = True  # Send notifications on failure


class HeartbeatMonitor:
    """
    Monitors service health with periodic heartbeat checks.
    """
    
    def __init__(self, config: HeartbeatConfig = None):
        self.config = config or HeartbeatConfig()
        self._services: dict[str, ServiceHealth] = {}
        self._health_checks: dict[str, Callable] = {}
        self._recovery_handlers: dict[str, Callable] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: list[Callable] = []
    
    def register_service(
        self,
        name: str,
        health_check: Callable[[], bool],
        recovery_handler: Callable = None,
    ) -> None:
        """
        Register a service for heartbeat monitoring.
        
        Args:
            name: Service identifier
            health_check: Async function that returns True if healthy
            recovery_handler: Optional async function to call on failure
        """
        self._services[name] = ServiceHealth(name=name)
        self._health_checks[name] = health_check
        if recovery_handler:
            self._recovery_handlers[name] = recovery_handler
        logger.info(f"Registered service for heartbeat: {name}")
    
    def unregister_service(self, name: str) -> bool:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            del self._health_checks[name]
            self._recovery_handlers.pop(name, None)
            return True
        return False
    
    def add_callback(self, callback: Callable) -> None:
        """Add callback for status changes."""
        self._callbacks.append(callback)
    
    async def check_service(self, name: str) -> ServiceHealth:
        """Check health of a specific service."""
        if name not in self._services:
            raise ValueError(f"Unknown service: {name}")
        
        health = self._services[name]
        check_func = self._health_checks[name]
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run health check with timeout
            result = await asyncio.wait_for(
                check_func() if asyncio.iscoroutinefunction(check_func) else asyncio.to_thread(check_func),
                timeout=self.config.timeout_seconds
            )
            
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if result:
                health.mark_healthy(latency)
            else:
                health.mark_unhealthy("Health check returned False")
                
        except asyncio.TimeoutError:
            health.mark_unhealthy(f"Health check timed out after {self.config.timeout_seconds}s")
        except Exception as e:
            health.mark_unhealthy(str(e))
        
        # Check if we need to attempt recovery
        if health.status == ServiceStatus.UNHEALTHY:
            if (self.config.auto_recover and 
                name in self._recovery_handlers and
                health.consecutive_failures >= self.config.failure_threshold):
                await self._attempt_recovery(name)
        
        return health
    
    async def _attempt_recovery(self, name: str) -> bool:
        """Attempt to recover a failed service."""
        if name not in self._recovery_handlers:
            return False
        
        logger.warning(f"Attempting recovery for service: {name}")
        
        try:
            recovery_func = self._recovery_handlers[name]
            if asyncio.iscoroutinefunction(recovery_func):
                await recovery_func()
            else:
                await asyncio.to_thread(recovery_func)
            
            logger.info(f"Recovery attempt completed for: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Recovery failed for {name}: {e}")
            return False
    
    async def check_all(self) -> dict[str, ServiceHealth]:
        """Check health of all registered services."""
        for name in self._services:
            await self.check_service(name)
        return self._services.copy()
    
    def get_overall_status(self) -> ServiceStatus:
        """Get overall system health status."""
        if not self._services:
            return ServiceStatus.UNKNOWN
        
        statuses = [s.status for s in self._services.values()]
        
        if all(s == ServiceStatus.HEALTHY for s in statuses):
            return ServiceStatus.HEALTHY
        elif any(s == ServiceStatus.UNHEALTHY for s in statuses):
            return ServiceStatus.UNHEALTHY
        else:
            return ServiceStatus.DEGRADED
    
    async def start(self) -> None:
        """Start the heartbeat monitor."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Heartbeat monitor started")
    
    async def stop(self) -> None:
        """Stop the heartbeat monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat monitor stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                old_statuses = {n: s.status for n, s in self._services.items()}
                
                await self.check_all()
                
                # Notify callbacks on status changes
                for name, health in self._services.items():
                    if name in old_statuses and old_statuses[name] != health.status:
                        await self._notify_status_change(name, health)
                
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
            
            await asyncio.sleep(self.config.interval_seconds)
    
    async def _notify_status_change(self, name: str, health: ServiceHealth) -> None:
        """Notify callbacks of status change."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(name, health)
                else:
                    callback(name, health)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_status_report(self) -> dict:
        """Get a full status report."""
        return {
            "overall_status": self.get_overall_status().value,
            "services": {n: s.to_dict() for n, s in self._services.items()},
            "running": self._running,
            "config": {
                "interval_seconds": self.config.interval_seconds,
                "timeout_seconds": self.config.timeout_seconds,
                "failure_threshold": self.config.failure_threshold,
            }
        }


# ============================================
# Retry Mechanism
# ============================================

@dataclass
class RetryConfig:
    """Configuration for retry mechanism."""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retry_on: tuple = (Exception,)  # Exception types to retry on
    

class RetryHandler:
    """
    Handles retries with exponential backoff.
    """
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry."""
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay
    
    async def execute(
        self,
        func: Callable,
        *args,
        on_retry: Callable = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute (sync or async)
            *args: Positional arguments
            on_retry: Optional callback on each retry
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return await asyncio.to_thread(func, *args, **kwargs)
                    
            except self.config.retry_on as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Retry {attempt + 1}/{self.config.max_retries} "
                        f"after {delay:.2f}s due to: {e}"
                    )
                    
                    if on_retry:
                        try:
                            if asyncio.iscoroutinefunction(on_retry):
                                await on_retry(attempt, e, delay)
                            else:
                                on_retry(attempt, e, delay)
                        except Exception:
                            pass
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_retries + 1} attempts failed")
        
        raise last_exception


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: tuple = (Exception,)
):
    """
    Decorator for adding retry logic to a function.
    
    Usage:
        @with_retry(max_retries=3)
        async def my_function():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        retry_on=retry_on,
    )
    handler = RetryHandler(config)
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await handler.execute(func, *args, **kwargs)
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        return wrapper
    
    return decorator


# ============================================
# Global Instance
# ============================================

_heartbeat_monitor: Optional[HeartbeatMonitor] = None
_retry_handler: Optional[RetryHandler] = None


def get_heartbeat_monitor() -> HeartbeatMonitor:
    """Get the global heartbeat monitor instance."""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor()
    return _heartbeat_monitor


def get_retry_handler(config: RetryConfig = None) -> RetryHandler:
    """Get a retry handler instance."""
    global _retry_handler
    if _retry_handler is None or config:
        _retry_handler = RetryHandler(config)
    return _retry_handler


__all__ = [
    "ServiceStatus",
    "ServiceHealth",
    "HeartbeatConfig",
    "HeartbeatMonitor",
    "RetryConfig",
    "RetryHandler",
    "with_retry",
    "get_heartbeat_monitor",
    "get_retry_handler",
]
