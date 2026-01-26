"""
Task Queue System for CursorBot

Provides:
- Async task queue management
- Priority-based task scheduling
- Task status tracking
- Concurrent execution control
- Rate limiting
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..utils.logger import logger


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """Represents a queued task."""
    id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None  # seconds
    callback: Optional[Callable] = None
    metadata: dict = field(default_factory=dict)
    
    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority (higher priority first)."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "priority": self.priority.name,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retries": self.retries,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class QueueConfig:
    """Configuration for task queue."""
    max_concurrent: int = 5  # Max concurrent tasks
    default_timeout: float = 300.0  # Default task timeout (5 min)
    default_max_retries: int = 3
    retry_delay: float = 1.0  # Base delay between retries
    rate_limit: Optional[float] = None  # Min seconds between task starts
    persist_results: bool = True  # Keep completed task results


class TaskQueue:
    """
    Async task queue with priority scheduling.
    """
    
    def __init__(self, config: QueueConfig = None, name: str = "default"):
        self.config = config or QueueConfig()
        self.name = name
        self._queue: asyncio.PriorityQueue = None
        self._tasks: dict[str, Task] = {}
        self._running_tasks: set[str] = set()
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._semaphore: asyncio.Semaphore = None
        self._last_task_time: float = 0
        self._callbacks: list[Callable] = []
    
    async def start(self) -> None:
        """Start the task queue workers."""
        if self._running:
            return
        
        self._running = True
        self._queue = asyncio.PriorityQueue()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        # Start worker tasks
        for i in range(self.config.max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info(f"Task queue '{self.name}' started with {self.config.max_concurrent} workers")
    
    async def stop(self, wait: bool = True) -> None:
        """
        Stop the task queue.
        
        Args:
            wait: Wait for current tasks to complete
        """
        self._running = False
        
        if wait:
            # Wait for running tasks to complete
            while self._running_tasks:
                await asyncio.sleep(0.1)
        
        # Cancel workers
        for worker in self._workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        
        self._workers.clear()
        logger.info(f"Task queue '{self.name}' stopped")
    
    def add_callback(self, callback: Callable) -> None:
        """Add callback for task completion."""
        self._callbacks.append(callback)
    
    async def submit(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = None,
        max_retries: int = None,
        callback: Callable = None,
        metadata: dict = None,
        **kwargs
    ) -> str:
        """
        Submit a task to the queue.
        
        Args:
            func: Function to execute (sync or async)
            *args: Positional arguments
            priority: Task priority
            timeout: Task timeout in seconds
            max_retries: Max retry attempts
            callback: Callback on completion
            metadata: Additional task metadata
            **kwargs: Keyword arguments
        
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout or self.config.default_timeout,
            max_retries=max_retries if max_retries is not None else self.config.default_max_retries,
            callback=callback,
            metadata=metadata or {},
        )
        
        self._tasks[task_id] = task
        await self._queue.put((task.priority.value * -1, task.created_at, task))
        
        logger.debug(f"Task {task_id} submitted to queue '{self.name}'")
        return task_id
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes tasks."""
        while self._running:
            try:
                # Wait for a task
                try:
                    _, _, task = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Rate limiting
                if self.config.rate_limit:
                    now = asyncio.get_event_loop().time()
                    elapsed = now - self._last_task_time
                    if elapsed < self.config.rate_limit:
                        await asyncio.sleep(self.config.rate_limit - elapsed)
                    self._last_task_time = asyncio.get_event_loop().time()
                
                # Execute task with semaphore
                async with self._semaphore:
                    await self._execute_task(task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._running_tasks.add(task.id)
        
        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(task.func):
                coro = task.func(*task.args, **task.kwargs)
            else:
                coro = asyncio.to_thread(task.func, *task.args, **task.kwargs)
            
            if task.timeout:
                task.result = await asyncio.wait_for(coro, timeout=task.timeout)
            else:
                task.result = await coro
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            logger.debug(f"Task {task.id} completed successfully")
            
        except asyncio.TimeoutError:
            task.error = f"Task timed out after {task.timeout}s"
            await self._handle_task_failure(task)
            
        except Exception as e:
            task.error = str(e)
            await self._handle_task_failure(task)
        
        finally:
            self._running_tasks.discard(task.id)
            
            # Execute callbacks
            await self._notify_completion(task)
            
            # Cleanup if not persisting
            if not self.config.persist_results and task.status == TaskStatus.COMPLETED:
                self._tasks.pop(task.id, None)
    
    async def _handle_task_failure(self, task: Task) -> None:
        """Handle task failure with retry logic."""
        if task.retries < task.max_retries:
            task.retries += 1
            task.status = TaskStatus.RETRYING
            
            # Calculate retry delay with exponential backoff
            delay = self.config.retry_delay * (2 ** (task.retries - 1))
            
            logger.warning(
                f"Task {task.id} failed, retry {task.retries}/{task.max_retries} "
                f"in {delay:.1f}s: {task.error}"
            )
            
            await asyncio.sleep(delay)
            
            # Re-queue the task
            task.status = TaskStatus.PENDING
            task.started_at = None
            await self._queue.put((task.priority.value * -1, task.created_at, task))
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            logger.error(f"Task {task.id} failed after {task.max_retries} retries: {task.error}")
    
    async def _notify_completion(self, task: Task) -> None:
        """Notify callbacks of task completion."""
        # Task-specific callback
        if task.callback:
            try:
                if asyncio.iscoroutinefunction(task.callback):
                    await task.callback(task)
                else:
                    task.callback(task)
            except Exception as e:
                logger.error(f"Task callback error: {e}")
        
        # Global callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Queue callback error: {e}")
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        
        return False
    
    async def wait_for_task(self, task_id: str, timeout: float = None) -> Task:
        """
        Wait for a task to complete.
        
        Args:
            task_id: Task to wait for
            timeout: Max wait time in seconds
        
        Returns:
            Completed task
        
        Raises:
            asyncio.TimeoutError: If timeout exceeded
            ValueError: If task not found
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        start_time = asyncio.get_event_loop().time()
        
        while task.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING):
            if timeout:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise asyncio.TimeoutError(f"Timeout waiting for task {task_id}")
            await asyncio.sleep(0.1)
        
        return task
    
    def get_stats(self) -> dict:
        """Get queue statistics."""
        status_counts = {}
        for task in self._tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "name": self.name,
            "running": self._running,
            "total_tasks": len(self._tasks),
            "queue_size": self._queue.qsize() if self._queue else 0,
            "running_tasks": len(self._running_tasks),
            "worker_count": len(self._workers),
            "status_counts": status_counts,
        }
    
    def get_recent_tasks(self, limit: int = 20) -> list[dict]:
        """Get recent tasks."""
        tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )[:limit]
        
        return [t.to_dict() for t in tasks]


