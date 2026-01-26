"""
Main Telegram Bot class for CursorBot
Handles bot initialization and lifecycle management
"""

import asyncio
from typing import Optional

from telegram import Bot, Update
from telegram.ext import Application, ApplicationBuilder

from ..utils.config import settings
from ..utils.logger import logger
from .handlers import setup_handlers


class CursorTelegramBot:
    """
    Main Telegram Bot manager for remote Cursor Agent control.
    Handles bot lifecycle, message routing, and integration with Cursor Agent.
    """

    def __init__(self):
        """Initialize the bot with configuration."""
        self.token = settings.telegram_bot_token
        self.app: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self._running = False

        if not self.token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required. "
                "Get one from @BotFather on Telegram."
            )

    async def initialize(self) -> None:
        """
        Initialize the bot application and setup handlers.
        Must be called before starting the bot.
        """
        logger.info("Initializing Telegram Bot...")

        # Build application
        self.app = (
            ApplicationBuilder()
            .token(self.token)
            .concurrent_updates(True)
            .build()
        )

        self.bot = self.app.bot

        # Setup command and message handlers
        setup_handlers(self.app)

        # Initialize the application
        await self.app.initialize()

        logger.info("Telegram Bot initialized successfully")

    async def start(self) -> None:
        """
        Start the bot and begin polling for updates.
        This method blocks until stop() is called.
        """
        if self.app is None:
            await self.initialize()

        logger.info("Starting Telegram Bot polling...")
        self._running = True

        try:
            await self.app.start()
            await self.app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )

            # Get bot info
            bot_info = await self.bot.get_me()
            logger.info(
                f"Bot started: @{bot_info.username} (ID: {bot_info.id})"
            )

            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in bot polling: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the bot gracefully."""
        logger.info("Stopping Telegram Bot...")
        self._running = False

        if self.app:
            if self.app.updater.running:
                await self.app.updater.stop()
            if self.app.running:
                await self.app.stop()
            await self.app.shutdown()

        logger.info("Telegram Bot stopped")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        **kwargs,
    ) -> None:
        """
        Send a message to a specific chat.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Message parse mode (HTML, Markdown, etc.)
            **kwargs: Additional arguments for send_message
        """
        if self.bot is None:
            logger.error("Bot not initialized")
            return

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def broadcast(self, text: str, parse_mode: str = "HTML") -> None:
        """
        Send a message to all authorized users.

        Args:
            text: Message text
            parse_mode: Message parse mode
        """
        for user_id in settings.allowed_user_ids:
            try:
                await self.send_message(user_id, text, parse_mode)
            except Exception as e:
                logger.error(f"Failed to broadcast to {user_id}: {e}")


# Global bot instance
telegram_bot: Optional[CursorTelegramBot] = None


def get_telegram_bot() -> CursorTelegramBot:
    """Get or create the global Telegram bot instance."""
    global telegram_bot
    if telegram_bot is None:
        telegram_bot = CursorTelegramBot()
    return telegram_bot


__all__ = ["CursorTelegramBot", "get_telegram_bot"]
