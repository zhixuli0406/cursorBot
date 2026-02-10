"""
Claude Code CLI Notification System
將任務完成通知發送到各個平台
"""

import asyncio
from typing import Optional, Dict, Any

from .claude_cli_monitor import ClaudeTask, get_claude_cli_monitor
from ..utils.logger import logger


class ClaudeCliNotifier:
    """
    Claude Code CLI 通知器
    負責將任務完成通知發送到 Telegram, Discord 等平台
    """

    def __init__(self):
        self.telegram_bot = None
        self.discord_bot = None
        self.user_platform_map: Dict[str, str] = {}  # user_id -> platform
        self.user_chat_map: Dict[str, str] = {}  # user_id -> chat_id

    def set_telegram_bot(self, bot):
        """設置 Telegram Bot"""
        self.telegram_bot = bot
        logger.info("Telegram bot registered for Claude CLI notifications")

    def set_discord_bot(self, bot):
        """設置 Discord Bot"""
        self.discord_bot = bot
        logger.info("Discord bot registered for Claude CLI notifications")

    def register_user(self, user_id: str, platform: str, chat_id: str):
        """
        註冊用戶平台信息

        Args:
            user_id: 用戶ID
            platform: 平台 (telegram, discord, etc.)
            chat_id: 聊天ID
        """
        self.user_platform_map[user_id] = platform
        self.user_chat_map[user_id] = chat_id
        logger.info(f"Registered user {user_id} on {platform}")

    async def send_notification(self, task: ClaudeTask, message: str):
        """
        發送任務完成通知

        Args:
            task: 任務信息
            message: 通知消息
        """
        try:
            # 確定目標平台
            platform = task.platform
            user_id = task.user_id

            if user_id and user_id in self.user_platform_map:
                platform = self.user_platform_map[user_id]

            # 根據平台發送通知
            if platform == "telegram" and self.telegram_bot:
                await self._send_telegram_notification(task, message)
            elif platform == "discord" and self.discord_bot:
                await self._send_discord_notification(task, message)
            else:
                logger.info(f"No notification handler for platform: {platform}")

        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    async def _send_telegram_notification(self, task: ClaudeTask, message: str):
        """發送 Telegram 通知"""
        try:
            if not self.telegram_bot:
                return

            chat_id = self.user_chat_map.get(task.user_id)
            if not chat_id:
                logger.warning(f"No chat_id for user {task.user_id}")
                return

            # 發送消息
            await self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
            )
            logger.info(f"Sent Telegram notification to {chat_id}")

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    async def _send_discord_notification(self, task: ClaudeTask, message: str):
        """發送 Discord 通知"""
        try:
            if not self.discord_bot:
                return

            channel_id = self.user_chat_map.get(task.user_id)
            if not channel_id:
                logger.warning(f"No channel_id for user {task.user_id}")
                return

            # 發送消息
            await self.discord_bot.send_message(
                channel_id=channel_id,
                content=message,
            )
            logger.info(f"Sent Discord notification to {channel_id}")

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")


# 全局通知器實例
_notifier_instance: Optional[ClaudeCliNotifier] = None


def get_claude_cli_notifier() -> ClaudeCliNotifier:
    """獲取全局通知器實例"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = ClaudeCliNotifier()
    return _notifier_instance


async def initialize_claude_cli_notifications(telegram_bot=None, discord_bot=None):
    """
    初始化 Claude CLI 通知系統

    Args:
        telegram_bot: Telegram Bot 實例
        discord_bot: Discord Bot 實例
    """
    notifier = get_claude_cli_notifier()

    if telegram_bot:
        notifier.set_telegram_bot(telegram_bot)

    if discord_bot:
        notifier.set_discord_bot(discord_bot)

    # 啟動監控器
    monitor = get_claude_cli_monitor()
    monitor.notification_callback = notifier.send_notification
    await monitor.start()

    logger.info("Claude CLI notification system initialized")