# ============================================
# Global Queue Manager
# ============================================

class QueueManager:
    """Manages multiple task queues."""
    
    def __init__(self):
        self._queues: dict[str, TaskQueue] = {}
    
    def get_queue(self, name: str = "default", config: QueueConfig = None) -> TaskQueue:
        """Get or create a task queue."""
        if name not in self._queues:
            self._queues[name] = TaskQueue(config, name)
        return self._queues[name]
    
    async def start_all(self) -> None:
        """Start all queues."""
        for queue in self._queues.values():
            await queue.start()
    
    async def stop_all(self, wait: bool = True) -> None:
        """Stop all queues."""
        for queue in self._queues.values():
            await queue.stop(wait)
    
    def get_all_stats(self) -> dict:
        """Get stats for all queues."""
        return {name: q.get_stats() for name, q in self._queues.items()}


# ============================================
# Global Instance
# ============================================

_queue_manager: Optional[QueueManager] = None


def get_queue_manager() -> QueueManager:
    """Get the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager


def get_task_queue(name: str = "default", config: QueueConfig = None) -> TaskQueue:
    """Get a task queue by name."""
    return get_queue_manager().get_queue(name, config)


__all__ = [
    "TaskStatus",
    "TaskPriority",
    "Task",
    "QueueConfig",
    "TaskQueue",
    "QueueManager",
    "get_queue_manager",
    "get_task_queue",
]
