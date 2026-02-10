"""
Claude Code CLI Task Monitor
Monitors .claude/ directory for task completion and sends notifications
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from ..utils.logger import logger


@dataclass
class ClaudeTask:
    """Claude Code CLI 任務信息"""
    task_id: str
    status: str  # running, completed, failed
    start_time: float
    end_time: Optional[float] = None
    output: str = ""
    error: Optional[str] = None
    user_id: Optional[str] = None
    platform: str = "local"  # local, telegram, discord, etc.
    task_type: str = "cli_task"  # cli_task, interactive_conversation
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """任務執行時長（秒）"""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "output": self.output,
            "error": self.error,
            "user_id": self.user_id,
            "platform": self.platform,
            "task_type": self.task_type,
            "metadata": self.metadata,
        }


class ClaudeDirectoryHandler(FileSystemEventHandler):
    """
    Claude Code CLI 目錄監控處理器
    監聽 .claude/ 目錄中的文件變化
    """

    def __init__(self, monitor: "ClaudeCliMonitor"):
        self.monitor = monitor
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop to schedule coroutines on."""
        self._loop = loop

    def _schedule_async(self, coro):
        """Schedule an async coroutine from the watchdog thread."""
        loop = self._loop
        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            logger.warning("No running event loop, skipping file change handler")

    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return

        if self._is_task_file(event.src_path):
            self._schedule_async(self.monitor.handle_file_change(event.src_path))

    def on_created(self, event):
        """文件創建事件"""
        if event.is_directory:
            return

        if self._is_task_file(event.src_path):
            self._schedule_async(self.monitor.handle_file_change(event.src_path))

    def _is_task_file(self, path: str) -> bool:
        """判斷是否為任務相關文件"""
        path_obj = Path(path)
        # 監控 tasks/, sessions/, output/ 目錄
        if any(
            part in path_obj.parts
            for part in ["tasks", "sessions", "output", "results"]
        ):
            return True
        # 監控 projects/ 目錄下的 .jsonl 互動式對話文件
        if "projects" in path_obj.parts and path_obj.suffix == ".jsonl":
            return True
        return False


