"""
Async Task Manager for CursorBot

Provides non-blocking task execution with push notifications.
Agent and CLI tasks run in background and push results when complete.

Features:
- Background task execution
- Progress tracking
- Push notifications on completion
- Task cancellation
- Timeout handling
- SSE streaming support

Usage:
    from src.core.async_tasks import get_task_manager, TaskType
    
    manager = get_task_manager()
    
    # Submit background task
    task_id = await manager.submit_agent_task(
        user_id="123",
        chat_id="456",
        platform="telegram",
        prompt="Help me write a function",
        on_complete=my_callback,
    )
    
    # Check status
    status = manager.get_task_status(task_id)
    
    # Cancel if needed
    await manager.cancel_task(task_id)
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Union
import traceback

from ..utils.logger import logger


# ============================================
# Task Types and Status
# ============================================

class TaskType(Enum):
    """Types of async tasks."""
    AGENT = "agent"
    CLI = "cli"
    RAG = "rag"
    WORKFLOW = "workflow"
    LLM = "llm"
    CUSTOM = "custom"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskProgress:
    """Progress information for a task."""
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    percentage: float = 0.0
    message: str = ""


@dataclass
class AsyncTask:
    """Represents an async background task."""
    id: str
    type: TaskType
    user_id: str
    chat_id: str
    platform: str
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    
    # Input/Output
    input_data: dict = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout: float = 300.0  # 5 minutes default
    
    # Callbacks
    on_complete: Optional[Callable] = None
    on_progress: Optional[Callable] = None
    on_error: Optional[Callable] = None
    
    # Internal
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _cancelled: bool = field(default=False, repr=False)
    
    @property
    def duration_seconds(self) -> float:
        """Get task duration in seconds."""
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            return (end_time - self.started_at).total_seconds()
        return 0.0
    
    @property
    def is_active(self) -> bool:
        """Check if task is still active."""
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "platform": self.platform,
            "status": self.status.value,
            "progress": {
                "current_step": self.progress.current_step,
                "percentage": self.progress.percentage,
                "message": self.progress.message,
            },
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


# ============================================
# Notification Sender
# ============================================

class NotificationSender:
    """
    Sends push notifications to users when tasks complete.
    Supports multiple platforms (Telegram, Discord, etc.)
    Uses direct API calls for reliability.
    """
    
    def __init__(self):
        self._telegram_bot = None
        self._discord_bot = None
    
    def set_telegram_bot(self, bot) -> None:
        """Set Telegram bot instance."""
        self._telegram_bot = bot
    
    def set_discord_bot(self, bot) -> None:
        """Set Discord bot instance."""
        self._discord_bot = bot
    
    async def send_completion(self, task: AsyncTask) -> bool:
        """Send task completion notification."""
        try:
            logger.info(f"Sending completion notification for task {task.id} to {task.platform}")
            
            if task.platform == "telegram":
                return await self._send_telegram(task)
            elif task.platform == "discord":
                return await self._send_discord(task)
            else:
                # Try gateway for other platforms
                return await self._send_via_gateway(task)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _format_completion_message(self, task: AsyncTask) -> str:
        """Format the completion message with task details."""
        lines = []
        
        if task.status == TaskStatus.COMPLETED:
            lines.append(f"✅ <b>Task Completed</b>")
            lines.append("")
            lines.append(f"<b>ID:</b> <code>{task.id}</code>")
            lines.append(f"<b>Type:</b> {task.type.value}")
            lines.append(f"<b>Duration:</b> {task.duration_seconds:.1f}s")
            lines.append("")
            
            # Add result
            result_text = str(task.result) if task.result else "Task completed"
            # Escape HTML special characters
            result_text = (
                result_text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            if len(result_text) > 3500:
                result_text = result_text[:3500] + "\n\n...(truncated)"
            
            lines.append("<b>Output:</b>")
            lines.append(f"<pre>{result_text}</pre>")
            
        elif task.status == TaskStatus.FAILED:
            lines.append(f"❌ <b>Task Failed</b>")
            lines.append("")
            lines.append(f"<b>ID:</b> <code>{task.id}</code>")
            lines.append(f"<b>Type:</b> {task.type.value}")
            lines.append(f"<b>Duration:</b> {task.duration_seconds:.1f}s")
            lines.append("")
            error_text = task.error or "Unknown error"
            error_text = error_text.replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"<b>Error:</b>\n<pre>{error_text[:500]}</pre>")
            
        elif task.status == TaskStatus.CANCELLED:
            lines.append(f"🚫 <b>Task Cancelled</b>")
            lines.append("")
            lines.append(f"<b>ID:</b> <code>{task.id}</code>")
            
        elif task.status == TaskStatus.TIMEOUT:
            lines.append(f"⏱️ <b>Task Timeout</b>")
            lines.append("")
            lines.append(f"<b>ID:</b> <code>{task.id}</code>")
            lines.append(f"Task exceeded {task.timeout}s limit")
            
        else:
            lines.append(f"Task <code>{task.id}</code> status: {task.status.value}")
        
        return "\n".join(lines)
    
    async def _send_telegram(self, task: AsyncTask) -> bool:
        """Send notification via Telegram using direct API call."""
        from ..utils.config import settings
        
        # Get bot token from settings (loaded from .env)
        bot_token = settings.telegram_bot_token
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set in .env, cannot send notification")
            return False
        
        message = self._format_completion_message(task)
        
        # Try using python-telegram-bot first if available
        try:
            from telegram import Bot
            
            bot = Bot(token=bot_token)
            await bot.send_message(
                chat_id=task.chat_id,
                text=message,
                parse_mode="HTML",
            )
            logger.info(f"Telegram notification sent for task {task.id} via python-telegram-bot")
            return True
            
        except Exception as e:
            logger.warning(f"python-telegram-bot failed: {e}, trying httpx...")
        
        # Fallback to httpx direct API call
        try:
            import httpx
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": task.chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"Telegram notification sent for task {task.id} via httpx")
                    return True
                else:
                    logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Telegram send error (httpx): {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    async def _send_discord(self, task: AsyncTask) -> bool:
        """Send notification via Discord."""
        if not self._discord_bot:
            return await self._send_via_gateway(task)
        
        try:
            channel = self._discord_bot.get_channel(int(task.chat_id))
            if not channel:
                return False
            
            if task.status == TaskStatus.COMPLETED:
                result_text = str(task.result) if task.result else "Task completed"
                if len(result_text) > 1900:
                    result_text = result_text[:1900] + "\n\n...(truncated)"
                message = f"✅ **Task Completed**\n\n{result_text}"
            elif task.status == TaskStatus.FAILED:
                message = f"❌ **Task Failed**\n\nError: {task.error}"
            else:
                message = f"Task status: {task.status.value}"
            
            await channel.send(message)
            return True
        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False
    
    async def _send_via_gateway(self, task: AsyncTask) -> bool:
        """Send notification via unified gateway."""
        try:
            from .gateway import get_gateway, OutgoingMessage, Platform
            gateway = get_gateway()
            
            if task.status == TaskStatus.COMPLETED:
                result_text = str(task.result) if task.result else "Task completed"
                if len(result_text) > 3000:
                    result_text = result_text[:3000] + "\n\n...(truncated)"
                message_text = f"✅ Task Completed\n\n{result_text}"
            elif task.status == TaskStatus.FAILED:
                message_text = f"❌ Task Failed\n\nError: {task.error}"
            elif task.status == TaskStatus.CANCELLED:
                message_text = "🚫 Task Cancelled"
            elif task.status == TaskStatus.TIMEOUT:
                message_text = f"⏱️ Task Timeout (>{task.timeout}s)"
            else:
                message_text = f"Task status: {task.status.value}"
            
            # Convert platform string to Platform enum if needed
            platform = None
            if task.platform:
                try:
                    if isinstance(task.platform, str):
                        platform = Platform(task.platform.lower())
                    elif isinstance(task.platform, Platform):
                        platform = task.platform
                except ValueError:
                    # Unknown platform, send to all
                    platform = None
            
            # Create OutgoingMessage object
            outgoing = OutgoingMessage(
                chat_id=str(task.chat_id),
                content=message_text,
                platform=platform,
            )
            
            await gateway.send_message(outgoing)
            return True
        except Exception as e:
            logger.error(f"Gateway send error: {e}")
            return False
    
    async def send_progress(self, task: AsyncTask) -> bool:
        """Send progress update (optional, for long-running tasks)."""
        # Only send progress updates every 30 seconds or on significant progress
        message = f"⏳ **Task in Progress**\n\n{task.progress.message}"
        if task.progress.percentage > 0:
            message += f"\nProgress: {task.progress.percentage:.0f}%"
        
        try:
            return await self._send_via_gateway(task)
        except:
            return False


# ============================================
# Async Task Manager
# ============================================

class AsyncTaskManager:
    """
    Manages background async tasks.
    Supports Agent, CLI, RAG, and custom tasks.
    """
    
    def __init__(self, max_concurrent: int = 10):
        self._tasks: dict[str, AsyncTask] = {}
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._notifier = NotificationSender()
        
        # Cleanup old tasks periodically
        self._cleanup_interval = 3600  # 1 hour
        self._max_task_age = 86400  # 24 hours
    
    @property
    def notifier(self) -> NotificationSender:
        """Get the notification sender."""
        return self._notifier
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        return str(uuid.uuid4())[:8]
    
    # ============================================
    # Task Submission
    # ============================================
    
    async def submit_agent_task(
        self,
        user_id: str,
        chat_id: str,
        platform: str,
        prompt: str,
        timeout: float = 600.0,  # 10 minutes default for Agent
        on_complete: Callable = None,
        on_progress: Callable = None,
        on_error: Callable = None,
        **kwargs,
    ) -> str:
        """
        Submit an Agent task for background execution.
        
        Args:
            user_id: User identifier
            chat_id: Chat/channel identifier
            platform: Platform (telegram, discord, etc.)
            prompt: Task prompt
            timeout: Timeout in seconds
            on_complete: Callback when complete
            on_progress: Callback for progress updates
            on_error: Callback on error
            **kwargs: Additional arguments for agent
            
        Returns:
            Task ID
        """
        task = AsyncTask(
            id=self._generate_task_id(),
            type=TaskType.AGENT,
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            input_data={"prompt": prompt, **kwargs},
            timeout=timeout,
            on_complete=on_complete,
            on_progress=on_progress,
            on_error=on_error,
        )
        
        self._tasks[task.id] = task
        
        # Start background execution
        task._task = asyncio.create_task(self._execute_agent_task(task))
        
        logger.info(f"Agent task {task.id} submitted for user {user_id}")
        return task.id
    
    async def submit_cli_task(
        self,
        user_id: str,
        chat_id: str,
        platform: str,
        prompt: str,
        working_directory: str = None,
        model: str = None,
        timeout: float = None,  # None = no timeout (use CLI's own timeout setting)
        on_complete: Callable = None,
        on_progress: Callable = None,
        on_error: Callable = None,
        **kwargs,
    ) -> str:
        """
        Submit a CLI task for background execution.
        
        Args:
            user_id: User identifier
            chat_id: Chat/channel identifier
            platform: Platform (telegram, discord, etc.)
            prompt: Task prompt
            working_directory: Working directory for CLI
            model: Model to use
            timeout: Timeout in seconds
            on_complete: Callback when complete
            on_progress: Callback for progress updates
            on_error: Callback on error
            **kwargs: Additional arguments
            
        Returns:
            Task ID
        """
        task = AsyncTask(
            id=self._generate_task_id(),
            type=TaskType.CLI,
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            input_data={
                "prompt": prompt,
                "working_directory": working_directory,
                "model": model,
                **kwargs,
            },
            timeout=timeout,
            on_complete=on_complete,
            on_progress=on_progress,
            on_error=on_error,
        )
        
        self._tasks[task.id] = task
        
        # Start background execution
        task._task = asyncio.create_task(self._execute_cli_task(task))
        
        logger.info(f"CLI task {task.id} submitted for user {user_id}")
        return task.id
    
    async def submit_rag_task(
        self,
        user_id: str,
        chat_id: str,
        platform: str,
        question: str,
        timeout: float = 120.0,
        on_complete: Callable = None,
        **kwargs,
    ) -> str:
        """Submit a RAG query task."""
        task = AsyncTask(
            id=self._generate_task_id(),
            type=TaskType.RAG,
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            input_data={"question": question, **kwargs},
            timeout=timeout,
            on_complete=on_complete,
        )
        
        self._tasks[task.id] = task
        task._task = asyncio.create_task(self._execute_rag_task(task))
        
        logger.info(f"RAG task {task.id} submitted for user {user_id}")
        return task.id
    
    async def submit_custom_task(
        self,
        user_id: str,
        chat_id: str,
        platform: str,
        coroutine: Callable,
        timeout: float = 300.0,
        on_complete: Callable = None,
        **kwargs,
    ) -> str:
        """Submit a custom async task."""
        task = AsyncTask(
            id=self._generate_task_id(),
            type=TaskType.CUSTOM,
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            input_data=kwargs,
            timeout=timeout,
            on_complete=on_complete,
        )
        
        self._tasks[task.id] = task
        task._task = asyncio.create_task(self._execute_custom_task(task, coroutine))
        
        return task.id
    
    # ============================================
    # Task Execution
    # ============================================
    
    async def _execute_agent_task(self, task: AsyncTask) -> None:
        """Execute an Agent task."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.progress.message = "Starting Agent..."
            
            try:
                from .agent_loop import get_agent_loop
                
                agent = get_agent_loop()
                prompt = task.input_data.get("prompt", "")
                
                task.progress.message = "Agent is thinking..."
                
                # Run with timeout
                ctx = await asyncio.wait_for(
                    agent.run(
                        prompt=prompt,
                        user_id=task.user_id,
                        timeout=int(task.timeout),
                    ),
                    timeout=task.timeout,
                )
                
                # Check if cancelled
                if task._cancelled:
                    task.status = TaskStatus.CANCELLED
                    return
                
                # Set result
                task.result = ctx.final_response or "Agent completed without response"
                task.status = TaskStatus.COMPLETED
                task.progress.percentage = 100
                task.progress.message = "Completed"
                
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = f"Task timed out after {task.timeout}s"
                logger.warning(f"Agent task {task.id} timed out")
                
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                logger.info(f"Agent task {task.id} cancelled")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"Agent task {task.id} failed: {e}")
                logger.debug(traceback.format_exc())
            
            finally:
                task.completed_at = datetime.now()
                await self._handle_task_completion(task)
    
    async def _execute_cli_task(self, task: AsyncTask) -> None:
        """Execute a CLI task."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.progress.message = "Starting Cursor CLI..."
            
            try:
                from ..cursor.cli_agent import get_cli_agent
                
                cli = get_cli_agent()
                prompt = task.input_data.get("prompt", "")
                working_dir = task.input_data.get("working_directory")
                model = task.input_data.get("model")
                
                task.progress.message = "CLI is processing..."
                
                # Progress callback
                def on_output(text: str):
                    task.progress.message = text[:100] if text else "Processing..."
                
                # Run CLI directly - CLI has its own timeout handling
                # Don't wrap with asyncio.wait_for to avoid double timeout
                result = await cli.run(
                    prompt=prompt,
                    working_directory=working_dir,
                    model=model,
                    timeout=int(task.timeout) if task.timeout else None,  # Pass timeout to CLI
                    on_output=on_output,
                    user_id=task.user_id,
                )
                
                # Check if cancelled
                if task._cancelled:
                    task.status = TaskStatus.CANCELLED
                    return
                
                # Set result
                if result.success:
                    task.result = result.output or "CLI completed"
                    task.status = TaskStatus.COMPLETED
                else:
                    # Check if it was a timeout
                    if "timed out" in (result.error or "").lower():
                        task.status = TaskStatus.TIMEOUT
                        task.error = result.error
                    else:
                        task.error = result.error or "CLI failed"
                        task.status = TaskStatus.FAILED
                
                task.progress.percentage = 100
                task.progress.message = "Completed"
                
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                logger.info(f"CLI task {task.id} cancelled")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"CLI task {task.id} failed: {e}")
                logger.debug(traceback.format_exc())
            
            finally:
                task.completed_at = datetime.now()
                await self._handle_task_completion(task)
    
    async def _execute_rag_task(self, task: AsyncTask) -> None:
        """Execute a RAG task."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.progress.message = "Searching knowledge base..."
            
            try:
                from .rag import get_rag_manager
                
                rag = get_rag_manager()
                question = task.input_data.get("question", "")
                
                # Run RAG query
                response = await asyncio.wait_for(
                    rag.query(question),
                    timeout=task.timeout,
                )
                
                if task._cancelled:
                    task.status = TaskStatus.CANCELLED
                    return
                
                task.result = response.answer
                task.status = TaskStatus.COMPLETED
                task.progress.percentage = 100
                
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = f"RAG query timed out after {task.timeout}s"
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"RAG task {task.id} failed: {e}")
            
            finally:
                task.completed_at = datetime.now()
                await self._handle_task_completion(task)
    
    async def _execute_custom_task(self, task: AsyncTask, coroutine: Callable) -> None:
        """Execute a custom task."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            try:
                result = await asyncio.wait_for(
                    coroutine(**task.input_data),
                    timeout=task.timeout,
                )
                
                if task._cancelled:
                    task.status = TaskStatus.CANCELLED
                    return
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = f"Task timed out after {task.timeout}s"
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
            
            finally:
                task.completed_at = datetime.now()
                await self._handle_task_completion(task)
    
    async def _handle_task_completion(self, task: AsyncTask) -> None:
        """Handle task completion - send notifications and call callbacks."""
        logger.info(f"Handling completion for task {task.id}, status={task.status.value}")
        
        # Send push notification
        try:
            success = await self._notifier.send_completion(task)
            if success:
                logger.info(f"Notification sent successfully for task {task.id}")
            else:
                logger.warning(f"Failed to send notification for task {task.id}")
        except Exception as e:
            logger.error(f"Exception sending notification for task {task.id}: {e}")
        
        # Call user callbacks
        if task.status == TaskStatus.COMPLETED and task.on_complete:
            try:
                if asyncio.iscoroutinefunction(task.on_complete):
                    await task.on_complete(task)
                else:
                    task.on_complete(task)
            except Exception as e:
                logger.error(f"Task {task.id} on_complete callback error: {e}")
        
        elif task.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT) and task.on_error:
            try:
                if asyncio.iscoroutinefunction(task.on_error):
                    await task.on_error(task)
                else:
                    task.on_error(task)
            except Exception as e:
                logger.error(f"Task {task.id} on_error callback error: {e}")
        
        logger.info(
            f"Task {task.id} ({task.type.value}) completed with status {task.status.value} "
            f"in {task.duration_seconds:.1f}s"
        )
    
    # ============================================
    # Task Management
    # ============================================
    
    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get task status as dictionary."""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None
    
    def get_user_tasks(self, user_id: str, active_only: bool = False) -> list[AsyncTask]:
        """Get all tasks for a user."""
        tasks = [t for t in self._tasks.values() if t.user_id == user_id]
        if active_only:
            tasks = [t for t in tasks if t.is_active]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def get_active_tasks(self) -> list[AsyncTask]:
        """Get all active tasks."""
        return [t for t in self._tasks.values() if t.is_active]
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self._tasks.get(task_id)
        if not task or not task.is_active:
            return False
        
        task._cancelled = True
        
        if task._task and not task._task.done():
            task._task.cancel()
            try:
                await task._task
            except asyncio.CancelledError:
                pass
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        logger.info(f"Task {task_id} cancelled")
        return True
    
    async def cancel_user_tasks(self, user_id: str) -> int:
        """Cancel all active tasks for a user."""
        tasks = self.get_user_tasks(user_id, active_only=True)
        count = 0
        for task in tasks:
            if await self.cancel_task(task.id):
                count += 1
        return count
    
    def cleanup_old_tasks(self, max_age_seconds: int = None) -> int:
        """Remove old completed tasks."""
        max_age = max_age_seconds or self._max_task_age
        cutoff = datetime.now()
        removed = 0
        
        for task_id in list(self._tasks.keys()):
            task = self._tasks[task_id]
            if not task.is_active:
                age = (cutoff - task.completed_at).total_seconds() if task.completed_at else 0
                if age > max_age:
                    del self._tasks[task_id]
                    removed += 1
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} old tasks")
        
        return removed
    
    def get_stats(self) -> dict:
        """Get task manager statistics."""
        tasks = list(self._tasks.values())
        by_status = {}
        by_type = {}
        
        for task in tasks:
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1
            
            task_type = task.type.value
            by_type[task_type] = by_type.get(task_type, 0) + 1
        
        active_tasks = [t for t in tasks if t.is_active]
        avg_duration = 0.0
        if tasks:
            completed = [t for t in tasks if t.completed_at]
            if completed:
                avg_duration = sum(t.duration_seconds for t in completed) / len(completed)
        
        return {
            "total_tasks": len(tasks),
            "active_tasks": len(active_tasks),
            "by_status": by_status,
            "by_type": by_type,
            "avg_duration_seconds": round(avg_duration, 2),
            "max_concurrent": self._max_concurrent,
        }


# ============================================
# Global Instance
# ============================================

_task_manager: Optional[AsyncTaskManager] = None


def get_task_manager(max_concurrent: int = 10) -> AsyncTaskManager:
    """Get the global async task manager instance."""
    global _task_manager
    
    if _task_manager is None:
        _task_manager = AsyncTaskManager(max_concurrent)
        logger.info("Async task manager initialized")
    
    return _task_manager


def reset_task_manager() -> None:
    """Reset the task manager instance."""
    global _task_manager
    _task_manager = None


__all__ = [
    # Types
    "TaskType",
    "TaskStatus",
    "TaskProgress",
    "AsyncTask",
    # Notification
    "NotificationSender",
    # Manager
    "AsyncTaskManager",
    "get_task_manager",
    "reset_task_manager",
]
