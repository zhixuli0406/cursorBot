"""
CursorBot Main Entry Point
Starts Telegram Bot, Discord Bot, and API Server
"""

import asyncio
import os
import signal
import sys
from typing import Optional

# Fix SSL certificate issue on macOS
try:
    import certifi
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
    os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())
except ImportError:
    pass

import uvicorn

from .bot.telegram_bot import CursorTelegramBot, get_telegram_bot
from .server.api import app
from .utils.config import settings
from .utils.logger import logger
from .utils.task_queue import get_task_queue


class CursorBotApp:
    """
    Main application class that coordinates all services.
    Manages Telegram Bot, Discord Bot, and API Server lifecycle.
    """

    def __init__(self):
        self.telegram_bot: Optional[CursorTelegramBot] = None
        self.discord_channel = None
        self.server_task: Optional[asyncio.Task] = None
        self.bot_task: Optional[asyncio.Task] = None
        self.discord_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def start_telegram_bot(self) -> None:
        """Start the Telegram bot."""
        try:
            self.telegram_bot = get_telegram_bot()
            await self.telegram_bot.start()
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
            raise

    async def start_discord_bot(self) -> None:
        """Start the Discord bot."""
        try:
            from .channels.discord_channel import create_discord_channel, DISCORD_AVAILABLE
            from .channels.discord_handlers import setup_discord_handlers

            if not DISCORD_AVAILABLE:
                logger.warning("discord.py not installed, skipping Discord bot")
                return

            # Parse allowed guilds and users
            allowed_guilds = []
            if settings.discord_allowed_guilds:
                allowed_guilds = [int(g.strip()) for g in settings.discord_allowed_guilds.split(",") if g.strip()]

            allowed_users = []
            if settings.discord_allowed_users:
                allowed_users = [int(u.strip()) for u in settings.discord_allowed_users.split(",") if u.strip()]

            # Create Discord channel
            self.discord_channel = create_discord_channel(
                token=settings.discord_bot_token,
                allowed_guilds=allowed_guilds,
                allowed_users=allowed_users,
            )

            if self.discord_channel:
                # Setup handlers
                setup_discord_handlers(self.discord_channel)
                logger.info("Starting Discord Bot...")
                await self.discord_channel.start()

        except Exception as e:
            logger.error(f"Discord bot error: {e}")
            # Don't raise - let other services continue

    async def start_api_server(self) -> None:
        """Start the FastAPI server."""
        config = uvicorn.Config(
            app=app,
            host=settings.server_host,
            port=settings.server_port,
            log_level="info" if settings.debug else "warning",
        )
        server = uvicorn.Server(config)

        try:
            await server.serve()
        except Exception as e:
            logger.error(f"API server error: {e}")
            raise

    async def _start_reminder_service(self) -> None:
        """Start the calendar reminder service."""
        try:
            from .core.calendar_reminder import get_reminder_service, ReminderPlatform
            
            reminder_service = get_reminder_service()
            
            # Register Telegram send handler
            async def telegram_send_handler(chat_id: str, message: str) -> None:
                if self.telegram_bot and self.telegram_bot.application:
                    try:
                        await self.telegram_bot.application.bot.send_message(
                            chat_id=int(chat_id),
                            text=message,
                            parse_mode="Markdown",
                        )
                    except Exception as e:
                        logger.error(f"Failed to send Telegram reminder: {e}")
            
            reminder_service.register_send_handler(
                ReminderPlatform.TELEGRAM,
                telegram_send_handler
            )
            
            # Register Discord send handler
            async def discord_send_handler(chat_id: str, message: str) -> None:
                if self.discord_channel and self.discord_channel.client:
                    try:
                        channel = self.discord_channel.client.get_channel(int(chat_id))
                        if channel:
                            await channel.send(message)
                    except Exception as e:
                        logger.error(f"Failed to send Discord reminder: {e}")
            
            reminder_service.register_send_handler(
                ReminderPlatform.DISCORD,
                discord_send_handler
            )
            
            # Start the reminder service
            await reminder_service.start()
            logger.info("Calendar reminder service started")
            
        except Exception as e:
            logger.warning(f"Failed to start reminder service: {e}")

    async def run(self) -> None:
        """
        Run all services concurrently.
        """
        logger.info("=" * 50)
        logger.info("Starting CursorBot")
        logger.info("=" * 50)

        # Setup signal handlers
        self._setup_signal_handlers()

        # Ensure directories exist
        settings.ensure_directories()

        try:
            # Initialize and start task queue
            task_queue = get_task_queue()
            await task_queue.start()
            logger.info("Task queue started")

            # Initialize and start calendar reminder service
            await self._start_reminder_service()

            # Start services concurrently
            tasks = []

            # Telegram Bot
            self.bot_task = asyncio.create_task(
                self.start_telegram_bot(),
                name="telegram_bot",
            )
            tasks.append(self.bot_task)

            # Discord Bot (if enabled)
            if settings.discord_enabled and settings.discord_bot_token:
                logger.info("Discord Bot enabled, starting...")
                self.discord_task = asyncio.create_task(
                    self.start_discord_bot(),
                    name="discord_bot",
                )
                tasks.append(self.discord_task)
            else:
                logger.info("Discord Bot disabled (set DISCORD_ENABLED=true to enable)")

            # API Server
            self.server_task = asyncio.create_task(
                self.start_api_server(),
                name="api_server",
            )
            tasks.append(self.server_task)

            # Wait for shutdown signal or task completion
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Check for errors
            for task in done:
                if task.exception():
                    logger.error(f"Task {task.get_name()} failed: {task.exception()}")

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except asyncio.CancelledError:
            logger.info("Application cancelled")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("Shutting down CursorBot...")

        # Stop reminder service
        try:
            from .core.calendar_reminder import get_reminder_service
            reminder_service = get_reminder_service()
            await reminder_service.stop()
        except Exception as e:
            logger.debug(f"Error stopping reminder service: {e}")

        # Stop task queue
        task_queue = get_task_queue()
        await task_queue.stop()

        # Stop Telegram bot
        if self.telegram_bot:
            await self.telegram_bot.stop()

        # Stop Discord bot
        if self.discord_channel:
            try:
                await self.discord_channel.stop()
            except Exception as e:
                logger.error(f"Error stopping Discord bot: {e}")

        # Cancel tasks
        for task in [self.bot_task, self.server_task, self.discord_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("CursorBot shutdown complete")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self._handle_signal()),
            )

    async def _handle_signal(self) -> None:
        """Handle shutdown signal."""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()

        # Cancel running tasks
        if self.bot_task:
            self.bot_task.cancel()
        if self.server_task:
            self.server_task.cancel()
        if self.discord_task:
            self.discord_task.cancel()


def main() -> None:
    """Main entry point."""
    # Print startup banner
    print("""
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║   🤖 CursorBot - Multi-Platform AI Control    ║
    ║                                               ║
    ║   Telegram + Discord + Cursor Agent           ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    """)

    # Validate configuration
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is required!")
        logger.info("Please set it in your .env file or environment variables")
        sys.exit(1)

    if not settings.allowed_user_ids:
        logger.warning("No TELEGRAM_ALLOWED_USERS configured. Bot will reject all users.")

    # Run application
    app_instance = CursorBotApp()

    try:
        asyncio.run(app_instance.run())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