class ClaudeCliMonitor:
    """
    Claude Code CLI 任務監控器
    監控本地 Claude Code CLI 任務並在完成時發送通知
    """

    def __init__(
        self,
        claude_dir: Optional[str] = None,
        notification_callback: Optional[Callable] = None,
    ):
        """
        初始化監控器

        Args:
            claude_dir: .claude 目錄路徑，默認為 ~/.claude
            notification_callback: 任務完成時的回調函數
        """
        self.claude_dir = Path(claude_dir or os.path.expanduser("~/.claude"))
        self.notification_callback = notification_callback
        self.tasks: Dict[str, ClaudeTask] = {}
        self.observer: Optional[Observer] = None
        self._running = False

        # 確保目錄存在
        self.claude_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Claude CLI Monitor initialized, watching: {self.claude_dir}")

    async def start(self):
        """啟動監控"""
        if self._running:
            logger.warning("Claude CLI Monitor already running")
            return

        self._running = True
        logger.info("Starting Claude CLI Monitor...")

        # 設置文件系統監控
        event_handler = ClaudeDirectoryHandler(self)
        event_handler.set_event_loop(asyncio.get_running_loop())
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.claude_dir), recursive=True)
        self.observer.start()

        # 掃描現有任務
        await self._scan_existing_tasks()

        # 啟動互動式對話閒置檢測
        self._idle_check_task = asyncio.create_task(self._check_conversation_idle())

        logger.info("Claude CLI Monitor started successfully")

    async def stop(self):
        """停止監控"""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping Claude CLI Monitor...")

        # 取消閒置檢測任務
        if hasattr(self, "_idle_check_task") and self._idle_check_task:
            self._idle_check_task.cancel()
            try:
                await self._idle_check_task
            except asyncio.CancelledError:
                pass

        if self.observer:
            self.observer.stop()
            self.observer.join()

        logger.info("Claude CLI Monitor stopped")

    async def handle_file_change(self, file_path: str):
        """
        處理文件變化事件

        Args:
            file_path: 變化的文件路徑
        """
        try:
            path = Path(file_path)

            # 讀取文件內容
            if not path.exists() or not path.is_file():
                return

            # 根據文件類型處理
            if path.name.endswith(".jsonl") and "projects" in path.parts:
                await self._handle_conversation_file(path)
            elif path.name.endswith(".json"):
                await self._handle_json_file(path)
            elif path.name.endswith(".log"):
                await self._handle_log_file(path)
            elif path.name.endswith(".txt") or path.name.endswith(".md"):
                await self._handle_output_file(path)

        except Exception as e:
            logger.error(f"Error handling file change {file_path}: {e}")

    async def _handle_json_file(self, path: Path):
        """處理 JSON 狀態文件"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 提取任務信息
            task_id = data.get("id") or data.get("task_id") or path.stem
            status = data.get("status", "unknown")

            if status in ["completed", "failed", "done", "error"]:
                # 任務完成
                task = self.tasks.get(task_id)
                if task and task.status == "running":
                    # 更新任務狀態
                    task.status = "completed" if status in ["completed", "done"] else "failed"
                    task.end_time = time.time()
                    task.output = data.get("output", "")
                    task.error = data.get("error")
                    task.metadata.update(data.get("metadata", {}))

                    # 發送通知
                    await self._send_notification(task)

                elif not task:
                    # 新任務完成（之前未跟踪）
                    task = ClaudeTask(
                        task_id=task_id,
                        status=task.status if status in ["completed", "done"] else "failed",
                        start_time=data.get("start_time", time.time() - 60),
                        end_time=time.time(),
                        output=data.get("output", ""),
                        error=data.get("error"),
                        metadata=data.get("metadata", {}),
                    )
                    self.tasks[task_id] = task
                    await self._send_notification(task)

        except json.JSONDecodeError:
            logger.debug(f"Invalid JSON file: {path}")
        except Exception as e:
            logger.error(f"Error handling JSON file {path}: {e}")

    async def _handle_log_file(self, path: Path):
        """處理日誌文件"""
        try:
            # 檢查是否有任務完成標記
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 查找完成標記
            for line in reversed(lines[-50:]):  # 只檢查最後50行
                if any(
                    marker in line.lower()
                    for marker in [
                        "completed",
                        "finished",
                        "done",
                        "success",
                        "task complete",
                    ]
                ):
                    # 提取任務ID
                    task_id = path.stem
                    task = self.tasks.get(task_id)

                    if task and task.status == "running":
                        task.status = "completed"
                        task.end_time = time.time()
                        task.output = "".join(lines[-10:])  # 最後10行作為輸出
                        await self._send_notification(task)
                    break

        except Exception as e:
            logger.error(f"Error handling log file {path}: {e}")

    async def _handle_output_file(self, path: Path):
        """處理輸出文件"""
        try:
            # 檢查文件是否最近修改（5秒內）
            mtime = path.stat().st_mtime
            if time.time() - mtime > 5:
                return

            # 讀取輸出
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # 嘗試關聯到任務
            task_id = path.stem
            task = self.tasks.get(task_id)

            if task and task.status == "running":
                task.output = content
                # 不立即發送通知，等待明確的完成信號

        except Exception as e:
            logger.error(f"Error handling output file {path}: {e}")

    async def _handle_conversation_file(self, path: Path):
        """
        處理互動式對話 JSONL 文件
        監控 ~/.claude/projects/<project>/<session-id>.jsonl
        """
        try:
            session_id = path.stem
            now = time.time()

            # Parse the JSONL to extract conversation metadata
            project_name = ""
            first_user_message = ""
            message_count = 0
            last_timestamp = ""
            cwd = ""
            version = ""

            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entry_type = entry.get("type", "")

                        if entry_type in ("user", "assistant"):
                            message_count += 1

                        if entry_type == "user":
                            if not cwd:
                                cwd = entry.get("cwd", "")
                            if not version:
                                version = entry.get("version", "")
                            if not first_user_message:
                                msg = entry.get("message", {})
                                content = msg.get("content", "")
                                if isinstance(content, list):
                                    for c in content:
                                        if isinstance(c, dict) and c.get("type") == "text":
                                            first_user_message = c.get("text", "")[:100]
                                            break
                                elif isinstance(content, str):
                                    first_user_message = content[:100]
                            last_timestamp = entry.get("timestamp", last_timestamp)

                        elif entry_type == "assistant":
                            last_timestamp = entry.get("timestamp", last_timestamp)

                    except json.JSONDecodeError:
                        continue

            # Extract project name from parent directory
            if path.parent.name != "projects":
                project_name = path.parent.name.replace("-", "/").lstrip("/")

            # Check if this conversation is already tracked
            existing_task = self.tasks.get(session_id)

            if existing_task:
                # Update the existing conversation tracking
                existing_task.metadata["message_count"] = message_count
                existing_task.metadata["last_activity"] = now
                existing_task.metadata["last_timestamp"] = last_timestamp
                # Reset idle timer since there's new activity
                return

            # Register a new interactive conversation
            task = ClaudeTask(
                task_id=session_id,
                status="running",
                start_time=now,
                user_id=None,
                platform="local",
                task_type="interactive_conversation",
                metadata={
                    "project": project_name,
                    "cwd": cwd,
                    "first_message": first_user_message,
                    "message_count": message_count,
                    "version": version,
                    "last_activity": now,
                    "last_timestamp": last_timestamp,
                    "jsonl_path": str(path),
                },
            )
            self.tasks[session_id] = task
            logger.info(
                f"Tracking interactive conversation: {session_id} "
                f"(project: {project_name}, messages: {message_count})"
            )

        except Exception as e:
            logger.error(f"Error handling conversation file {path}: {e}")

    @staticmethod
    def _is_conversation_still_processing(jsonl_path: str) -> bool:
        """
        Check if the conversation is still being processed by reading
        the last message entry in the JSONL file.

        If the last user/assistant entry is a 'user' message, it means
        Claude hasn't responded yet (still processing).
        """
        try:
            last_type = None
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entry_type = entry.get("type", "")
                        if entry_type in ("user", "assistant"):
                            last_type = entry_type
                    except json.JSONDecodeError:
                        continue
            return last_type == "user"
        except OSError:
            return False

    async def _check_conversation_idle(self):
        """
        定期檢查互動式對話是否已閒置（結束）
        如果對話超過指定時間無新活動，且 Claude 不在處理回應中，
        則判定為已結束並發送通知
        """
        idle_timeout = 300  # 5 minutes without activity = conversation ended

        while self._running:
            try:
                now = time.time()
                for task_id, task in list(self.tasks.items()):
                    if (
                        task.task_type != "interactive_conversation"
                        or task.status != "running"
                    ):
                        continue

                    last_activity = task.metadata.get("last_activity", task.start_time)

                    # Also check file modification time as a secondary signal
                    jsonl_path = task.metadata.get("jsonl_path")
                    if jsonl_path:
                        try:
                            file_mtime = Path(jsonl_path).stat().st_mtime
                            last_activity = max(last_activity, file_mtime)
                            task.metadata["last_activity"] = last_activity
                        except OSError:
                            pass

                    if now - last_activity > idle_timeout:
                        # Check 1: Is Claude still processing a response?
                        if jsonl_path and self._is_conversation_still_processing(
                            jsonl_path
                        ):
                            logger.debug(
                                f"Conversation {task_id} idle for "
                                f"{int(now - last_activity)}s but last "
                                f"entry is user message (still processing)"
                            )
                            continue

                        # Conversation is idle and Claude is not processing
                        task.status = "completed"
                        task.end_time = now
                        task.output = (
                            f"對話已結束 (共 {task.metadata.get('message_count', 0)} 則訊息)\n"
                            f"首則訊息: {task.metadata.get('first_message', 'N/A')}"
                        )
                        logger.info(
                            f"Interactive conversation {task_id} ended "
                            f"(idle for {int(now - last_activity)}s)"
                        )
                        await self._send_notification(task)

            except Exception as e:
                logger.error(f"Error checking conversation idle: {e}")

            await asyncio.sleep(60)  # Check every 60 seconds

    async def _scan_existing_tasks(self):
        """掃描現有任務"""
        try:
            # 掃描 tasks 目錄
            tasks_dir = self.claude_dir / "tasks"
            if tasks_dir.exists():
                for task_file in tasks_dir.glob("*.json"):
                    await self._handle_json_file(task_file)

            # 掃描 sessions 目錄
            sessions_dir = self.claude_dir / "sessions"
            if sessions_dir.exists():
                for session_file in sessions_dir.glob("*.json"):
                    await self._handle_json_file(session_file)

            # 掃描 projects 目錄下的互動式對話
            projects_dir = self.claude_dir / "projects"
            if projects_dir.exists():
                for jsonl_file in projects_dir.glob("**/*.jsonl"):
                    # Only track recently active conversations (modified in last 10 min)
                    try:
                        mtime = jsonl_file.stat().st_mtime
                        if time.time() - mtime < 600:
                            await self._handle_conversation_file(jsonl_file)
                    except OSError:
                        continue

            logger.info(f"Scanned existing tasks: {len(self.tasks)} found")

        except Exception as e:
            logger.error(f"Error scanning existing tasks: {e}")

    async def _send_notification(self, task: ClaudeTask):
        """
        發送任務完成通知

        Args:
            task: 完成的任務
        """
        try:
            logger.info(f"Task {task.task_id} completed: {task.status}")

            # 構建通知消息
            message = self._format_notification(task)

            # 調用通知回調
            if self.notification_callback:
                await self.notification_callback(task, message)
            else:
                logger.info(f"Notification: {message}")

        except Exception as e:
            logger.error(f"Error sending notification for task {task.task_id}: {e}")

    def _format_notification(self, task: ClaudeTask) -> str:
        """
        格式化通知消息

        Args:
            task: 任務信息

        Returns:
            格式化的通知消息
        """
        status_emoji = "✅" if task.status == "completed" else "❌"
        duration_str = (
            f"{task.duration:.1f}秒" if task.duration else "未知"
        )

        if task.task_type == "interactive_conversation":
            # Interactive conversation notification format
            project = task.metadata.get("project", "未知專案")
            msg_count = task.metadata.get("message_count", 0)
            first_msg = task.metadata.get("first_message", "")

            message = f"{status_emoji} **Claude Code 互動式對話結束**\n\n"
            message += f"**會話ID**: `{task.task_id[:8]}...`\n"
            message += f"**專案**: `{project}`\n"
            message += f"**訊息數**: {msg_count}\n"
            message += f"**執行時長**: {duration_str}\n"

            if first_msg:
                message += f"\n**首則訊息**: {first_msg}\n"
        else:
            # CLI task notification format
            message = f"{status_emoji} **Claude Code CLI 任務完成**\n\n"
            message += f"**任務ID**: `{task.task_id}`\n"
            message += f"**狀態**: {task.status}\n"
            message += f"**執行時長**: {duration_str}\n"

        if task.output:
            output_preview = task.output[:200]
            if len(task.output) > 200:
                output_preview += "..."
            message += f"\n**輸出**:\n```\n{output_preview}\n```\n"

        if task.error:
            message += f"\n**錯誤**: {task.error}\n"

        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return message

    def register_task(
        self,
        task_id: str,
        user_id: Optional[str] = None,
        platform: str = "local",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        註冊新任務（手動）

        Args:
            task_id: 任務ID
            user_id: 用戶ID
            platform: 平台
            metadata: 元數據
        """
        task = ClaudeTask(
            task_id=task_id,
            status="running",
            start_time=time.time(),
            user_id=user_id,
            platform=platform,
            metadata=metadata or {},
        )
        self.tasks[task_id] = task
        logger.info(f"Registered task: {task_id}")

    def get_task(self, task_id: str) -> Optional[ClaudeTask]:
        """獲取任務信息"""
        return self.tasks.get(task_id)

    def list_tasks(
        self, status: Optional[str] = None, task_type: Optional[str] = None
    ) -> list[ClaudeTask]:
        """
        列出任務

        Args:
            status: 過濾狀態（可選）
            task_type: 過濾類型（可選）: cli_task, interactive_conversation

        Returns:
            任務列表
        """
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        return tasks


# 全局監控器實例
_monitor_instance: Optional[ClaudeCliMonitor] = None


def get_claude_cli_monitor() -> ClaudeCliMonitor:
    """獲取全局監控器實例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ClaudeCliMonitor()
    return _monitor_instance


async def start_claude_cli_monitor(notification_callback: Optional[Callable] = None):
    """啟動 Claude CLI 監控器"""
    monitor = get_claude_cli_monitor()
    if notification_callback:
        monitor.notification_callback = notification_callback
    await monitor.start()


async def stop_claude_cli_monitor():
    """停止 Claude CLI 監控器"""
    monitor = get_claude_cli_monitor()
    await monitor.stop()
