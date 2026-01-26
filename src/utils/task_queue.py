"""
Task queue and multi-user management for CursorBot
Provides job scheduling, queuing, and user isolation
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Optional
from uuid import uuid4

from .logger import logger


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskStatus(Enum):
    """Task status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class Task:
    """Represents a queued task."""

    id: str
    user_id: int
    name: str
    func: Callable[..., Coroutine]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    timeout: int = 300  # 5 minutes default

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority for queue ordering."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at

    @property
    def duration_ms(self) -> Optional[int]:
        """Get task duration in milliseconds."""
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds() * 1000)
        return None

    def to_dict(self) -> dict:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "priority": self.priority.name,
            "status": self.status.value,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
        }


@dataclass
class UserContext:
    """User-specific context and limits."""

    user_id: int
    username: Optional[str] = None
    max_concurrent_tasks: int = 3
    max_queued_tasks: int = 10
    task_timeout: int = 300
    rate_limit_per_minute: int = 30
    _request_times: list = field(default_factory=list)
    _active_tasks: int = 0

    def can_submit_task(self) -> tuple[bool, str]:
        """
        Check if user can submit a new task.

        Returns:
            Tuple of (allowed, reason)
        """
        # Check rate limit
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 60]

        if len(self._request_times) >= self.rate_limit_per_minute:
            return False, f"Rate limit exceeded ({self.rate_limit_per_minute}/min)"

        return True, ""

    def record_request(self) -> None:
        """Record a request for rate limiting."""
        self._request_times.append(time.time())


