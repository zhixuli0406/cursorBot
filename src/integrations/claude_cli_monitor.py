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
            "metadata": self.metadata,
        }


class ClaudeDirectoryHandler(FileSystemEventHandler):
    """
    Claude Code CLI 目錄監控處理器
    監聽 .claude/ 目錄中的文件變化
    """

    def __init__(self, monitor: "ClaudeCliMonitor"):
        self.monitor = monitor

    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return

        if self._is_task_file(event.src_path):
            asyncio.create_task(self.monitor.handle_file_change(event.src_path))

    def on_created(self, event):
        """文件創建事件"""
        if event.is_directory:
            return

        if self._is_task_file(event.src_path):
            asyncio.create_task(self.monitor.handle_file_change(event.src_path))

    def _is_task_file(self, path: str) -> bool:
        """判斷是否為任務相關文件"""
        path_obj = Path(path)
        # 監控 tasks/, sessions/, output/ 目錄
        return any(
            part in path_obj.parts
            for part in ["tasks", "sessions", "output", "results"]
        )


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
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.claude_dir), recursive=True)
        self.observer.start()

        # 掃描現有任務
        await self._scan_existing_tasks()

        logger.info("Claude CLI Monitor started successfully")

    async def stop(self):
        """停止監控"""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping Claude CLI Monitor...")

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
            if path.name.endswith(".json"):
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

    def list_tasks(self, status: Optional[str] = None) -> list[ClaudeTask]:
        """
        列出任務

        Args:
            status: 過濾狀態（可選）

        Returns:
            任務列表
        """
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
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
