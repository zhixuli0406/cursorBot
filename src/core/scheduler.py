"""
Scheduler System for CursorBot
Inspired by Clawd Bot's cron and automation features

Provides:
- Cron-style job scheduling
- One-time scheduled tasks
- Recurring tasks
- Webhook triggers
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import uuid

from ..utils.logger import logger


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    ONCE = "once"  # Run once at specified time
    INTERVAL = "interval"  # Run at regular intervals
    CRON = "cron"  # Cron-style scheduling (simplified)


@dataclass
class ScheduledJob:
    """Represents a scheduled job."""
    job_id: str
    name: str
    job_type: JobType
    callback: Callable
    callback_args: tuple = field(default_factory=tuple)
    callback_kwargs: dict = field(default_factory=dict)
    user_id: Optional[int] = None
    chat_id: Optional[int] = None

    # Timing
    run_at: Optional[datetime] = None  # For ONCE jobs
    interval_seconds: Optional[int] = None  # For INTERVAL jobs
    cron_expression: Optional[str] = None  # For CRON jobs

    # State
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None = unlimited

    # Results
    last_result: Any = None
    last_error: Optional[str] = None

    @property
    def is_due(self) -> bool:
        """Check if job is due to run."""
        if self.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            return False
        if self.next_run is None:
            return False
        return datetime.now() >= self.next_run

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "type": self.job_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
        }


class Scheduler:
    """
    Job scheduler for automated tasks.

    Usage:
        scheduler = Scheduler()
        await scheduler.start()

        # Schedule a one-time job
        scheduler.schedule_once(
            name="reminder",
            run_at=datetime.now() + timedelta(hours=1),
            callback=send_reminder,
            user_id=12345,
        )

        # Schedule a recurring job
        scheduler.schedule_interval(
            name="health_check",
            interval_seconds=300,
            callback=check_health,
        )
    """

    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def _generate_id(self) -> str:
        """Generate a unique job ID."""
        return uuid.uuid4().hex[:12]

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_run_jobs()
                await asyncio.sleep(1)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)

    async def _check_and_run_jobs(self) -> None:
        """Check and run due jobs."""
        due_jobs = [j for j in self._jobs.values() if j.is_due]

        for job in due_jobs:
            await self._run_job(job)

    async def _run_job(self, job: ScheduledJob) -> None:
        """Run a single job."""
        job.status = JobStatus.RUNNING
        job.last_run = datetime.now()

        try:
            if asyncio.iscoroutinefunction(job.callback):
                result = await job.callback(*job.callback_args, **job.callback_kwargs)
            else:
                result = job.callback(*job.callback_args, **job.callback_kwargs)

            job.last_result = result
            job.last_error = None
            job.run_count += 1

            logger.debug(f"Job {job.job_id} ({job.name}) completed")

        except Exception as e:
            job.last_error = str(e)
            job.run_count += 1
            logger.error(f"Job {job.job_id} ({job.name}) failed: {e}")

        # Update status and next run
        self._update_job_schedule(job)

    def _update_job_schedule(self, job: ScheduledJob) -> None:
        """Update job status and schedule next run."""
        # Check if max runs reached
        if job.max_runs and job.run_count >= job.max_runs:
            job.status = JobStatus.COMPLETED
            job.next_run = None
            return

        if job.job_type == JobType.ONCE:
            job.status = JobStatus.COMPLETED
            job.next_run = None

        elif job.job_type == JobType.INTERVAL:
            job.status = JobStatus.PENDING
            job.next_run = datetime.now() + timedelta(seconds=job.interval_seconds)

        elif job.job_type == JobType.CRON:
            job.status = JobStatus.PENDING
            job.next_run = self._calculate_next_cron_run(job.cron_expression)

    def _calculate_next_cron_run(self, expression: str) -> datetime:
        """
        Calculate next run time from simplified cron expression.

        Simplified format: "minute hour" or "every Xm/Xh"
        Examples:
            "30 14" = 14:30 daily
            "every 30m" = every 30 minutes
            "every 2h" = every 2 hours
        """
        import re

        # Handle "every Xm/Xh" format
        match = re.match(r"every (\d+)([mh])", expression)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit == 'm':
                return datetime.now() + timedelta(minutes=amount)
            else:
                return datetime.now() + timedelta(hours=amount)

        # Handle "minute hour" format
        parts = expression.split()
        if len(parts) >= 2:
            minute = int(parts[0])
            hour = int(parts[1])

            now = datetime.now()
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if next_run <= now:
                next_run += timedelta(days=1)

            return next_run

        # Default: run in 1 hour
        return datetime.now() + timedelta(hours=1)

    def schedule_once(
        self,
        name: str,
        run_at: datetime,
        callback: Callable,
        callback_args: tuple = (),
        callback_kwargs: dict = None,
        user_id: int = None,
        chat_id: int = None,
    ) -> ScheduledJob:
        """
        Schedule a one-time job.

        Args:
            name: Job name
            run_at: When to run
            callback: Function to call
            callback_args: Args for callback
            callback_kwargs: Kwargs for callback
            user_id: Associated user ID
            chat_id: Associated chat ID

        Returns:
            ScheduledJob instance
        """
        job = ScheduledJob(
            job_id=self._generate_id(),
            name=name,
            job_type=JobType.ONCE,
            callback=callback,
            callback_args=callback_args,
            callback_kwargs=callback_kwargs or {},
            user_id=user_id,
            chat_id=chat_id,
            run_at=run_at,
            next_run=run_at,
        )

        self._jobs[job.job_id] = job
        logger.info(f"Scheduled one-time job: {name} at {run_at}")
        return job

    def schedule_interval(
        self,
        name: str,
        interval_seconds: int,
        callback: Callable,
        callback_args: tuple = (),
        callback_kwargs: dict = None,
        user_id: int = None,
        chat_id: int = None,
        start_immediately: bool = False,
        max_runs: int = None,
    ) -> ScheduledJob:
        """
        Schedule a recurring interval job.

        Args:
            name: Job name
            interval_seconds: Seconds between runs
            callback: Function to call
            start_immediately: Run immediately, then on interval
            max_runs: Maximum number of runs (None = unlimited)

        Returns:
            ScheduledJob instance
        """
        first_run = datetime.now() if start_immediately else datetime.now() + timedelta(seconds=interval_seconds)

        job = ScheduledJob(
            job_id=self._generate_id(),
            name=name,
            job_type=JobType.INTERVAL,
            callback=callback,
            callback_args=callback_args,
            callback_kwargs=callback_kwargs or {},
            user_id=user_id,
            chat_id=chat_id,
            interval_seconds=interval_seconds,
            next_run=first_run,
            max_runs=max_runs,
        )

        self._jobs[job.job_id] = job
        logger.info(f"Scheduled interval job: {name} every {interval_seconds}s")
        return job

    def schedule_cron(
        self,
        name: str,
        cron_expression: str,
        callback: Callable,
        callback_args: tuple = (),
        callback_kwargs: dict = None,
        user_id: int = None,
        chat_id: int = None,
    ) -> ScheduledJob:
        """
        Schedule a cron-style job.

        Args:
            name: Job name
            cron_expression: Simplified cron expression
            callback: Function to call

        Returns:
            ScheduledJob instance
        """
        next_run = self._calculate_next_cron_run(cron_expression)

        job = ScheduledJob(
            job_id=self._generate_id(),
            name=name,
            job_type=JobType.CRON,
            callback=callback,
            callback_args=callback_args,
            callback_kwargs=callback_kwargs or {},
            user_id=user_id,
            chat_id=chat_id,
            cron_expression=cron_expression,
            next_run=next_run,
        )

        self._jobs[job.job_id] = job
        logger.info(f"Scheduled cron job: {name} ({cron_expression})")
        return job

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.CANCELLED
            job.next_run = None
            logger.info(f"Cancelled job: {job_id}")
            return True
        return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self, user_id: int = None) -> list[ScheduledJob]:
        """List all jobs, optionally filtered by user."""
        jobs = list(self._jobs.values())
        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]
        return jobs

    def list_pending_jobs(self) -> list[ScheduledJob]:
        """List all pending jobs."""
        return [j for j in self._jobs.values() if j.status == JobStatus.PENDING]

    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        jobs = list(self._jobs.values())
        return {
            "total_jobs": len(jobs),
            "pending": len([j for j in jobs if j.status == JobStatus.PENDING]),
            "running": len([j for j in jobs if j.status == JobStatus.RUNNING]),
            "completed": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            "failed": len([j for j in jobs if j.last_error]),
            "scheduler_running": self._running,
        }


# Global instance
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """Get the global Scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


__all__ = [
    "Scheduler",
    "ScheduledJob",
    "JobStatus",
    "JobType",
    "get_scheduler",
]