class TaskQueue:
    """
    Priority task queue with multi-user support.
    Manages task scheduling and execution.
    """

    def __init__(
        self,
        max_workers: int = 5,
        max_queue_size: int = 100,
    ):
        """
        Initialize task queue.

        Args:
            max_workers: Maximum concurrent workers
            max_queue_size: Maximum queue size
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size

        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._tasks: dict[str, Task] = {}
        self._user_contexts: dict[int, UserContext] = {}
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._task_callbacks: list[Callable] = []

    def get_user_context(self, user_id: int) -> UserContext:
        """Get or create user context."""
        if user_id not in self._user_contexts:
            self._user_contexts[user_id] = UserContext(user_id=user_id)
        return self._user_contexts[user_id]

    def set_user_limits(
        self,
        user_id: int,
        max_concurrent: Optional[int] = None,
        max_queued: Optional[int] = None,
        timeout: Optional[int] = None,
        rate_limit: Optional[int] = None,
    ) -> None:
        """
        Set limits for a specific user.

        Args:
            user_id: User ID
            max_concurrent: Maximum concurrent tasks
            max_queued: Maximum queued tasks
            timeout: Task timeout in seconds
            rate_limit: Requests per minute limit
        """
        ctx = self.get_user_context(user_id)

        if max_concurrent is not None:
            ctx.max_concurrent_tasks = max_concurrent
        if max_queued is not None:
            ctx.max_queued_tasks = max_queued
        if timeout is not None:
            ctx.task_timeout = timeout
        if rate_limit is not None:
            ctx.rate_limit_per_minute = rate_limit

    async def submit(
        self,
        user_id: int,
        name: str,
        func: Callable[..., Coroutine],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[int] = None,
    ) -> Task:
        """
        Submit a task to the queue.

        Args:
            user_id: User ID submitting the task
            name: Task name for display
            func: Async function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            priority: Task priority
            timeout: Task timeout override

        Returns:
            Created Task object

        Raises:
            ValueError: If queue is full or user limits exceeded
        """
        ctx = self.get_user_context(user_id)

        # Check user limits
        can_submit, reason = ctx.can_submit_task()
        if not can_submit:
            raise ValueError(reason)

        # Check queue capacity
        if self._queue.qsize() >= self.max_queue_size:
            raise ValueError("Task queue is full")

        # Count user's queued tasks
        user_queued = sum(
            1
            for t in self._tasks.values()
            if t.user_id == user_id and t.status in (TaskStatus.PENDING, TaskStatus.QUEUED)
        )
        if user_queued >= ctx.max_queued_tasks:
            raise ValueError(f"User queue limit reached ({ctx.max_queued_tasks})")

        # Create task
        task = Task(
            id=str(uuid4())[:8],
            user_id=user_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            timeout=timeout or ctx.task_timeout,
        )

        # Add to tracking and queue
        self._tasks[task.id] = task
        task.status = TaskStatus.QUEUED
        await self._queue.put((task.priority.value * -1, task.created_at, task))

        ctx.record_request()

        logger.info(f"Task queued: {task.id} ({name}) by user {user_id}")

        # Notify callbacks
        await self._notify_callbacks(task, "queued")

        return task

    async def start(self) -> None:
        """Start the task queue workers."""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting task queue with {self.max_workers} workers")

        # Create worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

    async def stop(self) -> None:
        """Stop the task queue."""
        self._running = False

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        logger.info("Task queue stopped")

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes tasks."""
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                # Get task from queue with timeout
                try:
                    _, _, task = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Execute task
                await self._execute_task(task, worker_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.debug(f"Worker {worker_id} stopped")

    async def _execute_task(self, task: Task, worker_id: int) -> None:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        ctx = self.get_user_context(task.user_id)
        ctx._active_tasks += 1

        logger.info(f"Worker {worker_id} executing: {task.id} ({task.name})")

        await self._notify_callbacks(task, "started")

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                task.func(*task.args, **task.kwargs),
                timeout=task.timeout,
            )

            task.result = result
            task.status = TaskStatus.COMPLETED

        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task timed out after {task.timeout}s"
            logger.warning(f"Task timeout: {task.id}")

        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.error = "Task was cancelled"
            logger.info(f"Task cancelled: {task.id}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"Task failed: {task.id} - {e}")

        finally:
            task.finished_at = datetime.now()
            ctx._active_tasks -= 1

            await self._notify_callbacks(task, "finished")

            logger.info(
                f"Task {task.id} finished: {task.status.value} "
                f"({task.duration_ms}ms)"
            )

    def add_callback(self, callback: Callable) -> None:
        """Add callback for task events."""
        self._task_callbacks.append(callback)

    async def _notify_callbacks(self, task: Task, event: str) -> None:
        """Notify callbacks of task event."""
        for callback in self._task_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task, event)
                else:
                    callback(task, event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_user_tasks(
        self,
        user_id: int,
        status: Optional[TaskStatus] = None,
        limit: int = 20,
    ) -> list[Task]:
        """Get tasks for a user."""
        tasks = [
            t
            for t in self._tasks.values()
            if t.user_id == user_id and (status is None or t.status == status)
        ]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    async def cancel_task(self, task_id: str, user_id: int) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID to cancel
            user_id: User requesting cancellation (must own the task)

        Returns:
            True if cancelled
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.user_id != user_id:
            return False

        if task.status not in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING):
            return False

        task.status = TaskStatus.CANCELLED
        task.error = "Cancelled by user"
        task.finished_at = datetime.now()

        logger.info(f"Task cancelled: {task_id}")
        return True

    def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(
                1 for t in self._tasks.values() if t.status == status
            )

        return {
            "queue_size": self._queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "workers": self.max_workers,
            "running": self._running,
            "tasks_by_status": status_counts,
            "total_tasks": len(self._tasks),
        }

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Remove old completed tasks from memory.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of tasks removed
        """
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        removed = 0

        to_remove = [
            task_id
            for task_id, task in self._tasks.items()
            if task.finished_at
            and task.finished_at.timestamp() < cutoff
            and task.status
            in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]

        for task_id in to_remove:
            del self._tasks[task_id]
            removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old tasks")

        return removed


# Global task queue instance
task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get or create the global task queue."""
    global task_queue
    if task_queue is None:
        task_queue = TaskQueue()
    return task_queue


__all__ = [
    "Task",
    "TaskPriority",
    "TaskStatus",
    "UserContext",
    "TaskQueue",
    "get_task_queue",
]
